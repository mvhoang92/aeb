#!/usr/bin/env python
"""Quay video UI radar_aeb_view.py cho toàn bộ scenario vào chung một folder.

Cách hoạt động (rút ra từ các lần thử nghiệm):
- Chạy UI trên một màn hình ảo Xvfb (không chiếm màn hình thật).
- Quay bằng ffmpeg dùng NVENC (encode trên GPU) để CPU rảnh cho client chạy
  đúng timing async; nếu encode bằng CPU sẽ làm tụt FPS và sai lệch hành vi AEB.
- Mỗi scenario tự thoát sau khi hoàn tất + nán lại (--linger) nhờ cờ
  --scenario-autoexit-s của UI; thoát sạch nên CARLA tự dọn actor.
- Vẫn chủ động dọn actor còn sót giữa các lần để server không chậm dần.

Ví dụ:
  ../venv/bin/python scripts/record_scenario_videos.py
  ../venv/bin/python scripts/record_scenario_videos.py --scenario ccrs_50 --scenario clear_road_50
"""

from __future__ import print_function

import argparse
import datetime
import glob
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import yaml

AEB_ROOT = Path(__file__).resolve().parents[1]
VENV_PYTHON = str((AEB_ROOT.parent / "venv" / "bin" / "python").resolve())


def load_carla():
    try:
        import carla  # noqa: F401
        return carla
    except ImportError:
        for egg in glob.glob(
            os.path.expanduser("~/CARLA_0.9.11/PythonAPI/carla/dist/carla-*.egg")
        ):
            sys.path.append(egg)
        import carla  # noqa: F401
        return carla


def clean_actors(host, port):
    """Dọn vehicle/sensor còn sót trên server để tránh chồng chất gây lag."""
    carla = load_carla()
    try:
        client = carla.Client(host, port)
        client.set_timeout(10.0)
        world = client.get_world()
        actors = world.get_actors()
        for sensor in actors.filter("sensor.*"):
            try:
                sensor.stop()
            except RuntimeError:
                pass
            sensor.destroy()
        for vehicle in actors.filter("vehicle.*"):
            vehicle.destroy()
    except Exception as error:  # noqa: BLE001
        print("  [cảnh báo] không dọn được actor: {}".format(error))


def reload_world(host, port, wait_s=2.0):
    carla = load_carla()
    try:
        client = carla.Client(host, port)
        client.set_timeout(20.0)
        client.reload_world()
        if wait_s > 0.0:
            time.sleep(float(wait_s))
        return True
    except Exception as error:  # noqa: BLE001
        print("  [cảnh báo] không reload được world: {}".format(error))
        return False


def scenario_ids(config_path, requested):
    with open(str(config_path)) as stream:
        data = yaml.safe_load(stream)
    all_ids = [s["id"] for s in data.get("scenarios", []) if s.get("id")]
    if not requested:
        return all_ids
    missing = [s for s in requested if s not in all_ids]
    if missing:
        raise SystemExit("Không tìm thấy scenario: {}".format(", ".join(missing)))
    return [s for s in all_ids if s in requested]


