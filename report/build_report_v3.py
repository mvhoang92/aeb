#!/usr/bin/env python3
"""Build report_v3.md from the versioned chapter sources."""

from pathlib import Path


REPORT_DIR = Path(__file__).resolve().parent
SOURCE_DIR = REPORT_DIR / "chapters_v3"
CHAPTERS = [
    "00_front_matter.md",
    "01_tong_quan.md",
    "02_thiet_lap_moi_truong_mo_phong.md",
    "03_trien_khai_thuat_toan.md",
    "04_kiem_thu_danh_gia.md",
    "05_ket_luan.md",
    "99_tai_lieu_tham_khao_phu_luc.md",
]

parts = []
for name in CHAPTERS:
    text = (SOURCE_DIR / name).read_text(encoding="utf-8").strip()
    text = text.replace("../assets/", "assets/")
    text = text.replace("../../outputs/", "../outputs/")
    text = text.replace("../../logs/", "../logs/")
    text = text.replace("../../training_runs/", "../training_runs/")
    parts.append(text)

output = "\n\n".join(parts).rstrip() + "\n"
path = REPORT_DIR / "report_v3.md"
path.write_text(output, encoding="utf-8")
print("Built {} from {} chapter files".format(path.relative_to(REPORT_DIR.parent), len(CHAPTERS)))
