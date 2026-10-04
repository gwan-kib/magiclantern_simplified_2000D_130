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

FIRMWARE_110_PROFILE = r'''    /* EOS2000D_110_ROM1_ONLY: exact local 1.1.0 dump; never load invalid ROM0. */
    const char *eos2000d_options = qemu_opt_get(qemu_get_machine_opts(), "firmware");
    if (strcmp(eos_state->model->name, MODEL_NAME_2000D) == 0 &&
        eos2000d_options && atoi(eos2000d_options) == 110)
    {
        eos_state->model->firmware_version = 110;
        eos_state->model->rom0_size = 0;
        eos_state->model->rom1_addr = 0xF8000000;
        eos_state->model->rom1_size = 0x02000000;
        eos_state->model->firmware_start = 0xFE0C0000;
    }

'''

FIRMWARE_110_MAIN_ENTRY = r'''    /* EOS2000D_110_MAIN_ENTRY: explicit experiment, not a reset/bootloader claim. */
    if (strcmp(eos_state->model->name, MODEL_NAME_2000D) == 0 &&
        options && atoi(options) == 110 && strstr(options, "start=main"))
    {
        eos_state->cpu0->env.regs[15] = eos_state->model->firmware_start;
        fprintf(stderr, "[EOS2000D] direct main entry: 0x%08X (reset bypassed)\n",
                eos_state->cpu0->env.regs[15]);
    }

'''


FIRMWARE_110_LOW_VECTORS = r'''    /* EOS2000D_110_LOW_VECTORS: optional bootloader-state experiment. */
    if (strcmp(eos_state->model->name, MODEL_NAME_2000D) == 0 &&
        options && atoi(options) == 110 && strstr(options, "start=main") &&
        strstr(options, "vectors=low"))
    {
        uint64_t before = eos_state->cpu0->env.cp15.sctlr_ns;
        eos_state->cpu0->env.cp15.sctlr_ns &= ~SCTLR_V;
        fprintf(stderr, "[EOS2000D] low vectors experiment: SCTLR 0x%08" PRIX64
                " -> 0x%08" PRIX64 " (bootloader state assumed)\n",
                before, eos_state->cpu0->env.cp15.sctlr_ns);
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

    if "EOS2000D_110_ROM1_ONLY" not in eos_c:
        init_anchor = "static void eos_init_common(void)\n{\n    eos_init_cpu();"
        if init_anchor not in eos_c:
            raise PatchError("required anchor not found: eos_init_common")
        eos_c = eos_c.replace(
            init_anchor,
            "static void eos_init_common(void)\n{\n" + FIRMWARE_110_PROFILE + "    eos_init_cpu();",
            1,
        )
    eos_c = _insert_once(
        eos_c,
        '    if (options)\n    {\n        /* fixme: reinventing the wheel */',
        FIRMWARE_110_MAIN_ENTRY,
        "EOS2000D_110_MAIN_ENTRY",
    )

    eos_c = _insert_once(
        eos_c,
        '    if (options)\n    {\n        /* fixme: reinventing the wheel */',
        FIRMWARE_110_LOW_VECTORS,
        "EOS2000D_110_LOW_VECTORS",
    )

    return model_h, model_c, eos_c


def patch_flashif_texts(eos_h: str, eos_c: str) -> tuple[str, str]:
    """Install the disabled-by-default experiment without altering firmware."""
    eos_h = _insert_once(eos_h, '#include "target/arm/cpu.h"',
                         '#include "hw/eos/eos2000d_flashif.h"\n', 'hw/eos/eos2000d_flashif.h')
    eos_h = _insert_once(eos_h, '    uint32_t flash_state_machine;',
                         '    EosFlashIF experimental_flashif;\n', 'EosFlashIF experimental_flashif;')
    eos_c = _insert_once(eos_c, '#include "sysemu/sysemu.h"',
                         '#include "sysemu/reset.h"\n', '#include "sysemu/reset.h"')
    glue = Path(__file__).with_name('eos2000d_flashif_glue.c.inc').read_text()
    eos_c = _insert_once(eos_c, '// io range access', glue, 'EOS2000D_FLASHIF_EXPERIMENT')
    eos_c = _insert_once(eos_c, '    return eos_handler(addr, type, 0);',
                         '    unsigned value = 0;\n'
                         '    if (eos_fi_mmio(addr, size, false, &value)) return value;\n',
                         'eos_fi_mmio(addr, size, false')
    eos_c = _insert_once(eos_c, '    eos_handler(addr, type, val);',
                         '    unsigned value = val;\n'
                         '    if (eos_fi_mmio(addr, size, true, &value)) return;\n',
                         'eos_fi_mmio(addr, size, true')
    read_anchor = '    fprintf(stderr, "ROM read: %x %x\\n", (int)addr, (int)size);'
    read_hook = r'''    /* EOS2000D_FLASHIF_ROM_READ: use the backing array for ordinary reads. */
    EOSState *s = (EOSState *)((intptr_t) opaque & ~1);
    unsigned rom_id = (intptr_t) opaque & 1;
    if (s->experimental_flashif.enabled && rom_id == 1) {
        uint32_t value = 0;
        if (eos_fi_bank_read(&s->experimental_flashif, addr, size, &value)) {
            eos_fi_log(s, "data-read", addr, size, value);
            return value;
        }
        uint64_t raw = 0;
        uint8_t *backing = memory_region_get_ram_ptr(&s->rom1);
        for (unsigned i = 0; i < size; i++) raw |= (uint64_t)backing[addr + i] << (8 * i);
        return raw;
    }
