#!/usr/bin/env python3
"""Add a provisional EOS 2000D model to reticulatedpines/qemu-eos.

Target source:
    reticulatedpines/qemu-eos, branch qemu-eos-v4.2.1

This modifies emulator source only. The model parameters are a QEMU bring-up
starting point based on the existing 1300D model and historical 2000D.110
evidence. They are NOT verified Canon 2000D firmware 1.3.0 platform constants
and must not be copied into Magic Lantern's physical-camera platform files.
"""

from __future__ import annotations

import argparse
from pathlib import Path

MODEL_DEFINE = '#define MODEL_NAME_2000D "2000D"'

MODEL_BLOCK = r'''    {
        /*
         * EOS 2000D / 1500D / Rebel T7 — provisional QEMU bring-up model.
         *
         * Values below intentionally start from qemu-eos' late DIGIC IV
         * 1300D model, cross-checked where possible against historical
         * 2000D.110 Magic Lantern data. They require validation against the
         * canonical 2000D firmware 1.3.0 images and QEMU traces.
         */
        .name                   = MODEL_NAME_2000D,
        .digic_version          = 4,
        .ram_size               = 0x10000000,   /* provisional: 256MB */
        .rom0_size              = 0x02000000,   /* provisional: 32MB */
        .rom1_size              = 0x02000000,   /* provisional: 32MB */
        .firmware_start         = 0xFF0C0000,   /* qemu-eos D4 late-body convention; verify */
        .firmware_version       = 130,
        .dryos_timer_id         = 1,            /* provisional: copied from 1300D */
        .dryos_timer_interrupt  = 0x09,         /* provisional: copied from 1300D */
        .mpu_request_register   = 0xC022D0C4,   /* provisional */
        .mpu_request_bitmask    = 0x00100000,   /* provisional */
        .mpu_status_register    = 0xC022F484,   /* provisional */
        .current_task_addr      = 0x31170,       /* matches historical 2000D.110 and 1300D.110 */
        .sd_driver_interrupt    = 0x4B,          /* provisional */
        .sd_dma_interrupt       = 0x32,          /* provisional */
        .card_led_address       = 0xC0220134,    /* historical 2000D.110 + 1300D.110 */
        .uart_rx_interrupt      = 0x38,          /* provisional */
        .rtc_time_correct       = 0xFD,          /* provisional */
        .rtc_cs_register        = 0xC022D0B8,    /* provisional */
        .dedicated_movie_mode   = 1,
    },
'''

MACHINE_INIT = r'''static void eos_2000D_machine_init(MachineClass *mc)
{
    mc->desc = "Canon EOS 2000D / Rebel T7 (provisional)";
    mc->init = eos_init;
}

'''


class PatchError(RuntimeError):
    pass


def _insert_once(text: str, marker: str, insertion: str, already: str) -> str:
    if already in text:
        return text
    if marker not in text:
        raise PatchError(f"required anchor not found: {marker!r}")
    return text.replace(marker, insertion + marker, 1)


def patch_texts(model_h: str, model_c: str, eos_c: str) -> tuple[str, str, str]:
    model_h = _insert_once(
        model_h,
        '#define MODEL_NAME_A1100 "A1100"',
        MODEL_DEFINE + "\n",
        MODEL_DEFINE,
    )

    model_c = _insert_once(
        model_c,
        "    {\n        .name                   = MODEL_NAME_A1100,",
        MODEL_BLOCK,
        ".name                   = MODEL_NAME_2000D,",
    )

    eos_c = _insert_once(
        eos_c,
        "static void eos_A1100_machine_init(MachineClass *mc)",
        MACHINE_INIT,
        "static void eos_2000D_machine_init(MachineClass *mc)",
    )

    eos_c = _insert_once(
        eos_c,
        "DEFINE_MACHINE(MODEL_NAME_A1100, eos_A1100_machine_init)",
        "DEFINE_MACHINE(MODEL_NAME_2000D, eos_2000D_machine_init)\n",
        "DEFINE_MACHINE(MODEL_NAME_2000D, eos_2000D_machine_init)",
    )

    return model_h, model_c, eos_c


def patch_tree(root: Path, check_only: bool = False) -> bool:
    targets = {
        "model_h": root / "hw/eos/model_list.h",
        "model_c": root / "hw/eos/model_list.c",
        "eos_c": root / "hw/eos/eos.c",
    }
    missing = [str(path) for path in targets.values() if not path.is_file()]
    if missing:
        raise PatchError("qemu-eos source files not found: " + ", ".join(missing))

    original = {key: path.read_text(encoding="utf-8") for key, path in targets.items()}
    patched = dict(zip(
        ("model_h", "model_c", "eos_c"),
        patch_texts(original["model_h"], original["model_c"], original["eos_c"]),
    ))

    changed = any(original[key] != patched[key] for key in original)
    if check_only:
        return changed

    for key, path in targets.items():
        if original[key] != patched[key]:
            path.write_text(patched[key], encoding="utf-8")

    return changed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("qemu_root", type=Path)
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate anchors and report whether changes would be needed",
    )
    args = parser.parse_args()

    try:
        changed = patch_tree(args.qemu_root, check_only=args.check)
    except PatchError as exc:
        parser.error(str(exc))

    if args.check:
        print("patch required" if changed else "2000D model already present")
    else:
        print("qemu-eos 2000D model added" if changed else "qemu-eos already patched")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
