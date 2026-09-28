#!/usr/bin/env python3
"""Safety policy checks for the pre-ROM EOS 2000D port state."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

FORBIDDEN_PRE_ROM_DEFINES = {
    "CONFIG_PROP_REQUEST_CHANGE",
    "CONFIG_DUMPER_BOOTFLAG",
    "CONFIG_RAW_LIVEVIEW",
    "CONFIG_RAW_PHOTO",
    "CONFIG_EDMAC_MEMCPY",
    "CONFIG_FRAME_ISO_OVERRIDE",
    "CONFIG_FRAME_SHUTTER_OVERRIDE",
    "CONFIG_DIGIC_POKE",
}

DEFINE_RE = re.compile(r"^\s*#\s*define\s+([A-Za-z_][A-Za-z0-9_]*)\b", re.MULTILINE)


def strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return re.sub(r"//.*", "", text)


def active_defines(text: str) -> set[str]:
    return set(DEFINE_RE.findall(strip_comments(text)))


def validate_pre_rom(root: Path) -> list[str]:
    errors: list[str] = []
    platform = root / "platform/2000D.130"

    combined = ""
    for name in ("internals.h", "features.h"):
        combined += "\n" + (platform / name).read_text(encoding="utf-8")

    active = active_defines(combined)
    for name in sorted(FORBIDDEN_PRE_ROM_DEFINES & active):
        errors.append(f"{name}: forbidden before ROM/runtime validation")

    features = strip_comments((platform / "features.h").read_text(encoding="utf-8"))
    if "all_features.h" in features:
        errors.append("features.h includes all_features.h during restricted bring-up")

    modules = (platform / "modules.included").read_text(encoding="utf-8")
    if any(line.split("#", 1)[0].strip() for line in modules.splitlines()):
        errors.append("modules.included must remain empty before restricted core validation")

    firs = list(platform.glob("*.FIR")) + list(platform.glob("*.fir"))
    if firs:
        errors.append("installer FIR present before release-hardening gate")

    rom_manifest = json.loads(
        (root / "docs/2000D-130/rom-manifest.json").read_text(encoding="utf-8")
    )
    if rom_manifest.get("canonical_image") is not None:
        errors.append(
            "pre-rom CI mode is stale: canonical ROM is now populated; update policy mode deliberately"
        )

    makefile = (platform / "Makefile").read_text(encoding="utf-8")
    for variable in ("PORT_MAIN_FIRMWARE_ADDR ?=", "PORT_RESTARTSTART ?=", "PORT_ML_BOOT_OBJ ?="):
        if variable not in makefile:
            errors.append(f"expected pre-ROM build guard missing: {variable}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--mode", choices=["pre-rom"], default="pre-rom")
    args = parser.parse_args()

    errors = validate_pre_rom(args.root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("pre-ROM port safety policy passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
