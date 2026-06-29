#!/usr/bin/env python3
from pathlib import Path

REPORT_DIR = Path(__file__).resolve().parent
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
    path = REPORT_DIR / "chapters" / name
    text = path.read_text(encoding="utf-8").strip()
    text = text.replace("../assets/", "assets/")
    text = text.replace("../../outputs/", "../outputs/")
    text = text.replace("../../logs/", "../logs/")
    text = text.replace("../../training_runs/", "../training_runs/")
    parts.append(text)

out = "\n\n".join(parts).rstrip() + "\n"
(REPORT_DIR / "report.md").write_text(out, encoding="utf-8")
print(f"Built {(REPORT_DIR / 'report.md').relative_to(REPORT_DIR.parent)} from {len(CHAPTERS)} chapter files")
