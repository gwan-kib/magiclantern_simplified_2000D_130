# Firmware 1.1.0 FlashIF investigation

Status: the Startup.c line 220 assertion remains unresolved. No flash identity
is invented. No qemu-eos behavior or Canon instructions were changed.

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
The emulator source and binary remained unchanged throughout this task.

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

## Implementation decision and next evidence

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
