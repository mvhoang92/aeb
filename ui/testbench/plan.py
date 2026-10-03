"""Experiment plan: selection + options -> ordered runner commands (no Tk).

Command strategy
----------------
Both runners accept ``--scenario`` several times (``action="append"``) and
write one run directory per invocation, recording the SHA-256 of the *real*
suite file.  Therefore the plan issues exactly one command per
``(suite file, policy)``:

* whole suite selected  -> no ``--scenario`` flag (identical to the paper
  campaign invocation);
* part of a suite       -> one ``--scenario <id>`` per selected id, in YAML
  order, in the same single command and run directory.

No temporary suite YAML is ever generated, and ``--resume`` is only used when
the user explicitly continues an interrupted run.  Commands are ordered suite
by suite (all policies of one suite before the next suite) so an interrupted
queue still leaves complete paired comparisons for the suites that finished.
"""

from __future__ import absolute_import

import re
import shlex
from collections import OrderedDict, namedtuple
from pathlib import Path

from ui.testbench.paths import AEB_ROOT, CARLA_PYTHON, FUSION_RUNNER, RADAR_RUNNER
from ui.testbench.policies import (
    DEVICE_CPU,
    DEVICE_CUDA,
    POLICIES,
    policy_slug,
    sensor_config_for,
)


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 2000
PAPER_REPEAT = 5
PAPER_SEED = 2026

RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")

# Wall-clock model used for the *estimate* shown before a run.  Calibrated on
# this machine (RTX 3050 laptop, CARLA 0.9.11 Low, synchronous mode) from
# test-bench runs on 2026-10-03: radar smoke 5 runs ~36 s, fusion CUDA 1 run
# ~14 s.  Synchronous simulation runs faster than real time and scenarios stop
# early after a full stop, so simulated seconds are scaled down.  Real time
# varies with map loads, evidence recording and CARLA health.
STARTUP_S = {RADAR_RUNNER: 5.0, FUSION_RUNNER: 8.0}
SIM_FACTOR = {RADAR_RUNNER: 0.4, FUSION_RUNNER: 0.6}
RUN_OVERHEAD_S = {RADAR_RUNNER: 1.0, FUSION_RUNNER: 1.5}
COOLDOWN_FACTOR = 0.5
LOAD_MAP_S = 3.0
RELOAD_S = 1.5
RELOAD_WAIT_S = 2.0
EVIDENCE_FACTOR = 1.6


class ExperimentOptions(object):
    """Section 2/3 choices that apply to every command of a plan."""

    FIELDS = (
        ("repeat", 1),
        ("seed", PAPER_SEED),
        ("cooldown_s", 1.0),
        ("reload_every", 1),
        ("load_map", True),
        ("record_evidence", False),
        ("resume", False),
        ("control_mode", "physics"),
        ("device", DEVICE_CUDA),
        ("host", DEFAULT_HOST),
        ("port", DEFAULT_PORT),
    )

    def __init__(self, **values):
        unknown = set(values) - set(name for name, _ in self.FIELDS)
        if unknown:
            raise TypeError("unknown options: {}".format(sorted(unknown)))
        for name, default in self.FIELDS:
            setattr(self, name, values.get(name, default))

    def as_dict(self):
        return OrderedDict((name, getattr(self, name)) for name, _ in self.FIELDS)

    def validate(self):
        errors = []
        if int(self.repeat) < 1:
            errors.append("Số lần lặp phải ≥ 1.")
        if float(self.cooldown_s) < 0:
            errors.append("Thời gian nghỉ giữa kịch bản không được âm.")
        if int(self.reload_every) < 0:
            errors.append("Reload world mỗi N kịch bản không được âm.")
        if self.control_mode not in ("yaml", "physics", "deterministic"):
            errors.append("Chế độ điều khiển không hợp lệ.")
        if self.device not in (DEVICE_CUDA, DEVICE_CPU):
            errors.append("Thiết bị không hợp lệ.")
        return errors


Preset = namedtuple(
    "Preset",
    "key label suites policies device control_mode repeat full_repeat summary",
)

