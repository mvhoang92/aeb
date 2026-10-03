"""Scenario catalogue: read-only view of ``configs/scenarios`` (no Tk).

Every scenario is identified by ``(suite, id)`` where ``suite`` is the
repo-relative YAML path: the same id (for example ``clear_road_50``) appears in
several suites with different runner settings, so the id alone is ambiguous.
"""

from __future__ import absolute_import

from collections import OrderedDict, namedtuple
from pathlib import Path

import yaml

from ui.testbench.paths import AEB_ROOT


EXPECT_ALL = "all"
EXPECT_BRAKE = "brake"
EXPECT_NO_BRAKE = "no_brake"
EXPECT_COLLISION_OK = "collision_ok"

EXPECTATION_LABELS = OrderedDict(
    (
        (EXPECT_ALL, "Tất cả"),
        (EXPECT_BRAKE, "Phải phanh"),
        (EXPECT_NO_BRAKE, "Không được phanh"),
        (EXPECT_COLLISION_OK, "Va chạm chấp nhận được"),
    )
)

# (key, label, order).  Must-brake groups first, then must-not-brake groups.
GROUPS = OrderedDict(
    (
        ("ccrs", ("CCRs · xe trước đứng yên", 10)),
        ("ccrm", ("CCRm · xe trước chạy chậm hơn", 20)),
        ("ccrb", ("CCRb · xe trước phanh gấp", 30)),
        ("cut_in", ("Cut-in · xe chen vào làn", 40)),
        ("multi", ("Nhiều xe · chọn đúng mục tiêu", 50)),
        ("hazard", ("Vật cản không phải xe ở giữa làn", 60)),
        ("cut_out", ("Cut-out · xe trước rời làn", 70)),
        ("clear", ("Đường trống · không được phanh", 80)),
        ("ghost", ("Radar ma tổng hợp · không được phanh", 90)),
        ("adjacent", ("Xe đỗ ở làn bên · không được phanh", 100)),
        ("roadside", ("Vật ven đường · không được phanh", 110)),
        ("non_closing", ("Xe trước chạy nhanh hơn · không được phanh", 120)),
    )
)

SuiteInfo = namedtuple("SuiteInfo", "title summary tags order")

