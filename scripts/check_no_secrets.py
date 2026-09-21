"""Fail CI if hardcoded secret-like defaults appear in tracked Python files."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Concrete leaked key formats
KEY_FORMATS = [
    re.compile(r"sk-or-v1-[a-f0-9]{20,}", re.I),
    re.compile(r"\brpa_[A-Za-z0-9]{20,}"),
    re.compile(r"\brps_[A-Za-z0-9]{20,}"),
]

# getenv("…API_KEY|SECRET…", "non-empty-default") is never OK
SECRET_GETENV_DEFAULT = re.compile(
    r"""os\.getenv\(\s*["'][^"']*(?:API_KEY|SECRET|ACCESS_KEY|PASSWORD|TOKEN)[^"']*["']\s*,\s*["'][^"']+["']""",
    re.I,
)

SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", "outputs", "temp_assets", "music"}


def main() -> int:
    hits: list[str] = []
    for path in ROOT.rglob("*.py"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        # Don't fail the scanner on itself
        if path.name == "check_no_secrets.py":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pat in KEY_FORMATS:
            if pat.search(text):
                hits.append(f"{path.relative_to(ROOT)}: key-format match")
                break
        else:
            if SECRET_GETENV_DEFAULT.search(text):
                hits.append(f"{path.relative_to(ROOT)}: secret getenv() default")

    if hits:
        print("Possible hardcoded secrets found:")
        for h in hits:
            print(f"  - {h}")
        return 1

    print("OK: no hardcoded secret patterns detected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
