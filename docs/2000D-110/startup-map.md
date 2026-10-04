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

The patched qemu-eos 1.1.0 profile configures `rom0_size = 0`, ROM1 base
`0xF8000000`, ROM1 size `0x02000000`, and `firmware_start = 0xFE0C0000`.
Source inspection and repeated emulator runs confirm that zero ROM0 size skips
ROM0 mapping/loading. Normal reset still enters filler at `0xFFFF0000`;
explicit direct entry reaches the main code. These outcomes validate the
emulator settings, not the physical camera's ROM wiring or reset behavior.

## Executed ROM-to-RAM bootstrap

Debugger stops at `0xFE0C0000`, `0xFE0C000C`, `0xFE0C0638`, `0xFE0C3A38`,
`0xFE0C3A6C`, `0x00029898`, `0xFE0C3B0C`, `0x00005254`, and `0xFE129718`
were observed in order, twice per direct-entry mode. `0xFE0C3B34` is data and
was not executed.

The copy loop at `0xFE0C009C..0xFE0C00A8` uses four startup literals at
`0xFE0C00DC..0xFE0C00E8`:

| Operation | Source / start | Destination / end (exclusive) |
|---|---|---|
| Initialized code/data copy | ROM `0xFE9E9C48..0xFEA36DE4` | RAM `0x00001900..0x0004EA9C` |
| BSS clear | RAM `0x0004EA9C` | RAM `0x00084D24` |
| Initial low vectors | ROM `0xFE0C0648..0xFE0C0680` | RAM `0x00000000..0x00000038` |
| IRQ/bootstrap block | ROM `0xFE0C0680..0xFE0C0858` | RAM `0x000004B0..0x00000688` |

The first copy is 315,804 bytes. The debugger checked every byte at `cstart`
against canonical ROM1; SHA-256
`9c57fd4e542d72f3e96a6c5641e91d85f3edb9f1364dbba1049118c587d179e2`.
Under this linear copy, RAM `0x00029898` comes from `0xFEA11BE0` and RAM
`0x00005254` from `0xFE9ED59C`. Both routines were called after initialization.
There is another matching bzero sequence earlier in ROM1, but the executed
copy bounds identify the source above. The clear loop and its upper bound do
not establish a safe allocator-end patch or relocation region.

Startup sets banked IRQ and SVC SP to `0x1000` at `0xFE0C0608..0xFE0C061C`.
Low-vector contents are modified subsequently by IRQ setup; see the private
probe snapshots. Default direct entry retains reset SCTLR high vectors and
fails at the first timer IRQ. The opt-in low-vector experiment gets past it,
then startup routine `0xFE0C1B60` fails flash-identification checks and calls the
assertion routine at `0x00003CBC` from `0xFE0C1C44`. Without the debugger stop,
the terminal assertion loop is `0x00003CDC`. See [qemu.md](qemu.md) for the
mode distinction and evidence limits.

## Task structure

No `task` or `task_attr` variant is selected. The entry path calls the
historical task-creation routine, but this alone does not reveal the structure
layout. Required field offsets and scheduling/current-task evidence remain
unresolved; see [task-structure.md](task-structure.md).

## Flash-ID caller correction

RAM `27C4` maps to ROM `FE9EAB0C` and returns a status, measured as zero.
The manufacturer output at caller SP+20 is loaded into R0 at `FE0C1BC0`;
R0=6 at `FE0C1BC4` therefore is not the routine's status return. Device/type
and capacity at SP+16/+12 also must match an accepted tuple. See
[flashif.md](flashif.md); no new startup stage beyond the assertion is verified.