# Plain-language summaries of the tracked suites.  Unknown files still load;
# they fall back to the file name and the YAML header comment.
SUITE_INFO = {
    "smoke_basic": SuiteInfo(
        "Smoke cơ bản",
        "5 tình huống cơ bản (đường trống, CCRs, CCRm, CCRb, xe làn bên) để "
        "kiểm tra nhanh toàn bộ chuỗi chạy trước một chiến dịch dài.",
        ("smoke",),
        10,
    ),
    "radar_only_regression": SuiteInfo(
        "Hồi quy radar-only",
        "Bộ hồi quy: đường trống, CCRs/CCRm/CCRb, xe làn bên, đường cong, "
        "cut-in/cut-out, nhiều xe. Thuộc phạm vi core của paper.",
        ("core",),
        20,
    ),
    "system_limit_extended_sweep": SuiteInfo(
        "Quét giới hạn hệ thống (mở rộng)",
        "Lưới tốc độ × khoảng cách cho CCRm, CCRb và cut-in để tìm biên vận "
        "hành. Thuộc phạm vi core của paper.",
        ("core",),
        21,
    ),
    "fusion_physical_false_positive_v2": SuiteInfo(
        "Vật ven đường v2 (false-positive)",
        "Vật thể tĩnh sát mép làn, không nguy hiểm: AEB không được phanh. "
        "Thuộc phạm vi core của paper.",
        ("core",),
        22,
    ),
    "fusion_nonvehicle_hazard_limitation": SuiteInfo(
        "Giới hạn: vật cản không phải xe",
        "Hộp/thùng nằm giữa làn là nguy hiểm thật, phải phanh. Bộc lộ giới hạn "
        "của cổng camera chỉ xác nhận ô tô. Thuộc phạm vi core của paper.",
        ("core",),
        23,
    ),
    "fusion_fallback_holdout": SuiteInfo(
        "Hold-out đóng băng",
        "Tình huống chưa từng dùng để chỉnh tham số (vật thể/xe mới, radar ma "
        "nhiều điểm). Chỉ để đánh giá; không chỉnh tham số theo kết quả.",
        ("holdout",),
        30,
    ),
    "fusion_regression": SuiteInfo(
        "Hồi quy fusion (giới hạn vận hành)",
        "CCRs/CCRm/CCRb trong vùng vận hành, khoảng cách ngắn và "
        "false-positive trên đường cong.",
        (),
        40,
    ),
    "fusion_fallback_development": SuiteInfo(
        "Phát triển fallback (dev)",
        "Tình huống dùng để phát triển/ablation fallback; không phải hold-out.",
        ("dev",),
        41,
    ),
    "fusion_perturbation_robustness": SuiteInfo(
        "Nhiễu loạn quanh điểm danh định",
        "Biến thể ± tốc độ / khoảng cách / thời điểm quanh các ca phát triển; "
        "mỗi ID là một điều kiện riêng, lặp lại chỉ đo tính nhất quán.",
        (),
        42,
    ),
    "fusion_benefit_stress": SuiteInfo(
        "Stress radar ma tổng hợp",
        "Tiêm điểm radar giả (synthetic fault injection) trước xe. Không phải "
        "ước lượng tần suất radar ma thật của CARLA.",
        ("synthetic",),
        43,
    ),
    "fusion_physical_false_positive": SuiteInfo(
        "Cọc giao thông ven đường (v1)",
        "Cọc giao thông sát mép làn, không nguy hiểm: không được phanh.",
        (),
        44,
    ),
    "fusion_camera_degradation": SuiteInfo(
        "Camera suy giảm (detector tắt)",
        "Dành cho biến thể sensor tắt detector do campaign tạo ra. Chạy với "
        "cấu hình thường sẽ KHÔNG tái hiện điều kiện camera tắt.",
        ("needs_variant",),
        45,
    ),
    "system_limit_ccrs_sweep": SuiteInfo(
        "Quét giới hạn CCRs",
        "CCRs: tốc độ ego 40–110 km/h × khoảng cách 20–100 m.",
        (),
        50,
    ),
    "report_demo": SuiteInfo(
        "Demo cho báo cáo",
        "Các ca tiêu biểu (CCRs/CCRm/CCRb/cut-in tốc độ cao) dùng trong báo cáo.",
        (),
        60,
    ),
    "final_evidence_video": SuiteInfo(
        "Video bằng chứng cuối",
        "Các ca dùng để quay video bằng chứng cuối.",
        (),
        61,
    ),
    "clear_road": SuiteInfo("Theo loại · đường trống", "", (), 100),
    "adjacent_vehicle": SuiteInfo("Theo loại · xe đỗ làn bên", "", (), 101),
    "ccrs_stationary_lead": SuiteInfo("Theo loại · CCRs xe đứng yên", "", (), 102),
    "ccrm_moving_lead": SuiteInfo("Theo loại · CCRm xe chậm hơn", "", (), 103),
    "ccrb_braking_lead": SuiteInfo("Theo loại · CCRb xe phanh gấp", "", (), 104),
    "cut_in": SuiteInfo("Theo loại · cut-in", "", (), 105),
    "cut_out": SuiteInfo("Theo loại · cut-out", "", (), 106),
    "curve_cases": SuiteInfo("Theo loại · đường cong", "", (), 107),
    "multi_actor": SuiteInfo("Theo loại · nhiều xe", "", (), 108),
}

TAG_LABELS = {
    "smoke": "smoke",
    "core": "core paper",
    "holdout": "hold-out",
    "dev": "phát triển",
    "synthetic": "lỗi tổng hợp",
    "needs_variant": "cần sensor đặc biệt",
}


def _as_float(value):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _hazard_actor(raw):
    actors = raw.get("actors") or []
    for actor in actors:
        if isinstance(actor, dict) and actor.get("hazard"):
            return actor
    for actor in actors:
        if isinstance(actor, dict):
            return actor
    return None


def group_key(raw):
    """Plain-language group of a scenario, derived from ``type``/expectation."""
    kind = str(raw.get("type", "")).strip()
    brake = bool(raw.get("expected_brake", False))
    if kind == "stationary_lead":
        return "ccrs"
    if kind == "moving_lead":
        return "ccrm" if brake else "non_closing"
    if kind == "braking_lead":
        return "ccrb"
    if kind == "cut_in":
        return "cut_in"
    if kind == "cut_out":
        return "cut_out"
    if kind == "multi_actor":
        return "multi"
    if kind == "physical_hazard":
        return "hazard"
    if kind == "physical_false_positive":
        return "roadside"
    if kind == "adjacent_stationary":
        return "adjacent"
    if kind == "clear_road":
        return "ghost" if raw.get("synthetic_radar_points") else "clear"
    return kind or "other"


def group_label(key):
    if key in GROUPS:
        return GROUPS[key][0]
    return "Loại khác · {}".format(key)


def group_order(key):
    return GROUPS[key][1] if key in GROUPS else 999


