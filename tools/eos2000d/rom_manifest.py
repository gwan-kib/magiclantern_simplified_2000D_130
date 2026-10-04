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

DEFAULT_BASE = None  # A bank base cannot be inferred from a firmware entry.
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


def _ascii_evidence(data: bytes, base: int | None, terms: tuple[str, ...]) -> list[dict[str, Any]]:
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
                "virtual_address": None if base is None else f"0x{base + match.start():08X}",
                "text": text,
            }
        )

        if len(evidence) >= 100:
            break

    return evidence


def inspect_image(
    path: Path, base: int | None = DEFAULT_BASE, *, main_offset: int = 0,
    aliases: tuple[int, ...] = (), firmware: str | None = None,
) -> dict[str, Any]:
    data = path.read_bytes()
    sha256 = hashlib.sha256(data).hexdigest()

    if main_offset < 0 or main_offset + 4 > len(data):
        raise ValueError("main firmware offset must point to a complete word in the image")
    for address in (() if base is None else (base,)) + aliases:
        if address < 0 or address + len(data) > 0x100000000:
            raise ValueError("ROM bank/alias interval must fit in the 32-bit address space")
    if aliases and base is None:
        raise ValueError("alias addresses require an explicit ROM bank base")

    first_word = None
    branch_target = None
    if len(data) >= 4:
        first_word = struct.unpack_from("<I", data, 0)[0]
        branch_target = None if base is None else _arm_branch_target(base, first_word)
    entry_word = struct.unpack_from("<I", data, main_offset)[0]
    entry_address = None if base is None else base + main_offset

    return {
        "schema_version": 2,
        "target": {
            "camera": "Canon EOS 1500D / 2000D / Rebel T7",
            "firmware": firmware,
        },
        "source": {
            # Keep local paths out of a manifest that may be committed.
            "filename": path.name,
            "byte_size": len(data),
            "sha256": sha256,
            "md5": hashlib.md5(data).hexdigest(),
        },
        "mapping": {
            "bank_base": None if base is None else f"0x{base:08X}",
            "main_firmware_offset": f"0x{main_offset:X}",
            "main_firmware_address": None if entry_address is None else f"0x{entry_address:08X}",
            "entry_word_le": f"0x{entry_word:08X}",
            "entry_word_matches": entry_word == DEFAULT_EXPECTED_FIRST_WORD,
            "decoded_entry_branch_target": None if entry_address is None else (
                None if (target := _arm_branch_target(entry_address, entry_word)) is None else f"0x{target:08X}"
            ),
            "aliases": [
                {
                    "bank_base": f"0x{alias:08X}",
                    "main_firmware_address": f"0x{alias + main_offset:08X}",
                    "decoded_entry_branch_target": None if (target := _arm_branch_target(alias + main_offset, entry_word)) is None else f"0x{target:08X}",
                }
                for alias in aliases
            ],
            "first_word_le": None if first_word is None else f"0x{first_word:08X}",
            "expected_first_word": f"0x{DEFAULT_EXPECTED_FIRST_WORD:08X}",
            "expected_first_word_matches": first_word == DEFAULT_EXPECTED_FIRST_WORD,
            "decoded_first_branch_target": (
                None if branch_target is None else f"0x{branch_target:08X}"
            ),
        },
        "ascii_evidence": _ascii_evidence(data, base, DEFAULT_TERMS + (() if firmware is None else (firmware,))),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path, help="raw ROM/firmware image to inspect")
    parser.add_argument(
        "--bank-base", "--base",
        dest="base",
        type=lambda value: int(value, 0),
        default=DEFAULT_BASE,
        help="address of image byte zero; --base is a compatibility alias (no inferred default)",
    )
    parser.add_argument("--main-offset", type=lambda value: int(value, 0), default=0)
    parser.add_argument("--alias-base", type=lambda value: int(value, 0), action="append", default=[])
    parser.add_argument("--firmware", help="analyst-supplied firmware label; confirm independently")
    parser.add_argument(
        "--output",
        type=Path,
        help="write JSON metadata to this path instead of stdout",
    )
    args = parser.parse_args()

    try:
        manifest = inspect_image(args.image, args.base, main_offset=args.main_offset,
                                 aliases=tuple(args.alias_base), firmware=args.firmware)
    except ValueError as exc:
        parser.error(str(exc))
    rendered = json.dumps(manifest, indent=2, sort_keys=True) + "\n"

    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
