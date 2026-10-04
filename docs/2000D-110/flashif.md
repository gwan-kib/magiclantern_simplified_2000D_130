# Firmware 1.1.0 FlashIF investigation

Status: the default Startup.c line 220 assertion and physical flash identity
remain unresolved (KI-019). The explicitly opt-in C2 25 39 experiment passes
that comparison and advances into task activity; it does not identify the
physical chip. The baseline sections below describe the pre-experiment model.

## Evidence classes

- **Static ROM:** canonical ROM1 SHA256
  `7c17f49c5521ffe2fa140371a1bcb6353874b94d5c2669982b86f35e639c1a12`.
- **Measured QEMU:** qemu-eos `4b667a1d3c08ab7a55835d15ddbd884fa754946d`
  with the merged model patch, explicit main entry and low-vector experiment.
- **Related references:** SPI NOR datasheets, Linux device tables and related
  camera reports establish protocol context, not the installed T7 identity.
- **Temporary experiment:** `vectors=low` assumes missing bootloader state.
- **Unresolved:** physical chip identity, electrical controller semantics,
  reset values and full Canon startup.

## Baseline and instrumentation

Before any tooling change, two assertion stops and two identification stops
reproduced the existing failure with canonical ROM1. Both assertion runs
passed all nine ordered startup stages and the full 315,804-byte RAM copy.
The emulator source and binary remained unchanged during the original
PR #38 investigation. That historical result is distinct from the opt-in
experiment below.

`qemu_probe.py --flashif-trace` instruments the canonical driver's observed
MMIO access PCs, command descriptor entry, bank byte accesses, status return
and caller output load. Each event has order, monotonic timestamp, PC/LR,
R0..R15, access width, address, operation and value. Guest read values are
sampled after stepping the instruction, without debugger MMIO reads. ARM
conditions are checked: the loop's final non-executed `LDRBHI` is a skipped
event, not an invented access. Complete FlashIF log equality is mandatory;
missing/new controller accesses fail the probe. This coverage applies to this
observed canonical path, not every possible FlashIF operation or firmware.

Final repeated traces contain 153 controller accesses each and nine bank byte
accesses. Full JSONL, CSV, registers and disassembly remain private. All nine
startup stops, RAM copy and the assertion reproduce with instrumentation.

## RAM function and control flow (static and measured)

The ROM-to-RAM relation is `ROM = RAM + FE9E8348` on the copied range.
RAM `000027C4` therefore comes from ROM `FE9EAB0C`, file offset `9EAB0C`.
Its complete wrapper occupies `27C4..2830` (exclusive).

Arguments: R0 is the memory-mapped flash bank; R1/R2/R3 point to halfword
outputs for manufacturer, device/type and capacity; the fifth stack argument
points to a fourth halfword output. The startup caller passes SP+20, SP+16,
SP+12 and SP+8 respectively, with bank F8000000.

The wrapper saves interrupt state through `3074 -> FE0C0920`, dispatches
lock/prepare callbacks through `6F50` and `6E50`, calls identification via
`6F18`, waits for ready via `6EF8`, unlocks via `6F70`, restores interrupt
state through `3078 -> FE0C0934`, and returns the identification **status**.
The dispatch index at RAM `39DF0` is initially zero; table `39DF4` points to
callbacks at `39D60`. Initial callback `B1E4` emits command 06; ID callback
`B3DC` emits 9F; ready callback `B3C0` uses `B358` to emit 05 and loops while
status bit 0 is set. Lock/unlock callbacks are initially no-ops at `6FD8`.

`B3DC` builds a 28-byte descriptor: command at +0, bank at +4, address at +8,
address-mode at +12, output buffer at +16, count at +20, direction at +24.
RDID requests three bytes, no address and direction 2. It calls
`F9FC -> FA08 -> 1D3A8`; on success B444..B45C stores the three returned bytes
as zero-extended halfwords and sets the fourth output to zero.

**Correction to earlier wording:** at FE0C1BC0, immediately after the call,
R0 is 0 (success). FE0C1BC0 loads the manufacturer halfword from SP+20;
at FE0C1BC4 R0 is 6. Six is the output value, not the wrapper's status return.
The measured four output halfwords are manufacturer 6, type 0, capacity 0,
extra 0. There is no ID-operation timeout path in this observed executor
branch; the ready callback can wait indefinitely on status bit 0. The host
probe bounds total execution. Other executor branches are outside this claim.

