# EOS 2000D firmware 1.1.0 startup map

All file offsets below refer to the exact 32 MiB ROM1 image identified in
[rom-analysis.md](rom-analysis.md). The camera-reported firmware entry is
`0xFE0C0000`, corresponding to file offset `0xC0000` under the QEMU model's
32 MiB alias mapping.

| ROM1 file offset | QEMU virtual address (FE alias) | Observation | Confidence |
|---:|---:|---|---|
| `0xC0000` | `0xFE0C0000` | `0xEA000001`, branch to `0xFE0C000C` | Verified |
| `0xC000C` | `0xFE0C000C` | Register and memory setup begins | High |
| `0xC0638` | `0xFE0C0638` | Branch to startup routine at `0xFE0C3A38` | Verified control flow |
| `0xC3A38` | `0xFE0C3A38` | `cstart` candidate; prologue and verified call targets | High |
| `0xC3A6C` | `0xFE0C3A6C` | BL to RAM `bzero32` candidate `0x00029898` | Verified branch target |
| `0xC3B0C` | `0xFE0C3B0C` | BL to RAM `create_init_task` candidate `0x00005254` | Verified branch target |
| `0xC3B34` | `0xFE0C3B34` | Literal pointer `0xFE129718`, likely `init_task` | Strong candidate |
| `0xC1B74` | `0xFE0C1B74` | Word `0xE3A0160D`; historical `0xE3A01732` signature absent | Historical signature rejected |

## ROM alias model

The `qemu-eos` DIGIC IV defaults place ROM1 at `0xF8000000`. The EOS 2000D
profile uses a 32 MiB ROM1 size. QEMU aliases the ROM image at successive
32 MiB intervals through the top of the 32-bit address space; the resulting
bank bases are `0xF8000000`, `0xFA000000`, `0xFC000000`, and `0xFE000000`.
Therefore file offset `0xC0000` maps to `0xF80C0000`, `0xFA0C0000`,
`0xFC0C0000`, and `0xFE0C0000` in those QEMU aliases.

This resolves the firmware entry in the emulator's address space and explains
why the main entry is offset `0xC0000` into the final alias. It does not
independently prove physical ROM banking on the camera. `ROMBASEADDR` in the
rescue log is recorded as the main firmware entry, not a chip bank base.

## Task structure

No `task` or `task_attr` variant is selected. The entry path calls the
historical task-creation routine, but this alone does not reveal the structure
layout. Required field offsets and scheduling/current-task evidence remain
unresolved; see [task-structure.md](task-structure.md).
