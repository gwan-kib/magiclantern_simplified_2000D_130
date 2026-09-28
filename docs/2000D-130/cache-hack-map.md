# 2000D.130 cache-hack reverse-engineering map

This file is an **analysis map, not executable configuration**.

No address below may be copied into `platform/2000D.130/consts.h`,
`stubs.S`, or the Makefile merely because it appeared in firmware 1.1.0.

## What boot-d45-ch.c actually needs

The current cache-hack loader directly depends on:

- `MAIN_FIRMWARE_ADDR`;
- `HIJACK_CACHE_HACK_INITTASK_ADDR`;
- either `RSCMGR_MEMORY_PATCH_END` or
  `HIJACK_CACHE_HACK_BSS_END_ADDR`;
- a verified `RESTARTSTART`;
- Canon's original `init_task`;
- any firmware stubs required by the generic boot path.

If the BSS-end patch path is used, the original word at
`HIJACK_CACHE_HACK_BSS_END_ADDR` is expected to be a
`MOV R1, #immediate`-style ARM instruction. The loader derives the original
allocator end from that instruction and constructs a replacement based on
`RESTARTSTART`.

## Same-body 2000D.110 reference

Historical firmware 1.1.0 values:

| Purpose | 2000D.110 reference | 1.3.0 status |
|---|---:|---|
| ROM base / firmware entry | `0xFE0C0000` | reported by original 1.3.0 README, still needs canonical-ROM proof |
| `cstart` | `0xFE0C3A38` | unverified |
| `bzero32` RAM entry | `0x00029898` | unverified |
| `create_init_task` RAM entry | `0x00005254` | unverified |
| `init_task` | `0xFE129718` | unverified |
| cache-hack BSS-end instruction | `0xFE0C1B74` | unverified |
| expected 1.1.0 BSS-end word | `0xE3A01732` | do not assume unchanged |
| cache-hack init-task pointer/word | `0xFE0C3B34` | unverified |
| BL to `cstart` site | `0xFE0C0638` | unverified |
| BSS-end startup site | `0xFE0C3B24` | unverified |
| branch fix for `bzero32` | `0xFE0C3A6C` | unverified |
| branch fix for `create_init_task` | `0xFE0C3B0C` | unverified |
| historical restart reservation | `0x00C80000` | unverified for 1.3.0 |

## Closely related 1300D.110 comparison

The 1300D.110 reference contains:

- `cstart = 0xFE0C3A24`;
- `bzero32 = 0x00029898`;
- `create_init_task = 0x00005254`;
- `init_task = 0xFE1296C8`.

The identical RAM addresses for `bzero32` and `create_init_task` across
the old 1300D and 2000D references are useful search anchors, but do not
prove those RAM copies are identical in 1.3.0.

## 1.3.0 verification procedure

### 1. Verify the ROM base and entry branch

Load the canonical raw image at `0xFE0C0000` as little-endian ARM.

Confirm:

- first word;
- decoded branch target;
- expected executable code at/after the target;
- version/model evidence elsewhere in the image.

### 2. Locate cstart

Start from the entry path and identify the routine responsible for early RAM
initialization. Compare control flow against 2000D.110/1300D.110 rather than
searching only by absolute address.

Expected characteristics include:

- early initialization before DryOS tasks;
- calls/branches related to BSS clearing;
- setup of memory boundaries;
- eventual creation of the Canon init task.

### 3. Locate the BSS / allocator-end instruction

Find where `cstart` loads or constructs the end of Canon's startup memory
region.

For the cache-hack loader's current BSS-end path, verify the original
instruction class as well as the resulting decoded address. Do not simply
patch the 1.1.0 location.

Record:

- original instruction word;
- disassembly;
- decoded address;
- role of that address in Canon's memory map;
- why the proposed `RESTARTSTART` leaves safe memory for Canon.

### 4. Locate create_init_task and init_task

Follow the startup control flow to the routine that creates the initial DryOS
task and identify the function pointer passed as Canon's `init_task`.

If firmware copies low-level functions from ROM into RAM, distinguish the ROM
source from the eventual RAM callable address.

### 5. Identify the cache-hack patch word

Find the exact 1.3.0 word that contains/references Canon's init-task function
and would be replaced by `my_init_task` through data-cache fakery.

Verify:

- the original word points to the expected Canon function;
- the location is safely patchable with the cache-lockdown mechanism;
- no adjacent assumptions depend on the 1.1.0 layout.

### 6. Record evidence before code

For every candidate, update this document or a linked analysis note first.
Only then promote it into `platform/2000D.130`.

## Exit gate for ML2000D-009

Do not close ML2000D-009 until all active cache-hack constants have:

- an exact 1.3.0 ROM hash;
- an address;
- the original instruction/data word;
- surrounding disassembly/control-flow evidence;
- a comparison with the historical port;
- manual review.