class Scenario(object):
    """One named condition of one suite file."""

    __slots__ = (
        "suite",
        "id",
        "type",
        "description",
        "expected_brake",
        "expected_collision",
        "ego_speed_kph",
        "target_speed_kph",
        "initial_gap_m",
        "duration_s",
        "control_modes",
        "group",
        "raw",
    )

    def __init__(self, suite, raw):
        self.suite = suite
        self.raw = raw
        self.id = str(raw["id"])
        self.type = str(raw.get("type", ""))
        self.description = str(raw.get("description", "") or "")
        self.expected_brake = bool(raw.get("expected_brake", False))
        self.expected_collision = bool(raw.get("expected_collision", False))
        self.ego_speed_kph = _as_float(raw.get("ego_speed_kph"))
        self.target_speed_kph = _as_float(raw.get("target_speed_kph"))
        self.initial_gap_m = _as_float(raw.get("initial_gap_m"))
        self.duration_s = _as_float(raw.get("duration_s")) or 0.0
        self.control_modes = tuple(str(mode) for mode in raw.get("control_modes") or ())
        self.group = group_key(raw)

    @property
    def key(self):
        return (self.suite, self.id)

    def supports_mode(self, control_mode):
        return not self.control_modes or control_mode in self.control_modes

    def matches_expectation(self, expectation):
        if expectation == EXPECT_BRAKE:
            return self.expected_brake
        if expectation == EXPECT_NO_BRAKE:
            return not self.expected_brake
        if expectation == EXPECT_COLLISION_OK:
            return self.expected_collision
        return True

    def search_text(self):
        return " ".join(
            (
                self.id,
                self.type,
                self.description,
                group_label(self.group),
                self.suite,
            )
        ).lower()

    def __repr__(self):
        return "Scenario({!r}, {!r})".format(self.suite, self.id)


class Suite(object):
    """One scenario YAML file."""

    def __init__(self, path, data, root=AEB_ROOT):
        path = Path(path)
        self.path = path
        try:
            self.rel = path.resolve().relative_to(Path(root).resolve()).as_posix()
        except ValueError:
            self.rel = str(path)
        self.stem = path.stem
        self.category = path.parent.name
        runner = data.get("runner") if isinstance(data.get("runner"), dict) else {}
        # Mirrors ScenarioRunner: only ``runner.control_mode`` is read; a suite
        # without a ``runner`` block runs deterministic unless overridden.
        self.default_control_mode = str(runner.get("control_mode", "deterministic"))
        self.map = str(runner.get("map", data.get("map", "Town04")))
        info = SUITE_INFO.get(self.stem)
        self.header = _header_comment(path)
        if info is None:
            info = SuiteInfo(self.stem, self.header, (), 500)
        self.title = info.title
        self.summary = info.summary or self.header
        self.tags = tuple(info.tags)
        self.order = info.order
        self.scenarios = [
            Scenario(self.rel, item)
            for item in data.get("scenarios") or []
            if isinstance(item, dict) and item.get("id")
        ]

    def scenario_ids(self):
        return [scenario.id for scenario in self.scenarios]

    def groups(self, scenarios=None):
        """``[(group_key, [scenarios])]`` in display order, YAML order inside."""
        grouped = OrderedDict()
        for scenario in self.scenarios if scenarios is None else scenarios:
            grouped.setdefault(scenario.group, []).append(scenario)
        return sorted(grouped.items(), key=lambda item: group_order(item[0]))

    def __repr__(self):
        return "Suite({!r}, {} scenarios)".format(self.rel, len(self.scenarios))


def _header_comment(path):
    lines = []
    try:
        with open(str(path), encoding="utf-8") as stream:
            for line in stream:
                stripped = line.strip()
                if not stripped.startswith("#"):
                    break
                lines.append(stripped.lstrip("#").strip())
    except (IOError, OSError):
        return ""
    return " ".join(line for line in lines if line)


class Catalog(object):
    """All suites under ``configs/scenarios`` plus lookup and filtering."""

    def __init__(self, suites):
        self.suites = sorted(suites, key=lambda suite: (suite.order, suite.rel))
        self._by_rel = OrderedDict((suite.rel, suite) for suite in self.suites)
        self._by_key = {}
        for suite in self.suites:
            for scenario in suite.scenarios:
                self._by_key[scenario.key] = scenario

    @classmethod
    def load(cls, scenario_root=None, root=AEB_ROOT):
        scenario_root = Path(scenario_root or Path(root) / "configs" / "scenarios")
        suites = []
        for path in sorted(scenario_root.glob("**/*.yaml")):
            with open(str(path), encoding="utf-8") as stream:
                data = yaml.safe_load(stream) or {}
            if isinstance(data, dict) and data.get("scenarios"):
                suites.append(Suite(path, data, root=root))
        return cls(suites)

    def suite(self, rel):
        return self._by_rel[rel]

    def find_suite(self, name):
        """Suite by repo-relative path, path tail or stem."""
        if name in self._by_rel:
            return self._by_rel[name]
        for suite in self.suites:
            if suite.rel.endswith("/" + name) or suite.stem == name:
                return suite
        raise KeyError(name)

    def scenario(self, key):
        return self._by_key[tuple(key)]

    def all_keys(self):
        return [scenario.key for suite in self.suites for scenario in suite.scenarios]

    def filter(self, text="", expectation=EXPECT_ALL, only_keys=None):
        """``OrderedDict(suite_rel -> [scenarios])`` of matching scenarios.

        ``text`` is split on whitespace and every token must occur in the id,
        description, type, group label or suite path (case-insensitive).
        """
        tokens = [token for token in str(text or "").lower().split() if token]
        result = OrderedDict()
        for suite in self.suites:
            suite_text = (suite.title + " " + suite.rel).lower()
            matched = []
            for scenario in suite.scenarios:
                if only_keys is not None and scenario.key not in only_keys:
                    continue
                if not scenario.matches_expectation(expectation):
                    continue
                haystack = scenario.search_text() + " " + suite_text
                if all(token in haystack for token in tokens):
                    matched.append(scenario)
            if matched:
                result[suite.rel] = matched
        return result

    def expectation_counts(self):
        counts = OrderedDict((key, 0) for key in EXPECTATION_LABELS)
        for suite in self.suites:
            for scenario in suite.scenarios:
                for key in counts:
                    if scenario.matches_expectation(key):
                        counts[key] += 1
        return counts