## Exact controller sequence (measured)

Let D be the eight halfwords `DC,DE,E0,E2,E4,E6,E8,EA`, and E be
`EC,EE,F0,F2,F4,F6,F8,FA`, all relative to C0000000. Ordering within each
list is ascending. All these guest instructions are 16-bit accesses.

| Phase | Ordered controller operations | Bank byte operations |
|---|---|---|
| Entry | Write C0000010=D9C5D9C5, 32 bits | none |
| WREN 06 | Read E then D (16 reads); write D=zeros; write E=(0707,0707,0,0,0,0,0,0); restore E then D=zeros | Dummy read F8000000=0, then write F8000000=06 |
| RDID 9F | Read E then D; write D=zeros; write D=(9F0E,0707,0,0,0,0,0,0); write D=zeros after receive; restore E then D=zeros | Dummy read=06; read F8000000/1/2 = 06/00/00; final dummy read=06 |
| RDSR 05 | Read E then D; write D=zeros; write D=(0506,0707,0,0,0,0,0,0); restore E then D=zeros | Dummy read=06; status read F8000000=06 |

Controller counts are 1 + 48 + 56 + 48 = 153. Nine bank accesses include the
four dummy reads, one command write, three ID reads and one status read.
No AA/55/90 parallel-NOR unlock/autoselect or CFI query is observed here.

## Register mapping: qualified roles, not a hardware datasheet

| Address | Guest access PC | Observed role | Current upstream behavior |
|---|---|---|---|
| C0000010 | FE0C0014 | Main-entry write-enable word | Reads 1; recognizes D9C5/0 writes for logging; no persistent latch |
| C00000DC | 1D278 write / 1D360 read | First D descriptor halfword; command bits 15..8 when used for read | Reads 0; writes discarded |
| C00000DE | 1D280 / 1D36C | Second D halfword, observed 0707 | Reads 0; writes discarded |
| C00000E0 | 1D288 / 1D374 | D slot 2, zero on this path | Reads 0; writes discarded |
| C00000E2 | 1D290 / 1D37C | D slot 3, zero | Reads 0; writes discarded |
| C00000E4 | 1D298 / 1D384 | D slot 4, zero | Reads 0; writes discarded |
| C00000E6 | 1D2A0 / 1D38C | D slot 5, zero | Reads 0; writes discarded |
| C00000E8 | 1D2A8 / 1D394 | D slot 6, zero | Reads 0; writes discarded |
| C00000EA | 1D2B0 / 1D39C | D slot 7, zero | Reads 0; writes discarded |
| C00000EC | 1D2C0 / 1D31C | First E halfword; command-write configuration 0707 | Reads 0; writes discarded |
| C00000EE | 1D2C8 / 1D328 | Second E halfword, 0707 | Reads 0; writes discarded |
| C00000F0 | 1D2D0 / 1D330 | E slot 2, zero | Reads 0; writes discarded |
| C00000F2 | 1D2D8 / 1D338 | E slot 3, zero | Reads 0; writes discarded |
| C00000F4 | 1D2E0 / 1D340 | E slot 4, zero | Reads 0; writes discarded |
| C00000F6 | 1D2E8 / 1D348 | E slot 5, zero | Reads 0; writes discarded |
| C00000F8 | 1D2F0 / 1D350 | E slot 6, zero | Reads 0; writes discarded |
| C00000FA | 1D2F8 / 1D358 | E slot 7, zero | Reads 0; writes discarded |

Executor 1D3A8 saves both groups to RAM 7D4EC/7D4FC, configures commands,
performs bank byte accesses and restores them via 1D300. Low control bits
start from RAM 490DC=6; a multi-byte read adds bit 3, producing 9F0E.
The second descriptor adds 0700 and bit 0, producing 0707. Hardware meanings
of individual low bits and the unused slots remain unresolved. The handler
matches `address & 1FF` across C0000000..C0001FFF; aliasing is an upstream
emulator implementation detail. It has no state or command/data window model.

## Why six appears (measured and source-confirmed)

Command 06 is executed as a byte store to F8000000 at RAM 1D554. QEMU's ROM
window has no serial-command state for this path, and the following RDID
reads return the stored 06 byte plus original zeros at offsets 1 and 2.
The on-disk canonical ROM still hashes identically. This explains the output
without treating it as chip identity. Controller-register return zeros alone
do not explain six; the missing bank command/data behavior is essential.