CORE_SUITES = (
    "configs/scenarios/suites/system_limit_extended_sweep.yaml",
    "configs/scenarios/suites/radar_only_regression.yaml",
    "configs/scenarios/suites/fusion_physical_false_positive_v2.yaml",
    "configs/scenarios/suites/fusion_nonvehicle_hazard_limitation.yaml",
)
ALL_POLICIES = tuple(POLICIES)

PRESETS = OrderedDict(
    (
        (
            "smoke",
            Preset(
                "smoke",
                "Smoke nhanh",
                ("configs/scenarios/suites/smoke_basic.yaml",),
                ("radar_only",),
                DEVICE_CUDA,
                "physics",
                1,
                1,
                "5 kịch bản cơ bản, radar-only, 1 lần: kiểm tra nhanh CARLA và "
                "toàn bộ chuỗi chạy trước chiến dịch dài.",
            ),
        ),
        (
            "core",
            Preset(
                "core",
                "Hồi quy core",
                CORE_SUITES,
                ALL_POLICIES,
                DEVICE_CUDA,
                "physics",
                1,
                PAPER_REPEAT,
                "Phạm vi core của paper (4 suite, không gồm lỗi radar tổng hợp) "
                "× 3 chính sách, CUDA, physics. Giao thức đầy đủ của paper là "
                "5 lần lặp; mặc định 1 lần để vừa thời gian.",
            ),
        ),
        (
            "holdout",
            Preset(
                "holdout",
                "Hold-out",
                ("configs/scenarios/suites/fusion_fallback_holdout.yaml",),
                ALL_POLICIES,
                DEVICE_CUDA,
                "physics",
                1,
                PAPER_REPEAT,
                "Bộ hold-out đóng băng × 3 chính sách, CUDA, physics. Giao thức "
                "đầy đủ là 5 lần lặp; mặc định 1 lần. Chỉ để đánh giá — không "
                "chỉnh tham số theo kết quả hold-out.",
            ),
        ),
    )
)


def slugify(text):
    slug = re.sub(r"[^A-Za-z0-9]+", "_", str(text or "")).strip("_").lower()
    return slug or "custom"


def default_run_id_template(label, now, multi_suite=False):
    """``tb_<preset|custom>_{policy}[_{suite}]_<yyyymmdd_hhmm>``."""
    middle = "{policy}_{suite}" if multi_suite else "{policy}"
    return "tb_{}_{}_{}".format(slugify(label), middle, now.strftime("%Y%m%d_%H%M"))


def expand_run_id(template, policy_part, suite_part, multi_policy, multi_suite):
    """Fill ``{policy}``/``{suite}``; append them if needed for uniqueness."""
    run_id = str(template or "").strip()
    if "{policy}" in run_id:
        run_id = run_id.replace("{policy}", policy_part)
    elif multi_policy:
        run_id += "_" + policy_part
    if "{suite}" in run_id:
        run_id = run_id.replace("{suite}", suite_part)
    elif multi_suite:
        run_id += "_" + suite_part
    return run_id


def resolve_control_mode(option, suite):
    return suite.default_control_mode if option == "yaml" else option


def build_argv(
    runner,
    sensor_config,
    suite_rel,
    control_mode,
    options,
    run_id,
    scenario_ids=(),
    python=CARLA_PYTHON,
):
    argv = [
        str(python),
        runner,
        "--sensor-config",
        sensor_config,
        "--scenario-config",
        suite_rel,
        "--control-mode",
        control_mode,
        "--repeat",
        str(int(options.repeat)),
        "--seed",
        str(int(options.seed)),
        "--scenario-cooldown-s",
        "{:g}".format(float(options.cooldown_s)),
        "--reload-world-every",
        str(int(options.reload_every)),
        "--run-id",
        run_id,
    ]
    if str(options.host) != DEFAULT_HOST:
        argv.extend(("--host", str(options.host)))
    if int(options.port) != DEFAULT_PORT:
        argv.extend(("--port", str(int(options.port))))
    if options.load_map:
        argv.append("--load-map")
    if options.record_evidence:
        argv.append("--record-evidence")
    if options.resume:
        argv.append("--resume")
    for scenario_id in scenario_ids:
        argv.extend(("--scenario", scenario_id))
    return argv


