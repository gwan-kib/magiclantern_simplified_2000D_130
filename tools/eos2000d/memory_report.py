#!/usr/bin/env python3
"""Analyze structured EOS 2000D memory-validation records."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def overlaps(a: dict, b: dict) -> bool:
    return int(a["start"]) < int(b["end"]) and int(b["start"]) < int(a["end"])


def analyze(records: list[dict], drift_limit: int = 0) -> list[str]:
    errors: list[str] = []
    if not records:
        return ["no memory records supplied"]

    free_values: list[int] = []

    for index, record in enumerate(records):
        prefix = f"record {index}"
        ml = record.get("ml_region")
        if ml:
            if int(ml["start"]) >= int(ml["end"]):
                errors.append(f"{prefix}: invalid ML region")
            for region in record.get("canon_regions", []):
                if int(region["start"]) >= int(region["end"]):
                    errors.append(f"{prefix}: invalid Canon region {region.get('name')!r}")
                    continue
                if overlaps(ml, region):
                    errors.append(
                        f"{prefix}: ML region overlaps Canon region {region.get('name')!r}"
                    )

        if record.get("canary_ok") is False:
            errors.append(f"{prefix}: canary failure")

        if record.get("free_memory") is not None:
            free_values.append(int(record["free_memory"]))

    if len(free_values) >= 2:
        drift = max(free_values) - min(free_values)
        if drift > drift_limit:
            errors.append(f"free-memory drift {drift} exceeds limit {drift_limit}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--drift-limit", type=int, default=0)
    args = parser.parse_args()

    records = json.loads(args.input.read_text(encoding="utf-8"))
    errors = analyze(records, args.drift_limit)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("memory report passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
