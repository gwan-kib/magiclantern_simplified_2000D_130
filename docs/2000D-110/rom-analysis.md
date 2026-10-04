# EOS 2000D / Rebel T7 firmware 1.1.0 ROM analysis

This document records analysis of the locally supplied EOS 2000D / Rebel T7
firmware 1.1.0 dump. Canon ROM bytes and local paths are intentionally excluded
from the repository. Hashes identify the supplied files; they do not establish
that a mismatching image is an authentic full ROM.

## Dump identity and integrity

| Image | Size | MD5 from dump/log | Independently calculated MD5 | SHA-256 | Assessment |
|---|---:|---|---|---|---|
| ROM0.BIN | 33,554,432 (0x02000000) | `66354cabd287d45faae4c6158ba09606` | `387d96a501c80ee5a1291e6a4bbbb636` | `776ca15c7c087423135729a606fcf961f4e3f77a9bdd01113ae4f7fb69343557` | Hash mismatch; 8,388,608 little-endian words all equal `0x00010000`; only two byte values occur. Treat as unusable dump data, not as verified Canon ROM0. |
| ROM1.BIN | 33,554,432 (0x02000000) | `885bc2112958e86a0bf81c591ba482cc` | `885bc2112958e86a0bf81c591ba482cc` | `7c17f49c5521ffe2fa140371a1bcb6353874b94d5c2669982b86f35e639c1a12` | MD5 matches the accompanying dump log. The image contains the T7 identity and 1.1.0 version strings and executable code. |

The accompanying rescue log identifies model ID `0x432`, EOS 2000D / K432,
Rebel T7, firmware 1.1.0 (2.3.5 20(03)), and `ROMBASEADDR: 0xFE0C0000`.
It records the expected ROM0 hash above, which does not match the supplied
ROM0 bytes, and the ROM1 hash, which does match. It reports no serial flash.
The log's `ROMBASEADDR` is the firmware main-entry address; it is not by itself
proof of the physical ROM chip's bank base.

## Entry and control-flow evidence

ROM1 file offset `0xC0000` contains little-endian ARM word `0xEA000001`, which
branches from the reported entry `0xFE0C0000` to `0xFE0C000C`. This entry stub
sets up registers and proceeds into executable startup code. A branch at
`0xFE0C0638` reaches `0xFE0C3A38`, whose instructions have a credible startup
prologue (literal load, link-register save, and stack adjustment).

The `cstart` identification is high-confidence: it is on the entry control-flow
path, has startup prologue structure, and contains calls matching two
historical RAM-callable routines:

| Candidate | Evidence in 1.1.0 ROM1 | Status |
|---|---|---|
| Firmware entry `0xFE0C0000` | Offset `0xC0000`, word `0xEA000001`; branch target `0xFE0C000C` | Verified |
| `cstart` `0xFE0C3A38` | Entry-path branch at `0xFE0C0638`; startup prologue; calls below | High-confidence identification |
| `bzero32` `0x00029898` | BL at `0xFE0C3A6C` decodes to `0x00029898` | Verified as a called RAM routine; semantic name matches historical evidence |
| `create_init_task` `0x00005254` | BL at `0xFE0C3B0C` decodes to `0x00005254` | Verified as a called RAM routine; semantic name matches historical evidence |
| `init_task` `0xFE129718` | Pointer literal at `0xFE0C3B34`; pointed-to code begins with a function prologue | Strong candidate; task semantics need fuller analysis |

The historical BSS instruction signature at `0xFE0C1B74` is **rejected** for
1.1.0: the word there is `0xE3A0160D`, not the expected `0xE3A01732`.
This does not identify an alternate BSS/allocator-end patch.

## Local execution evidence

Repeated qemu-eos direct-entry probes reached the main entry, cstart, both RAM
call targets and init-task entry. The startup code copies ROM
`0xFE9E9C48..0xFEA36DE4` into RAM `0x1900..0x4EA9C`; the full copied range
matched canonical ROM1 byte-for-byte before cstart. RAM routine sources are
`0xFEA11BE0` for `0x29898` and `0xFE9ED59C` for `0x5254`.

Normal reset never reached main entry. Default direct entry fails when an IRQ
uses inherited high vectors; the optional low-vector experiment reaches a
repeatable flash-identification assertion (`Startup/Startup.c`, line 220).
These are emulator results and assumptions, not independently verified physical
reset state or flash device identity. See [qemu.md](qemu.md).

## Unknowns and limits

- The invalid/uniform ROM0 dump suggests an unpopulated or inaccessible bank,
  but does not prove the camera's electrical ROM0 state.
- QEMU's alias mapping is documented separately in
  [startup-map.md](startup-map.md); it is not evidence of physical silicon
  wiring.
- No task/task-attribute structure layout has been established.
- `RESTARTSTART = 0x00C80000` remains a historical RAM reservation lead; RAM,
  BSS, allocator, and overlap boundaries are unknown.
- Candidate `DryosDebugMsg` at `0xFE11F3C8` has a plausible function prologue,
  but no confirmed caller/string evidence; it remains unverified.
- The LED register and values `0x46` / `0x44` are not verified. The byte
  sequence for literal `0xC0220134` was not found; synthesized addresses and
  canonical LED routines remain possible.
- RAM call targets `0x00003780`, `0x000038FC`, and `0x00055820` point into
  filler in the ROM file; because RAM code may be copied, this alone neither
  verifies nor disproves the historical `msleep`, `task_create`, and
  `bmp_vram_info` names.

No 1.1.0 stubs or platform constants should be enabled based only on historical
names. Preserve each address as an evidence-qualified candidate until the
calling convention, semantics, and use are confirmed.

## Flash identification

Static and repeated runtime analysis identify a serial-flash 06/9F/05 path,
four halfword outputs and three alternative accepted manufacturer/type/capacity
tuples. No unique installed chip identity follows from those alternatives.
The measured manufacturer six comes from an unmodeled command/data window,
not a physical chip ID or status return. See [flashif.md](flashif.md).
