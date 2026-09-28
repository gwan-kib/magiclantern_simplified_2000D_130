#!/usr/bin/env python3
"""Require evidence records for active EOS 2000D firmware stubs."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

STUB_RE = re.compile(
    r"^\s*(?:NSTUB|THUMB_FN)\s*\(\s*(0x[0-9A-Fa-f]+|[0-9]+)\s*,\s*([A-Za-z_][A-Za-z0-9_]*)",
    re.MULTILINE,
)
VALID_STATUSES = {"rom-verified", "qemu-tested", "hardware-tested"}


def active_stubs(text: str) -> dict[str, int]:
    cleaned = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    cleaned = re.sub(r"//.*", "", cleaned)
    return {symbol: int(address, 0) for address, symbol in STUB_RE.findall(cleaned)}


def validate(stub_text: str, evidence: dict) -> list[str]:
    errors: list[str] = []
    active = active_stubs(stub_text)
    entries = {item.get("symbol"): item for item in evidence.get("stubs", [])}

    for symbol, address in active.items():
        item = entries.get(symbol)
        if not item:
            errors.append(f"{symbol}: active stub has no evidence entry")
            continue

        try:
            recorded_address = int(str(item.get("address")), 0)
        except (TypeError, ValueError):
            errors.append(f"{symbol}: evidence address is missing/invalid")
            continue

        if recorded_address != address:
            errors.append(
                f"{symbol}: stubs.S has 0x{address:X}, evidence has 0x{recorded_address:X}"
            )

        status = item.get("status")
        if status not in VALID_STATUSES:
            errors.append(f"{symbol}: invalid/unverified status {status!r}")

        rom_hash = item.get("rom_sha256") or evidence.get("canonical_rom_sha256")
        if not isinstance(rom_hash, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", rom_hash):
            errors.append(f"{symbol}: missing canonical 64-hex ROM SHA-256")

        proof = item.get("evidence")
        if not proof or not isinstance(proof, list):
            errors.append(f"{symbol}: evidence list is empty")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stubs", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()

    data = json.loads(args.evidence.read_text(encoding="utf-8"))
    errors = validate(args.stubs.read_text(encoding="utf-8"), data)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("stub evidence check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
