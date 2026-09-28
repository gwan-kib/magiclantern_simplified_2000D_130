#!/usr/bin/env python3
"""Enforce the explicit EOS 2000D feature/module evidence allowlist."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

DEFINE_RE = re.compile(r"^\s*#\s*define\s+(FEATURE_[A-Za-z0-9_]+)\b", re.MULTILINE)
ALLOWED_ENABLED_STATUSES = {"Compiles", "QEMU-tested", "Hardware-tested", "Experimental", "Stable"}


def strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return re.sub(r"//.*", "", text)


def enabled_features(text: str) -> set[str]:
    return set(DEFINE_RE.findall(strip_comments(text)))


def included_modules(text: str) -> set[str]:
    modules = set()
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            modules.add(line)
    return modules


def validate(features_text: str, modules_text: str, matrix: dict) -> list[str]:
    errors: list[str] = []
    clean_features = strip_comments(features_text)

    if re.search(r'^\s*#\s*include\s+["<]all_features\.h[">]', clean_features, re.MULTILINE):
        errors.append('features.h must remain an explicit allowlist; all_features.h is forbidden during bring-up')

    matrix_features = {item.get("name"): item for item in matrix.get("features", [])}
    for name in sorted(enabled_features(features_text)):
        item = matrix_features.get(name)
        if not item:
            errors.append(f"{name}: enabled but missing from feature matrix")
            continue
        if item.get("status") not in ALLOWED_ENABLED_STATUSES:
            errors.append(f"{name}: enabled while matrix status is {item.get('status')!r}")
        evidence = item.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            errors.append(f"{name}: enabled without supporting evidence")

    matrix_modules = {item.get("name"): item for item in matrix.get("modules", [])}
    for name in sorted(included_modules(modules_text)):
        item = matrix_modules.get(name)
        if not item:
            errors.append(f"module {name}: included but missing from matrix")
            continue
        if item.get("status") not in ALLOWED_ENABLED_STATUSES:
            errors.append(f"module {name}: included while matrix status is {item.get('status')!r}")
        if not item.get("evidence"):
            errors.append(f"module {name}: included without supporting evidence")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--modules", type=Path, required=True)
    parser.add_argument("--matrix", type=Path, required=True)
    args = parser.parse_args()

    errors = validate(
        args.features.read_text(encoding="utf-8"),
        args.modules.read_text(encoding="utf-8"),
        json.loads(args.matrix.read_text(encoding="utf-8")),
    )
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("feature matrix check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
