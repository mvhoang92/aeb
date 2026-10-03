"""Brake-permission policies under test and their runner/config mapping.

The mapping matches the paper campaign (``scripts/campaign/run_v4_campaign.py``):
radar-only runs the radar runner with ``configs/sensors.yaml``; the two fusion
policies run the fusion runner with the frozen ``*_batch_{gpu,cpu}.yaml``
sensor configs.  Nothing here edits a config.
"""

from __future__ import absolute_import

from collections import OrderedDict, namedtuple

from ui.testbench.paths import FUSION_RUNNER, RADAR_RUNNER


DEVICE_CUDA = "cuda"
DEVICE_CPU = "cpu"
DEVICES = (DEVICE_CUDA, DEVICE_CPU)

DEVICE_LABELS = OrderedDict(
    (
        (DEVICE_CUDA, "CUDA (bắt buộc CUDAExecutionProvider)"),
        (DEVICE_CPU, "CPU (chỉ để chẩn đoán)"),
    )
)

DEVICE_HINT = (
    "CUDA: YOLO bắt buộc chạy trên GPU. Nếu thiếu CUDAExecutionProvider, runner "
    "dừng trước khi kết nối CARLA với exit code 3 — đó là HARD-STOP KỸ THUẬT, "
    "không phải thuật toán FAIL. CPU chỉ dùng để chẩn đoán, không trộn vào "
    "bằng chứng cuối. Radar-only không dùng camera nên không phụ thuộc thiết bị."
)

CONTROL_MODES = OrderedDict(
    (
        ("yaml", "Theo file kịch bản"),
        ("physics", "physics"),
        ("deterministic", "deterministic"),
    )
)

CONTROL_MODE_HINT = (
    "physics: xe được điều khiển bằng ga/phanh qua mô hình vật lý của CARLA — "
    "gần thực tế hơn, giao thức của paper dùng chế độ này. deterministic: đặt "
    "thẳng vận tốc (set_target_velocity) — lặp lại tốt nhưng bỏ qua động lực "
    "học. 'Theo file kịch bản' dùng runner.control_mode của từng file YAML. "
    "Kịch bản khai báo control_modes: [physics] sẽ bị runner bỏ qua ở "
    "deterministic."
)

Policy = namedtuple(
    "Policy",
    "key label slug runner configs uses_camera explanation",
)

POLICIES = OrderedDict(
    (
        (
            "radar_only",
            Policy(
                "radar_only",
                "Radar-only",
                "radar_only",
                RADAR_RUNNER,
                {
                    DEVICE_CUDA: "configs/sensors.yaml",
                    DEVICE_CPU: "configs/sensors.yaml",
                },
                False,
                "Chỉ radar quyết định phanh theo TTC/khoảng cách dừng. Recall "
                "cao, nhưng dễ phanh nhầm khi radar thấy vật không nguy hiểm.",
            ),
        ),
        (
            "hard_gate",
            Policy(
                "hard_gate",
                "Camera hard gate",
                "hard_gate",
                FUSION_RUNNER,
                {
                    DEVICE_CUDA: "configs/sensors_fusion_hard_batch_gpu.yaml",
                    DEVICE_CPU: "configs/sensors_fusion_hard_batch_cpu.yaml",
                },
                True,
                "Radar đề xuất phanh, chỉ được phanh khi YOLO xác nhận có ô tô "
                "(giữ xác nhận 0.35 s). Chính xác cao, nhưng camera bỏ sót thì "
                "không phanh.",
            ),
        ),
        (
            "fallback",
            Policy(
                "fallback",
                "Gate + radar emergency fallback",
                "fallback",
                FUSION_RUNNER,
                {
                    DEVICE_CUDA: "configs/sensors_fusion_safe_fallback_batch_gpu.yaml",
                    DEVICE_CPU: "configs/sensors_fusion_safe_fallback_batch_cpu.yaml",
                },
                True,
                "Như hard gate, nhưng radar được tự phanh khi mục tiêu ổn định, "
                "ở giữa đường đi và nguy cấp (TTC/khoảng cách). Cứu ca camera "
                "bỏ sót, có thể nhận cả radar ma có nhiều điểm.",
            ),
        ),
    )
)


def policy(key):
    return POLICIES[key]


def sensor_config_for(policy_key, device):
    return POLICIES[policy_key].configs[device]


def policy_slug(policy_key, device):
    """Run-id fragment, e.g. ``radar_only`` or ``fallback_cuda``."""
    item = POLICIES[policy_key]
    if not item.uses_camera:
        return item.slug
    return "{}_{}".format(item.slug, device)


def classify_run(command, sensor_config, providers=None):
    """``(policy_key, device)`` of a past run from its metadata.

    Returns ``(None, None)`` when the run cannot be attributed.
    """
    command = str(command or "")
    sensor_name = str(sensor_config or "").rsplit("/", 1)[-1]
    providers = [str(item) for item in (providers or [])]
    if "run_radar_aeb_scenarios" in command:
        return "radar_only", None
    if "run_fusion_aeb_scenarios" not in command and not sensor_name.startswith(
        "sensors_fusion"
    ):
        return None, None
    if "safe_fallback" in sensor_name:
        key = "fallback"
    elif sensor_name.startswith("sensors_fusion") or "run_fusion" in command:
        key = "hard_gate"
    else:
        return None, None
    if sensor_name.endswith("_gpu.yaml"):
        device = DEVICE_CUDA
    elif sensor_name.endswith("_cpu.yaml"):
        device = DEVICE_CPU
    elif providers and providers[0].startswith("CUDA"):
        device = DEVICE_CUDA
    elif providers:
        device = DEVICE_CPU
    else:
        device = None
    return key, device


def run_label(policy_key, device, sensor_config=None):
    if policy_key is None:
        return "Không rõ"
    label = POLICIES[policy_key].label
    sensor_name = str(sensor_config or "").rsplit("/", 1)[-1]
    if sensor_name.startswith("sensors_fusion_hold_"):
        label += " (hold {})".format(sensor_name[len("sensors_fusion_hold_"):-5])
    if POLICIES[policy_key].uses_camera and device:
        label += " · " + device.upper()
    return label


SHORT_LABELS = {"radar_only": "Radar-only", "hard_gate": "Hard gate", "fallback": "Fallback"}


def short_run_label(policy_key, device):
    if policy_key is None:
        return "?"
    label = SHORT_LABELS[policy_key]
    if POLICIES[policy_key].uses_camera and device:
        label += " · " + device.upper()
    return label
