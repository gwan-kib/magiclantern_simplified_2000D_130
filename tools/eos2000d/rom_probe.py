#!/usr/bin/env python3
"""Locally inspect words around candidate EOS 2000D ROM addresses.

This is an analyst convenience tool. Its output may contain firmware bytes and
should not be committed to the public repository without review.
"""

from __future__ import annotations

import argparse
import struct
from pathlib import Path

DEFAULT_BASE = 0xFE0C0000


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path)
    parser.add_argument("addresses", nargs="+", type=lambda value: int(value, 0))
    parser.add_argument("--base", type=lambda value: int(value, 0), default=DEFAULT_BASE)
    parser.add_argument("--words", type=int, default=4)
    args = parser.parse_args()

    data = args.image.read_bytes()

    for address in args.addresses:
        offset = address - args.base
        print(f"{address:#010x}  file+{offset:#x}")
        if offset < 0 or offset >= len(data):
            print("  outside image")
            continue

        for index in range(args.words):
            word_offset = offset + index * 4
            if word_offset + 4 > len(data):
                break
            word = struct.unpack_from("<I", data, word_offset)[0]
            print(
                f"  {args.base + word_offset:#010x}: "
                f"{word:#010x}  "
                f"{data[word_offset:word_offset + 4].hex(' ')}"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