def command_text(argv, cwd=None):
    text = " ".join(shlex.quote(str(part)) for part in argv)
    if cwd is not None:
        text = "cd {} && {}".format(shlex.quote(str(cwd)), text)
    return text


def estimate_seconds(runner, scenarios, options):
    """Rough wall-clock estimate for one command (see constants above)."""
    runs = len(scenarios) * int(options.repeat)
    if runs == 0:
        return 0.0
    simulated = sum(scenario.duration_s for scenario in scenarios) * int(options.repeat)
    simulated *= SIM_FACTOR.get(runner, 0.6)
    if options.record_evidence:
        simulated *= EVIDENCE_FACTOR
    total = STARTUP_S.get(runner, 8.0) + simulated
    total += runs * RUN_OVERHEAD_S.get(runner, 1.5)
    total += (runs - 1) * float(options.cooldown_s) * COOLDOWN_FACTOR
    if int(options.reload_every) > 0:
        total += ((runs - 1) // int(options.reload_every)) * (RELOAD_S + RELOAD_WAIT_S)
    if options.load_map:
        total += LOAD_MAP_S
    return total


def format_duration(seconds):
    seconds = float(seconds or 0.0)
    if seconds < 60:
        return "< 1 phút"
    minutes = int(round(seconds / 60.0))
    if minutes < 60:
        return "≈ {} phút".format(minutes)
    hours, minutes = divmod(minutes, 60)
    if minutes == 0:
        return "≈ {} giờ".format(hours)
    return "≈ {} giờ {} phút".format(hours, minutes)


class PlannedCommand(object):
    def __init__(self, **values):
        self.__dict__.update(values)

    @property
    def scenario_runs(self):
        return len(self.runnable) * int(self.repeat)

    @property
    def selection_text(self):
        if self.whole_suite:
            return "cả suite ({})".format(len(self.runnable))
        return "{} kịch bản".format(len(self.runnable))

    def text(self, with_cwd=False):
        return command_text(self.argv, AEB_ROOT if with_cwd else None)


class Plan(object):
    def __init__(self, commands, errors, warnings):
        self.commands = commands
        self.errors = errors
        self.warnings = warnings

    @property
    def ok(self):
        return not self.errors and bool(self.commands)

    @property
    def total_runs(self):
        return sum(command.scenario_runs for command in self.commands)

    @property
    def total_estimate_s(self):
        return sum(command.estimate_s for command in self.commands)

    def script_text(self):
        lines = ["cd {}".format(shlex.quote(str(AEB_ROOT)))]
        lines.extend(command.text() for command in self.commands)
        return "\n".join(lines)


def build_plan(
    catalog,
    selected_keys,
    policy_keys,
    options,
    run_id_template,
    logs_root,
    python=CARLA_PYTHON,
    path_exists=None,
):
    """Return a :class:`Plan`; never touches CARLA or the filesystem except
    for checking whether a run directory already exists."""
    path_exists = path_exists or (lambda path: Path(path).exists())
    errors = list(options.validate())
    warnings = []
    selected = set(tuple(key) for key in selected_keys)
    policy_keys = [key for key in POLICIES if key in set(policy_keys)]
    if not selected:
        errors.append("Chưa chọn kịch bản nào (mục 1).")
    if not policy_keys:
        errors.append("Chưa chọn hệ thống nào để kiểm tra (mục 2).")

    suites = [
        suite
        for suite in catalog.suites
        if any(scenario.key in selected for scenario in suite.scenarios)
    ]
    multi_suite = len(suites) > 1
    multi_policy = len(policy_keys) > 1
    commands = []
    seen_run_ids = set()
    for suite in suites:
        chosen = [scenario for scenario in suite.scenarios if scenario.key in selected]
        whole = len(chosen) == len(suite.scenarios)
        mode = resolve_control_mode(options.control_mode, suite)
        runnable = [scenario for scenario in chosen if scenario.supports_mode(mode)]
        skipped = [scenario.id for scenario in chosen if not scenario.supports_mode(mode)]
        if skipped:
            warnings.append(
                "{}: {} kịch bản chỉ hỗ trợ {} nên runner sẽ bỏ qua ở chế độ {} "
                "({}).".format(
                    suite.rel,
                    len(skipped),
                    "/".join(sorted(set(
                        mode_name
                        for scenario in chosen
                        if not scenario.supports_mode(mode)
                        for mode_name in scenario.control_modes
                    ))),
                    mode,
                    ", ".join(skipped[:4]) + (" …" if len(skipped) > 4 else ""),
                )
            )
        if not runnable:
            warnings.append(
                "{}: không còn kịch bản nào chạy được ở chế độ {} — bỏ khỏi kế "
                "hoạch.".format(suite.rel, mode)
            )
            continue
        if "holdout" in suite.tags:
            warnings.append(
                "Hold-out ({}): chỉ dùng để đánh giá; không chỉnh tham số theo "
                "kết quả.".format(suite.rel)
            )
        if "needs_variant" in suite.tags:
            warnings.append(
                "{}: suite này cần sensor config tắt detector (do campaign tạo); "
                "với cấu hình thường điều kiện camera tắt KHÔNG được tái hiện.".format(
                    suite.rel
                )
            )
        if "synthetic" in suite.tags:
            warnings.append(
                "{}: radar ma là lỗi tổng hợp (fault injection), không phải tần "
                "suất radar ma thật.".format(suite.rel)
            )
        for key in policy_keys:
            item = POLICIES[key]
            device = options.device if item.uses_camera else None
            slug = policy_slug(key, options.device)
            run_id = expand_run_id(
                run_id_template, slug, suite.stem, multi_policy, multi_suite
            )
            log_dir = Path(logs_root) / run_id
            exists = bool(run_id) and path_exists(log_dir)
            if not RUN_ID_PATTERN.match(run_id or ""):
                errors.append(
                    "Run-id '{}' không hợp lệ (chỉ dùng chữ, số, _ . -).".format(run_id)
                )
            elif run_id in seen_run_ids:
                errors.append(
                    "Run-id '{}' bị trùng giữa các lệnh; thêm {{policy}}/{{suite}} "
                    "vào mẫu run-id.".format(run_id)
                )
            elif exists and not options.resume:
                errors.append(
                    "Thư mục log '{}' đã tồn tại. Đổi run-id hoặc bật 'Tiếp tục "
                    "run-id có sẵn'.".format(run_id)
                )
            seen_run_ids.add(run_id)
            sensor_config = sensor_config_for(key, options.device)
            scenario_ids = () if whole else tuple(scenario.id for scenario in chosen)
            argv = build_argv(
                item.runner,
                sensor_config,
                suite.rel,
                mode,
                options,
                run_id,
                scenario_ids,
                python=python,
            )
            commands.append(
                PlannedCommand(
                    index=len(commands) + 1,
                    policy_key=key,
                    policy_label=item.label,
                    device=device,
                    suite_rel=suite.rel,
                    suite_title=suite.title,
                    whole_suite=whole,
                    scenario_ids=scenario_ids,
                    runnable=runnable,
                    skipped=skipped,
                    control_mode=mode,
                    repeat=int(options.repeat),
                    run_id=run_id,
                    log_dir=log_dir,
                    log_dir_exists=exists,
                    sensor_config=sensor_config,
                    runner=item.runner,
                    argv=argv,
                    estimate_s=estimate_seconds(item.runner, runnable, options),
                )
            )
    if options.device == DEVICE_CPU and any(
        POLICIES[key].uses_camera for key in policy_keys
    ):
        warnings.append(
            "CPU chỉ để chẩn đoán: không trộn kết quả CPU vào bằng chứng cuối "
            "(bằng chứng cuối yêu cầu CUDA)."
        )
    if options.resume:
        warnings.append(
            "--resume chỉ chạy được khi working tree sạch, cùng commit và config "
            "không đổi so với lần chạy trước."
        )
    if options.record_evidence:
        warnings.append("Ghi video bằng chứng làm mỗi kịch bản chậm hơn đáng kể.")
    return Plan(commands, errors, warnings)
