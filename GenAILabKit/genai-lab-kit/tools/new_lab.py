"""Scaffold a new lab from lab-template/.

Usage:
    python tools/new_lab.py <lab-id> --title "Lab Title" --track agentic-ai

Creates  labs/<lab-id>/  as a copy of  lab-template/  with the id/title/track
substituted into lab.yaml. Refuses to overwrite an existing lab.
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
TEMPLATE = KIT / "lab-template"
LABS = KIT / "labs"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("lab_id", help="kebab-case id, also the folder name")
    ap.add_argument("--title", required=True)
    ap.add_argument("--track", default="genai", choices=["genai", "agentic-ai"])
    ap.add_argument("--difficulty", default="beginner",
                    choices=["beginner", "intermediate", "advanced"])
    ap.add_argument("--duration", type=int, default=90)
    args = ap.parse_args()

    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", args.lab_id):
        print("lab_id must be kebab-case (a-z, 0-9, hyphens).")
        return 1

    dest = LABS / args.lab_id
    if dest.exists():
        print(f"Refusing to overwrite existing lab: {dest}")
        return 1

    shutil.copytree(TEMPLATE, dest,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc",
                                                  ".ipynb_checkpoints"))

    manifest = dest / "lab.yaml"
    text = manifest.read_text(encoding="utf-8")
    text = text.replace("<kebab-case-id>", args.lab_id)
    text = text.replace("<Human Readable Title>", args.title)
    text = re.sub(r"^track: .*$", f"track: {args.track}", text, count=1, flags=re.M)
    text = re.sub(r"^difficulty: .*$", f"difficulty: {args.difficulty}", text,
                  count=1, flags=re.M)
    text = re.sub(r"^duration_minutes: .*$", f"duration_minutes: {args.duration}",
                  text, count=1, flags=re.M)
    manifest.write_text(text, encoding="utf-8")

    for md in ("README.md", "00_START_HERE.md", "01_TASK_GUIDE/TASKS.md"):
        p = dest / md
        p.write_text(p.read_text(encoding="utf-8").replace("<Lab Title>", args.title),
                     encoding="utf-8")

    print(f"Created {dest.relative_to(KIT)}")
    print("Next:")
    print("  1. edit lab.yaml (tasks, models, data, validation)")
    print("  2. drop datasets into 04_DATA/ and list them in lab.yaml")
    print("  3. write the notebooks in 02_STARTER_CODE/ and 03_SOLUTION_GUIDE/")
    print("  4. wire scripts/setup_check.py and scripts/validate_solution.py")
    print("  5. run  python tools/aggregate_requirements.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
