# Minimum firmware interface for the first 2000D payload

This is a dependency checklist for ML2000D-011. It intentionally separates a
**first LED diagnostic** from the richer graphical `minimal/hello-world`.

## Loader-level dependencies

For the current `boot-d45-ch.o` path, the port first needs verified:

- `MAIN_FIRMWARE_ADDR`;
- cache-hack init-task patch address;
- cache-hack BSS/memory-end patch address or validated alternative;
- `RESTARTSTART`;
- Canon `init_task`.

The cache-hack locations themselves are tracked in
`cache-hack-map.md`.

## First LED-only payload

The preferred first payload should require as little firmware API as possible.

If the card LED is verified as direct MMIO, the observable diagnostic itself
can avoid a Canon LED function.

Potential linked firmware dependencies still need review because generic
boot/error paths may reference them. In particular:

- `init_task`;
- `msleep` if the generic boot out-of-memory path remains linked;
- any debug-print implementation pulled into the selected boot profile.

Before claiming a "zero-stub" LED payload, inspect the final ELF's undefined
and referenced symbols and the map file.

Useful commands:

```bash
arm-none-eabi-nm -u platform/2000D.130/build/magiclantern
grep -E "init_task|msleep|task_create|bmp_vram_info|DryosDebugMsg" \
  platform/2000D.130/build/location.map
```

The build should contain no unresolved symbol at link completion; these
commands are for understanding which platform stubs were actually consumed.

## Graphical minimal/hello-world dependencies

Current `minimal/hello-world/minimal.c` directly or indirectly requires at
least:

- `bmp_vram_info` on DIGIC 4/5;
- `msleep`;
- `task_create`;
- card LED address/on/off constants;
- the boot-path symbols above;
- bitmap geometry/constants needed by `font_draw`;
- any libc helpers retained by the minimal link.

Historical **2000D.110** candidates include:

| Symbol | 1.1.0 reference | 1.3.0 status |
|---|---:|---|
| `init_task` | `0xFE129718` | unverified |
| `msleep` | `0x00003780` | unverified |
| `task_create` | `0x000038FC` | unverified |
| `bmp_vram_info` | `0x00055820` | unverified |
| `DryosDebugMsg` | `0xFE11F3C8` | unverified |

Closely related **1300D.110** also used:

- `msleep = 0x00003780`;
- `task_create = 0x000038FC`.

This suggests some early RAM-resident DryOS code may be stable across these
bodies, but every 1.3.0 value still needs confirmation.

## Stub evidence standard

Every stub added to `platform/2000D.130/stubs.S` should have an adjacent
comment or linked analysis entry recording:

- canonical 1.3.0 ROM SHA-256;
- function address;
- ROM vs RAM callable address;
- how the function was identified;
- nearby string/call-graph/signature evidence;
- historical 2000D.110 equivalent;
- confidence/reviewer.

Example only:

```asm
// 1.3.0 ROM SHA-256: <hash>
// Located by: <method>; cross-checked with 2000D.110 <address>
// Evidence: <analysis note>
NSTUB(0xXXXXXXXX, msleep)
```

Do not add the example until the address is real.

## Exit gate for ML2000D-011

- the first selected minimal payload links with only verified 1.3.0 stubs;
- no historical address is active without 1.3.0 evidence;
- the link map is reviewed;
- each active stub is documented.