def start_xvfb(display, screen_size):
    proc = subprocess.Popen(
        ["Xvfb", display, "-screen", "0", screen_size + "x24", "-nolisten", "tcp"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    env = dict(os.environ, DISPLAY=display)
    for _ in range(50):
        if subprocess.call(
            ["xdpyinfo"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        ) == 0:
            return proc
        time.sleep(0.1)
    raise SystemExit("Xvfb không khởi động được trên {}".format(display))


def record_one(scenario, args, env, log_dir):
    out_path = Path(args.output_dir) / (scenario + ".mp4")
    log_path = log_dir / (scenario + ".log")
    if args.skip_existing and out_path.exists() and out_path.stat().st_size > 50_000:
        return True, str(out_path), str(log_path), "skip_existing"
    ui_cmd = [
        VENV_PYTHON, str(args.ui_script),
        "--res", str(args.capture_size),
        "--scenario-config", str(args.scenario_config),
        "--control-mode", args.control_mode,
        "--scenario", scenario,
        "--scenario-warmup-s", str(args.warmup),
        "--scenario-debug-interval-s", str(args.debug_interval),
        "--scenario-autoexit-s", str(args.linger),
    ]
    if Path(args.ui_script).name == "aeb_demo_view.py":
        ui_cmd.insert(4, "--no-fit-screen")
        ui_cmd.extend(
            [
                "--record-video-path",
                str(out_path),
                "--record-video-fps",
                str(args.fps),
                "--record-video-codec",
                args.encoder,
            ]
        )
    if args.brake_mode != "config":
        ui_cmd.extend(["--brake-mode", args.brake_mode])
    if args.keep_driving_after_aeb:
        ui_cmd.append("--keep-driving-after-aeb")
    log_file = open(str(log_path), "w")
    log_file.write("UI command: {}\n".format(" ".join(ui_cmd)))
    log_file.flush()
    ui_proc = subprocess.Popen(
        ui_cmd, cwd=str(AEB_ROOT), env=env, stdout=log_file, stderr=subprocess.STDOUT
    )
    # Chờ cửa sổ UI hiện ra trước khi quay.
    time.sleep(2.0)
    if ui_proc.poll() is not None:
        log_file.close()
        return False, "UI thoát sớm (xem log)", str(log_path), "ui_exit_early"

    if Path(args.ui_script).name == "aeb_demo_view.py":
        deadline = time.time() + args.max_seconds + 15
        while ui_proc.poll() is None and time.time() < deadline:
            time.sleep(0.5)
        if ui_proc.poll() is None:
            ui_proc.terminate()
            try:
                ui_proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                ui_proc.kill()
        log_file.close()
        ok = out_path.exists() and out_path.stat().st_size > 50_000
        status = "ok" if ok else "video_missing_or_too_small"
        return ok, str(out_path), str(log_path), status

    if args.encoder == "h264_nvenc":
        encoder_args = ["-c:v", "h264_nvenc", "-preset", "p4"]
    else:
        encoder_args = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23"]
    ffmpeg_cmd = [
        "ffmpeg", "-y", "-f", "x11grab",
        "-framerate", str(args.fps),
        "-video_size", args.capture_size,
        "-i", "{}.0+0,0".format(args.display),
        "-t", str(args.max_seconds),
    ] + encoder_args + [
        "-pix_fmt", "yuv420p",
        str(out_path),
    ]
    log_file.write("FFmpeg command: {}\n".format(" ".join(ffmpeg_cmd)))
    log_file.flush()
    ffmpeg_proc = subprocess.Popen(
        ffmpeg_cmd, env=env, stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

    deadline = time.time() + args.max_seconds + 15
    while ui_proc.poll() is None and time.time() < deadline:
        time.sleep(0.5)

    if ui_proc.poll() is None:
        ui_proc.terminate()
        try:
            ui_proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            ui_proc.kill()

    # Dừng ffmpeg sạch để mp4 được finalize.
    if ffmpeg_proc.poll() is None:
        try:
            ffmpeg_proc.communicate(input=b"q", timeout=10)
        except subprocess.TimeoutExpired:
            ffmpeg_proc.send_signal(signal.SIGINT)
            try:
                ffmpeg_proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                ffmpeg_proc.kill()
    log_file.close()
    ok = out_path.exists() and out_path.stat().st_size > 50_000
    status = "ok" if ok else "video_missing_or_too_small"
    return ok, str(out_path), str(log_path), status


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scenario-config", type=Path,
        default=AEB_ROOT / "configs" / "scenarios" / "suites" / "report_demo.yaml",
    )
    parser.add_argument(
        "--output-dir", default=str(AEB_ROOT / "outputs" / "scenario_videos"),
    )
    parser.add_argument(
        "--ui-script",
        type=Path,
        default=Path("ui/aeb_demo_view.py"),
        help="Pygame UI dùng để quay video. Mặc định là UI final 3 vùng.",
    )
    parser.add_argument(
        "--run-id",
        help=(
            "Tên thư mục con trong output-dir. Nếu bỏ trống sẽ sinh theo thời gian; "
            "dùng để gom một batch video/report."
        ),
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        help="Đường dẫn file markdown report. Mặc định nằm trong thư mục output batch.",
    )
    parser.add_argument("--scenario", action="append", dest="scenarios")
    parser.add_argument("--control-mode", default="physics")
    parser.add_argument(
        "--brake-mode",
        choices=(
            "config",
            "binary",
            "staged",
            "pid",
            "pid_v1",
            "pid_v2",
            "pid_v2_comfort",
            "staged_pid",
        ),
        default="config",
        help="Override brake.brake_mode khi quay bằng UI final.",
    )
    parser.add_argument(
        "--keep-driving-after-aeb",
        action="store_true",
        help=(
            "Truyền sang UI final để demo realistic: AEB có thể nhả phanh và "
            "scenario controller tiếp tục lái."
        ),
    )
    parser.add_argument("--display", default=":99")
    parser.add_argument("--screen-size", default="1920x1080")
    parser.add_argument("--capture-size", default="1920x1080")
    parser.add_argument("--fps", type=int, default=20)
    parser.add_argument(
        "--encoder",
        choices=("h264_nvenc", "libx264"),
        default="h264_nvenc",
        help="h264_nvenc nhanh hơn nếu NVIDIA encode ổn; libx264 là fallback CPU.",
    )
    parser.add_argument("--warmup", type=float, default=2.0)
    parser.add_argument("--linger", type=float, default=4.0)
    parser.add_argument("--debug-interval", type=float, default=0.2)
    parser.add_argument("--max-seconds", type=float, default=90.0)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=2000)
    parser.add_argument(
        "--scenario-cooldown-s",
        type=float,
        default=2.0,
        help="Nghỉ giữa hai video để CARLA kịp dọn actor/sensor.",
    )
    parser.add_argument(
        "--reload-world-every",
        type=int,
        default=1,
        help="Nếu > 0, reload world sau mỗi N video để chạy batch bền hơn.",
    )
    parser.add_argument(
        "--reload-world-wait-s",
        type=float,
        default=2.0,
        help="Số giây đợi sau reload_world trước video tiếp theo.",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Nếu video đã tồn tại và đủ lớn thì bỏ qua để resume batch.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Chỉ liệt kê scenario sẽ quay, không mở Xvfb/ffmpeg/UI.",
    )
    args = parser.parse_args()
    if args.scenario_cooldown_s < 0:
        parser.error("--scenario-cooldown-s không được âm")
    if args.reload_world_every < 0:
        parser.error("--reload-world-every không được âm")
    if args.reload_world_wait_s < 0:
        parser.error("--reload-world-wait-s không được âm")
    return args


def write_report(report_path, args, ids, results):
    lines = [
        "# Scenario Video Report",
        "",
        "- Scenario config: `{}`".format(args.scenario_config),
        "- Output dir: `{}`".format(args.output_dir),
        "- Control mode: `{}`".format(args.control_mode),
        "- Capture: `{}` @ {} FPS".format(args.capture_size, args.fps),
        "- Encoder: `{}`".format(args.encoder),
        "",
        "Cột Drive để trống để sau khi upload video lên Google Drive thì điền link.",
        "",
        "| # | Scenario | Video local | Log | Status | Google Drive |",
        "|---:|---|---|---|---|---|",
    ]
    by_id = {item["scenario"]: item for item in results}
    for index, scenario in enumerate(ids, 1):
        item = by_id.get(scenario, {})
        video = item.get("video", "")
        log = item.get("log", "")
        status = item.get("status", "not_run")
        lines.append(
            "| {} | `{}` | `{}` | `{}` | {} |  |".format(
                index,
                scenario,
                video,
                log,
                status,
            )
        )
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    args = parse_args()
    ids = scenario_ids(args.scenario_config, args.scenarios)
    if args.run_id:
        output_dir = Path(args.output_dir) / args.run_id
    else:
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path(args.output_dir) / "video_batch_{}".format(stamp)
    args.output_dir = str(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    log_dir = output_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    report_path = args.report_path or (output_dir / "video_report.md")
    env = dict(os.environ, DISPLAY=args.display)

    print("Sẽ quay {} scenario vào {}".format(len(ids), args.output_dir))
    if args.dry_run:
        for index, scenario in enumerate(ids, 1):
            print("[{}/{}] {}".format(index, len(ids), scenario))
        write_report(report_path, args, ids, [])
        print("Dry-run report: {}".format(report_path))
        return

    xvfb = start_xvfb(args.display, args.screen_size)
    results = []
    try:
        for index, scenario in enumerate(ids, 1):
            print("[{}/{}] {} ...".format(index, len(ids), scenario))
            clean_actors(args.host, args.port)
            ok, video, log, status = record_one(scenario, args, env, log_dir)
            print("   {} -> {}".format("OK" if ok else "FAIL", video))
            results.append(
                {
                    "scenario": scenario,
                    "ok": ok,
                    "video": video,
                    "log": log,
                    "status": status,
                }
            )
            write_report(report_path, args, ids, results)
            clean_actors(args.host, args.port)
            if args.scenario_cooldown_s > 0.0 and index < len(ids):
                time.sleep(args.scenario_cooldown_s)
            if (
                args.reload_world_every > 0
                and index < len(ids)
                and index % args.reload_world_every == 0
            ):
                print("   Reload world sau {} video để giảm rủi ro crash".format(index))
                reload_world(args.host, args.port, args.reload_world_wait_s)
    finally:
        xvfb.terminate()

    write_report(report_path, args, ids, results)
    passed = sum(1 for item in results if item["ok"])
    print("\nXong: {}/{} video tạo thành công.".format(passed, len(results)))
    print("Report: {}".format(report_path))
    for item in results:
        if not item["ok"]:
            print("  FAIL: {} ({})".format(item["scenario"], item["status"]))


if __name__ == "__main__":
    main()