'''
    eos_c = _insert_once(eos_c, read_anchor, read_hook, 'EOS2000D_FLASHIF_ROM_READ')
    write_hook = r'''    /* EOS2000D_FLASHIF_ROM_WRITE: commands never modify ROM backing. */
    if (rom_id == 1 && eos_fi_bank_write(&s->experimental_flashif, addr, size, value)) {
        eos_fi_log(s, "command-write", addr, size, value);
        memory_region_rom_device_set_romd(&s->rom1,
                                          s->experimental_flashif.phase == EOS_FI_IDLE);
        return;
    }

'''
    eos_c = _insert_once(eos_c, '    if (strcmp(s->model->name, MODEL_NAME_1300D) == 0)',
                         write_hook, 'EOS2000D_FLASHIF_ROM_WRITE')
    selection = r'''    /* EOS2000D_FLASHIF_SELECTION: reject unsupported/ambiguous experiments. */
    int flash_selection = eos_fi_select(&eos_state->experimental_flashif,
                                        eos_state->model->name, eos2000d_options);
    if (flash_selection < 0) {
        fprintf(stderr, "Invalid experimental flash-id: requires 2000D firmware 110; "
                "flash-id=c22539 and exact supported option tokens\n");
        exit(1);
    }
    if (flash_selection)
        fprintf(stderr, "[EOS2000D] EXPERIMENTAL flash-id=c22539; "
                "physical T7 identity UNVERIFIED\n");

'''
    eos_c = _insert_once(eos_c, '    eos_init_cpu();', selection, 'EOS2000D_FLASHIF_SELECTION')
    reset = r'''    /* EOS2000D_FLASHIF_RESET: registration only for the opt-in device. */
    if (eos_state->experimental_flashif.enabled)
        qemu_register_reset(eos_fi_qemu_reset, eos_state);

'''
    eos_c = _insert_once(eos_c, '    /* hijack machine option "firmware"', reset,
                         'EOS2000D_FLASHIF_RESET')
    return eos_h, eos_c


def patch_tree(root: Path, check_only: bool = False) -> bool:
    targets = {
        "model_h": root / "hw/eos/model_list.h",
        "model_c": root / "hw/eos/model_list.c",
        "eos_c": root / "hw/eos/eos.c",
        "eos_h": root / "hw/eos/eos.h",
    }
    missing = [str(path) for path in targets.values() if not path.is_file()]
    if missing:
        raise PatchError("qemu-eos source files not found: " + ", ".join(missing))

    original = {key: path.read_text(encoding="utf-8") for key, path in targets.items()}
    patched = dict(zip(
        ("model_h", "model_c", "eos_c"),
        patch_texts(original["model_h"], original["model_c"], original["eos_c"]),
    ))

    patched["eos_h"], patched["eos_c"] = patch_flashif_texts(original["eos_h"], patched["eos_c"])
    helper = root / "hw/eos/eos2000d_flashif.h"
    helper_text = Path(__file__).with_name("eos2000d_flashif.h").read_text()
    changed = (any(original[key] != patched[key] for key in original) or
               not helper.exists() or helper.read_text() != helper_text)
    if check_only:
        return changed

    for key, path in targets.items():
        if original[key] != patched[key]:
            path.write_text(patched[key], encoding="utf-8")

    if not helper.exists() or helper.read_text() != helper_text:
        helper.write_text(helper_text, encoding="utf-8")
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