def _fmt(value, unit):
    """``28 m`` / ``8.4 s``: shortest exact form, unit appended."""
    if value is None:
        return None
    return "{:g} {}".format(float(value), unit)


def expectation_text(scenario):
    brake = "Phải phanh" if scenario.expected_brake else "Không được phanh"
    collision = (
        "va chạm chấp nhận được"
        if scenario.expected_collision
        else "không được va chạm"
    )
    return "{} · {}".format(brake, collision)


def scenario_facts(scenario):
    """``[(label, value)]`` describing a scenario in plain Vietnamese."""
    raw = scenario.raw
    facts = [("Nhóm", group_label(scenario.group))]
    if scenario.ego_speed_kph is not None:
        facts.append(("Tốc độ xe thử (ego)", _fmt(scenario.ego_speed_kph, "km/h")))
    if scenario.target_speed_kph is not None:
        speed = _fmt(scenario.target_speed_kph, "km/h")
        if scenario.target_speed_kph == 0:
            speed += " (đứng yên)"
        facts.append(("Tốc độ xe mục tiêu", speed))
    if scenario.initial_gap_m is not None:
        facts.append(("Khoảng cách ban đầu", _fmt(scenario.initial_gap_m, "m")))
    if raw.get("target_brake_time_s") is not None:
        facts.append(
            (
                "Xe trước phanh",
                "tại {} với lực {}".format(
                    _fmt(_as_float(raw.get("target_brake_time_s")), "s"),
                    raw.get("target_brake", "?"),
                ),
            )
        )
    actor = _hazard_actor(raw)
    if actor is not None:
        parts = [str(actor.get("role") or "actor")]
        if actor.get("blueprint"):
            parts.append(str(actor.get("blueprint")))
        if actor.get("speed_kph") is not None:
            parts.append(_fmt(_as_float(actor.get("speed_kph")), "km/h"))
        if actor.get("initial_gap_m") is not None:
            parts.append("gap " + _fmt(_as_float(actor.get("initial_gap_m")), "m"))
        offset = _as_float(actor.get("lateral_offset_m"))
        if offset:
            parts.append("lệch ngang {:+.2f} m".format(offset))
        lane_change = actor.get("lane_change")
        if isinstance(lane_change, dict) and lane_change.get("start_s") is not None:
            parts.append(
                "đổi làn tại {} s".format(lane_change.get("start_s"))
            )
        label = "Tác nhân chính" if actor.get("hazard") else "Tác nhân"
        actors = raw.get("actors") or []
        if len(actors) > 1:
            label += " (1/{})".format(len(actors))
        facts.append((label, ", ".join(parts)))
    points = raw.get("synthetic_radar_points") or []
    if points:
        first = points[0] if isinstance(points[0], dict) else {}
        facts.append(
            (
                "Radar ma tổng hợp",
                "{} cụm, {} điểm ở {} phía trước".format(
                    len(points),
                    first.get("count", "?"),
                    _fmt(_as_float(first.get("x_forward_m")), "m") or "?",
                ),
            )
        )
    facts.append(("Thời lượng tối đa", _fmt(scenario.duration_s, "s")))
    facts.append(("Kỳ vọng", expectation_text(scenario)))
    if raw.get("min_stop_gap_m") is not None:
        facts.append(
            ("Khoảng dừng tối thiểu", _fmt(_as_float(raw.get("min_stop_gap_m")), "m"))
        )
    if scenario.control_modes:
        facts.append(("Chỉ chạy ở chế độ", ", ".join(scenario.control_modes)))
    facts.append(("File · id", "{} · {}".format(scenario.suite, scenario.id)))
    return facts