The status read also returns 06, whose busy bit 0 is clear, so the ready loop
exits. That is an emulator artifact, not a verified physical status response.

## Protocol and accepted identities

The observed 06/9F/05 sequence and three-byte response are SPI NOR WREN,
JEDEC RDID and RDSR, consistent with primary SPI NOR documentation. This
identifies the firmware's attempted protocol, not the physical bus topology.
The accepted startup tuples are exactly:

| Manufacturer | Type | Capacity | Accepted initializer |
|---|---|---|---|
| C2 | 25 | 39 | RAM 2938 |
| 20 | BB | 19 | RAM 2B0C |
| 01 | 02 | 19 | RAM 2CE4 |

All three bytes are checked; manufacturer alone cannot pass. These alternatives
also appear in the driver table at RAM 39DF4. An initial index of zero is a
default driver choice before identification, not proof of a Macronix chip.
A ROM string scan found no Macronix/MX25/N25Q/S25FL/JEDEC identity strings.
CFI/flash/SPI string hits are retained privately and do not uniquely select a
chip. No unique installed-device identity was derived from the firmware.

Primary references:
- [Macronix SPI NOR RDID command definition](https://www.macronix.com/Lists/Datasheet/Attachments/8390/MX25L25635F%2C%203V%2C%20256Mb%2C%20v1.2.pdf), section 9-3: command 9F and a three-byte ID. This is a protocol reference, not a T7 part identification.
- [Linux Micron/ST device table](https://github.com/torvalds/linux/blob/master/drivers/mtd/spi-nor/micron-st.c): 20 BB 19 is an accepted 32 MiB SPI NOR family.
- [Linux Spansion device table](https://github.com/torvalds/linux/blob/master/drivers/mtd/spi-nor/spansion.c): 01 02 19 is a prefix used by 32 MiB devices; extended IDs distinguish variants.
- [4000D developer report](https://www.magiclantern.fm/forum/index.php?topic=23369): a historical workaround changes a 1300D emulator ID. It is reference-camera evidence only and was not copied. The pinned qemu-eos source has the same incomplete handler for 1200D/1300D, no 4000D entry and no independently established 2000D identity.

## Pre-experiment implementation decision and next evidence

No controller state machine was installed. The transaction structure is now
known, but a complete RDID response fundamentally needs an unknown physical
identity. Returning an accepted tuple, an invented unknown-chip tuple or
suppressing the assertion would violate the evidence requirement. A register
latch alone cannot produce the missing serial response. The next meaningful
change needs independent chip-identification evidence plus controller/window
semantics, including reset and invalid-command behavior. No active 1.3.0
platform constants or unrelated model behavior changed.

The deepest repeatable point remains Startup.c line 220 at 3CBC; no new MPU,
GUI or post-assertion stage is promoted. The original nine-stage smoke check
is unchanged. No ML injection was attempted.

Reproduce privately using a fresh result directory:

```bash
python3 tools/eos2000d/qemu_probe.py /private/workdir \
  --binary /path/to/qemu-system-arm --log-dir /private/flash-results \
  --start-main --low-vectors --stop-at 0x3cbc --timeout 15 --flashif-trace
```

AI provenance: Codex authored this investigation's debugger tooling, tests and
analysis notes. Static conclusions were checked against canonical ROM1 and
runtime claims against repeated measured runs. Raw evidence stays outside Git.

## Experimental C2 25 39 hypothesis (2026-10-04)

**QEMU + Experiment. Physical identity: Unresolved. KI-019 stays open.**
The user explicitly authorized testing this accepted tuple as a hypothesis.
It is available only through `2000D,firmware=110;flash-id=c22539`. It is not
installed in platform constants, release metadata or default emulator behavior.

Two pre-change traces reproduced the nine-stage startup chain, full RAM copy,
06/9F/05, caller ID 06/00/00 and assertion 3CBC. The final rebuilt binary
also reproduces normal-reset FFFF0004, default direct-main high-vector failure,
and low-vector-only 06/00/00 plus 3CBC, twice per mode.

### Peripheral implementation

The public C helper is `tools/eos2000d/eos2000d_flashif.h`; the patcher embeds
`eos2000d_flashif_glue.c.inc` in pinned qemu-eos. State belongs to EOSState,
not a firmware PC: phase IDLE/RDID/RDSR/UNSUPPORTED, last command, ID index,
WEL, WIP, address-mode latch, and sixteen controller halfword latches.

- Reset clears phase, registers, WEL, WIP, index and four-byte mode; selection
  survives. The peripheral QEMU reset callback restores ROMD. Normal initial
  machine reset still starts at FFFF0000; the existing EOS board does not reset
  the stopped ARM PC through QMP system_reset, a separate board limitation.
- 06 sets WEL when idle; 04 clears it. RDID and RDSR retain WEL.
- 9F restarts the three-byte RDID stream C2/25/39. Reads beyond the three
  modeled bytes return FF with a saturated index. This bounded behavior is an
  explicit experiment assumption, not a verified physical continuation rule.
- 05 composes actual modeled WIP bit 0 and WEL bit 1. The observed response is
  02 after WREN. Other status bits are zero, not evidence of physical reset
  values. Program/erase is unsupported, so no operation sets busy and no fake
  busy completion is implemented. Synthetic tests also exercise busy=true.
- B7/E9 set/clear an address-mode latch when not busy. E9 is observed at runtime;
  B7 is its tested counterpart. Addressed serial reads/writes, EAR and the full
  configuration register are not implemented by this latch.
- Unknown commands return FF during byte data reads and have no WEL or storage
  side effects. Writes outside the observed command window are intercepted as
  unsupported rather than changing the canonical ROM backing array.

The observed read descriptor uses DC high byte for the command and DE=0707;
DC=0 or invalid DE ends data mode. The command-write descriptor requires
EC=EE=0707 and an offset-zero bank byte store. Controller reads/writes preserve
1/2/4-byte little-endian accesses at DC..FB, including partial updates. Aliasing
uses the existing upstream low-nine-bit convention, not a new hardware claim.
ROMD is disabled during serial data phases; ordinary instruction/data reads
fall back to the canonical array. No accepted-ID comparison, assertion, ROM
instruction, or PC-based peripheral response is patched.

Strict experiment tokens allow `start=main`, `vectors=low` and
`flash-id=c22539` once each, reject empty/unknown/duplicate tokens and require
start=main for vectors=low. Model must be exactly 2000D and firmware prefix
exactly `110;`. Without flash-id the prior option parser and I/O fallbacks are
preserved. Other IDs deliberately remain unsupported.

Diagnostics include phase, command, ID index, WEL, WIP, address byte count and
hypothesis label. Exact FlashIF MMIO equality, ARM condition checks and all nine
startup smoke requirements remain intact. The trace also observes all three
initializer entries, geometry registration and task-creation arguments. Raw
instructions, memory, registers and detailed traces stay private.

### Measured initializer and later commands

Both final repetitions return C2/25/39, wrapper status zero and extra output
zero; only RAM 2938 executes. RAM 2B0C and 2CE4 are monitored and not hit.
At entry R0=F8000000, LR=FE0C1BE8. The initializer allocates 0x11E8 bytes;
measured table pointer is 002D0488 and RAM 39DF0 changes to dispatch index 1.

At 29DC, R0=0, R1=002D0488, R2=2664, R3=28AC, R4=02000000, R5=40,
R6=002D0488, R7=F8000000. The subsequent registration call FE2B8DC4 returns
R0=0 at 29E4. The table contains 64 ranges of 4096 bytes followed by 508 ranges
of 65536 bytes, contiguous over exactly 32 MiB, plus terminator (FFFF,0).
Those sizes describe Canon's installed erase map; no erase is actually issued.
The driver source-name string contains `Install_MX66U51235F`; that shared
installer name does not establish the physical part, and its nominal part
name must not override the measured 32 MiB geometry.

The full measured descriptor command sequence is:
`06 -> 9F -> 05 -> 06 -> 9F -> 05 -> E9`.
Both ID reads are C2/25/39; both status reads are 02. Each complete trace matches
353 controller accesses and 20 bank-byte accesses. The controller returns to
its saved zero descriptor state. No timing calibration or real serial clock
rate is established by register latching.

### Protocol comparison: Related, not chip identification

The primary [Macronix MX25U25635F datasheet](https://www.macronix.com/Lists/Datasheet/Attachments/8663/MX25U25635F%2C%201.8V%2C%20256Mb%2C%20v1.5.pdf)
provides C2/25/39, 256 Mbit capacity, WREN/RDID/RDSR, 4 KiB sectors and 64 KiB
blocks, 256-byte page programming, and B7/E9 address-mode commands.

| Finding | Classification for C2 hypothesis |
|---|---|
| Three-byte ID accepted; 32 MiB geometry; 4 KiB/64 KiB erase ranges | Consistent, conditional on supplied ID |
| WREN, repeated ID, WIP polling, E9 | Consistent protocol context |
| Installed driver source-name string | Neutral; shared code name is not part identity |
| Page size, erase/program busy timing, reset commands, quad/dual setup, protection bits | Neutral/insufficient; not exercised |
| Upper-bank addressed reads, EAR/configuration register | Neutral/insufficient; latch is not a complete addressing model |
| Physical part, voltage, wiring and controller reset state | Unresolved |

No observation proves the installed chip; no inconsistency was established in
this limited exercised path. Other accepted IDs were not modeled or compared.

### New bounded startup result

**QEMU + Experiment:** the line-220 assertion is not taken. The initializer
returns at 29FC, startup routine FE0C1B60 reaches its task-creation call and
return at FE0C1DD0, then actual task-entry breakpoints reach Startup FE0D3C94,
TaskMain FE0C12AC, shared manager entry FE2C1438, PowerMgr FE2BA2F4 and HotPlug
FE0C69DC, in the same order in two bounded repetitions. Creation calls at RAM
38FC record PowerMgr, DbgMgr, Startup, TaskMain, PropMgr, NFCMgr, HotPlug and
EventMgr. Names are caller arguments; no task-structure offsets are promoted.

Both 30-second runs end at PC FE2BA330, SP=0014BB18, LR=FE2BA314, R0=0,
R1=1, R4=C0400000, R5=39E44, PSR=60000093. Static code connects the PowerMgr
creation call FE2BA42C -> RAM 38FC, entry FE2BA2F4 and loop FE2BA304 through
save-interrupt-state 3074 -> FE0C0920, conditional CP15 power-save instruction
FE2BA32C, PC FE2BA330, and restore-state 3078 -> FE0C0934 before looping.
This is a repeatable power-management wait, **not proof of a deadlock or the
next fatal assertion**. Timer/IRQ and HotPlug activity continues in the trace.
The meaningful stable milestone is task startup; a later fatal blocker is
still unresolved. No full-boot claim follows from the bounded timeout.

Post-identification MMIO includes timer C02431xx/C02432xx, interrupt/DMA setup,
and HotPlug reads at FE121ED8 of C022F48C returning 10C with callers FE0C69F4
and FE0C6A7C. Generic SD-detect labels do not prove SD initialization. No MPU
handshake, GUI entry, display initialization or mounted file system is verified.
Generic upstream MPU spell/button fallback warnings are configuration messages,
not executed handshake evidence. KI-019 remains open; no new independently
justified peripheral blocker is asserted from an idle-task snapshot.

### Reproduction and validation

```bash
python3 tools/eos2000d/qemu_probe.py /private/workdir \
  --binary /path/to/qemu-system-arm --log-dir /private/c22539 \
  --start-main --low-vectors --flash-id c22539 --stop-at 0x3cbc \
  --watch-at 0x29fc --watch-at 0xfe0c1dd0 --watch-at 0xfe0d3c94 \
  --watch-at 0xfe0c12ac --watch-at 0xfe2ba2f4 --watch-at 0xfe0c69dc \
  --watch-at 0xfe2c1438 --repeat 2 --timeout 30 --flashif-trace
```

The expanded suite has 56 passing tests, including 19 compiled C state-machine
cases and an integration test for idempotence/default fallbacks. Actual QEMU
CLI checks reject wrong model, firmware, ID, duplicate options and low vectors
without main entry. A QMP system_reset clears device state during an active
RDID transaction; it does not establish a complete board/CPU reset path. Fresh pinned source patched by the public script exactly
matches the compiled source; the script is idempotent. Firmware-130 evidence,
feature and pre-ROM policy gates pass; reference-camera build is checked by CI.

AI provenance: Codex authored the opt-in C helper/glue, patcher changes,
synthetic tests, read-only debugger observers and analysis/documentation.
No physical camera/SD action or ML payload/injection was performed.
