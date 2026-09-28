#!/usr/bin/env python3
"""Generate non-copyrighted metadata for an EOS 2000D firmware/ROM image.

This tool intentionally records hashes, sizes, version-string evidence and
basic entry-point metadata. It does not copy the ROM into the repository.

Example:
    python3 tools/eos2000d/rom_manifest.py ROM.BIN \
        --base 0xFE0C0000 \
        --output /tmp/2000d-130-manifest.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
from pathlib import Path
from typing import Any

DEFAULT_BASE = 0xFE0C0000
DEFAULT_EXPECTED_FIRST_WORD = 0xEA000001
DEFAULT_TERMS = (
    "1.3.0",
    "firmware",
    "version",
    "2000d",
    "1500d",
    "rebel t7",
    "kiss x90",
)


def _arm_branch_target(address: int, word: int) -> int | None:
    """Return ARM B/BL target for a 32-bit ARM instruction, if applicable."""
    if (word & 0x0E000000) != 0x0A000000:
        return None

    imm24 = word & 0x00FFFFFF
    if imm24 & 0x00800000:
        imm24 -= 0x01000000

    return (address + 8 + (imm24 << 2)) & 0xFFFFFFFF


def _ascii_evidence(data: bytes, base: int, terms: tuple[str, ...]) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    lowered_terms = tuple(term.lower() for term in terms)

    for match in re.finditer(rb"[\x20-\x7e]{6,}", data):
        text = match.group().decode("ascii", errors="replace")
        lowered = text.lower()
        if not any(term in lowered for term in lowered_terms):
            continue

        # Avoid making public manifests unnecessarily large.
        if len(text) > 240:
            text = text[:237] + "..."

        evidence.append(
            {
                "file_offset": f"0x{match.start():X}",
                "virtual_address": f"0x{base + match.start():08X}",
                "text": text,
            }
        )

        if len(evidence) >= 100:
            break

    return evidence


def inspect_image(path: Path, base: int = DEFAULT_BASE) -> dict[str, Any]:
    data = path.read_bytes()
    sha256 = hashlib.sha256(data).hexdigest()

    first_word = None
    branch_target = None
    if len(data) >= 4:
        first_word = struct.unpack_from("<I", data, 0)[0]
        branch_target = _arm_branch_target(base, first_word)

    return {
        "schema_version": 1,
        "target": {
            "camera": "Canon EOS 1500D / 2000D / Rebel T7",
            "firmware": "1.3.0",
        },
        "source": {
            # Keep local paths out of a manifest that may be committed.
            "filename": path.name,
            "byte_size": len(data),
            "sha256": sha256,
        },
        "mapping": {
            "assumed_base": f"0x{base:08X}",
            "first_word_le": None if first_word is None else f"0x{first_word:08X}",
            "expected_first_word": f"0x{DEFAULT_EXPECTED_FIRST_WORD:08X}",
            "expected_first_word_matches": first_word == DEFAULT_EXPECTED_FIRST_WORD,
            "decoded_first_branch_target": (
                None if branch_target is None else f"0x{branch_target:08X}"
            ),
        },
        "ascii_evidence": _ascii_evidence(data, base, DEFAULT_TERMS),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path, help="raw ROM/firmware image to inspect")
    parser.add_argument(
        "--base",
        type=lambda value: int(value, 0),
        default=DEFAULT_BASE,
        help="virtual base address for a raw ROM image (default: 0xFE0C0000)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="write JSON metadata to this path instead of stdout",
    )
    args = parser.parse_args()

    manifest = inspect_image(args.image, args.base)
    rendered = json.dumps(manifest, indent=2, sort_keys=True) + "\n"

    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
