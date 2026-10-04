# EOS 2000D firmware 1.1.0 QEMU execution

The canonical ROM1-only firmware profile has now executed locally. This is
software emulation evidence, not a complete Canon boot or a hardware test.
The supplied ROM0 is invalid and is never loaded or replaced.

## Build environment (2026-10-03)

- Ubuntu 22.04.5 LTS in WSL2; kernel
  `6.18.33.2-microsoft-standard-WSL2`.
- GCC `11.4.0` (`Ubuntu 11.4.0-1ubuntu1~22.04.3`), Python 3.10,
  GNU make, glib `2.72.4`, pixman `0.40.0`, zlib `1.2.11`.
- `reticulatedpines/qemu-eos`, branch `qemu-eos-v4.2.1`, commit
  `4b667a1d3c08ab7a55835d15ddbd884fa754946d`.
- Required bundled sources: dtc
  `88f18909db731a627456f26d779445f84e449536`; keycodemapdb
  `6b3d716e2b6472eb7189d3220552280ef3d832ce`.
- The existing Windows checkout was exported with `git archive` into Linux
  storage to preserve executable modes and LF line endings. Only the two
  required submodules were exported; slirp and unrelated firmware submodules
  are unnecessary for this configuration.
- No host package installation or compiler compatibility source edit was
  required. The full ARM emulator linked successfully. Dtc's recursive make
  emitted warnings about absent flex/bison for unused parser-generation
  targets; its libfdt target and the emulator build nevertheless succeeded.
- Earlier native-Windows attempts failed with WSL access denied. Switching
  Codex to Ubuntu resolved WSL access; this session's sandbox launcher remained
  unavailable, so the approved build/probes ran outside that launcher.

Apply `tools/eos2000d/qemu_eos_patch.py`, then build outside the source tree:

```bash
../qemu-eos/configure --target-list=arm-softmmu --disable-docs \
  --disable-werror --disable-slirp --disable-capstone --enable-plugins \
  --disable-gtk --disable-sdl
make -j4
```

`--disable-werror` is an explicit historical-source build setting; no source
warning was silenced by changing firmware or camera behavior.

## Repeated execution results

Two runs of each mode were captured with the saved debugger probe. Hardware
breakpoints established executed PCs, rather than relying on disassembly of
translated blocks or machine-setup messages. All runs were bounded and QEMU
was stopped after the recorded failure or timeout.

| Mode | Initial PC | Verified progress | Repeatable failure |
|---|---|---|---|
| Normal reset, `firmware=110` | `0xFFFF0000` | First ROM1-alias instruction is erased filler; main entry never reached | Undefined instruction at reset, then undefined-vector loop `0xFFFF0004` |
| Direct main, `firmware=110;start=main` | `0xFE0C0000` | Main entry, RAM copy, cstart, RAM calls, init-task entry | First timer IRQ vectors to filler at `0xFFFF0018`, then `0xFFFF0004` |
| Direct main plus **opt-in low-vector experiment**, `firmware=110;start=main;vectors=low` | `0xFE0C0000` | Same milestones, working low-RAM IRQ handler, later startup/flash-identification code | Assertion called at `0xFE0C1C44`: `Startup/Startup.c`, line 220; RAM assertion entry `0x00003CBC`, terminal self-branch `0x00003CDC` |

The mandatory startup breakpoint order is:

```text
FE0C0000 -> FE0C000C -> FE0C0638 -> FE0C3A38
-> FE0C3A6C -> 00029898 -> FE0C3B0C -> 00005254 -> FE129718
```

`0xFE0C3B34` is a pointer literal, not an executed instruction. The probe also
sets a breakpoint there; no run hit it. It must not be a mandatory smoke stage.

### First direct-main failure: inherited high vectors

The main path installs low vectors and IRQ code, and initializes IRQ and SVC
stacks to `0x1000`. It does not execute a CP15 control write on this path.
The ARM946 CPU still inherits reset SCTLR `0x2078` with `SCTLR.V=1`.
When the emulated timer IRQ fires, the CPU uses `0xFFFF0018`, whose ROM1 word
is filler; undefined exceptions then loop at `0xFFFF0004`. The exact interrupted
firmware PC varies with debugger/timer timing, but this failure mechanism
repeated in both runs. It is not a failure to populate the RAM call targets.

The opt-in `vectors=low` experiment clears only `SCTLR.V` in the nonsecure
control register (`0x2078 -> 0x0078`) before direct entry. It is guarded by
model 2000D, firmware 110, and `start=main`; normal reset and default direct
entry are unchanged. This assumes a missing bootloader handoff state, and does
**not** verify the physical camera's reset/bootloader behavior. No firmware
instructions, ROM bytes, interrupt masks, or peripheral responses are patched.

### Next failure: flash-identification assertion

With low vectors, both runs take the same failing path in startup routine
`0xFE0C1B60`. The call at `0xFE0C1BBC` invokes RAM routine `0x000027C4`
with ROM bank base `0xF8000000` and stack outputs for flash-identification data.
A dedicated debugger stop at `0xFE0C1BC4` measured the caller-loaded manufacturer
`r0=0x00000006` in two further runs. Checks for manufacturer `0xC2`,
`0x20`, or the accepted `0x01` variant fail; `0xFE0C1C44` calls the assertion
routine with `r0=0xFE0C152C` (string `0`), `r1=0xFE0C1DF0` (source filename),
`r2=0xDC` (line 220), and `lr=0xFE0C1C48`.

The trace accesses the flash controller halfword registers
`0xC00000DC..0xC00000FA`. The upstream `eos_handle_flashctrl` only models
register `0x10`; these controller operations return zero. The
identification routine nevertheless returns `0x0006`, which is not one of the
accepted manufacturer codes; this measured value must not be described as a
verified physical flash identity. The last logged
MMIO operation before the assertion is a write to `0xC00000EA` from RAM
`0x0001D2B0`, returning to `0x0001D30C`.

This is evidence of unsupported flash-controller behavior, not proof of the
T7's actual flash manufacturer/device IDs or full transaction protocol. The
nearby 1300D model uses the same incomplete handler and supplies no independently
verified T7 identity. No flash ID was invented and no assertion was bypassed.
Progress beyond this point requires new flash-interface evidence/emulation.
No MPU handshake or GUI-startup milestone was verified; upstream generic MPU
spells/button-code fallbacks remain provisional.

## RAM initialization

The entry code itself performs the copy; see [startup-map.md](startup-map.md).
Before `cstart`, the probe compared all 315,804 copied bytes against the exact
ROM1 source and found a byte-for-byte match in both runs. The RAM copy hash is
`9c57fd4e542d72f3e96a6c5641e91d85f3edb9f1364dbba1049118c587d179e2`.
RAM targets `0x00029898` and `0x00005254` contain code and were actually called.
Direct entry does not omit this copy. Task creation/scheduler handoff reaches
`0xFE129718`; no task/task_attr field layout has been promoted.

## Reproduction and startup smoke test

Keep the verified ROM1 at `<workdir>/2000D/110/ROM1.BIN`, outside Git.
`qemu_workdir.py --firmware 110 --create-disks --command` verifies size/hash,
rejects ROM0, and creates disposable 64 MiB SD and 16 MiB CF images. Both disk
arguments explicitly specify `format=raw`.

Use fresh private result directories when repeating an experiment:

```bash
# Normal reset: first undefined-vector stop.
python3 tools/eos2000d/qemu_probe.py /private/workdir \
  --binary /path/to/build/arm-softmmu/qemu-system-arm \
  --log-dir /private/reset-results --stop-at 0xffff0004

# Default direct entry: observe inherited high-vector failure.
python3 tools/eos2000d/qemu_probe.py /private/workdir \
  --binary /path/to/build/arm-softmmu/qemu-system-arm \
  --log-dir /private/main-results --start-main --stop-at 0xffff0004

# Explicit vector-state experiment: stop at the assertion entry.
python3 tools/eos2000d/qemu_probe.py /private/workdir \
  --binary /path/to/build/arm-softmmu/qemu-system-arm \
  --log-dir /private/low-vector-results --start-main --low-vectors \
  --stop-at 0x3cbc

python3 tools/eos2000d/qemu_smoke.py \
  --probe-report /private/low-vector-results/low-vectors-1/result.json
```

The probe uses `-display none -monitor none -d in_asm,io,int,guest_errors`,
QMP, and GDB hardware breakpoints (`-S`); it saves the exact launch argument
vector, initial/final registers, observed stages, RAM-copy comparison,
serial output, combined stdout/stderr, and private instruction trace. Default
repeat count is two and execution bound is three seconds per run.

The report smoke check requires the canonical ROM1 identity, successful probe
termination, the verified RAM copy, and every required **executed** PC in order.
Default direct-entry and low-vector reports pass this limited init-entry check;
normal-reset reports fail it. Passing does not mean full Canon boot, ML
injection, camera safety, or verified peripheral behavior. CI tests remain
synthetic and contain no private ROM or disassembly bytes.

ROM1 map `0xF8000000/0x02000000`, its four aliases, entry `0xFE0C0000`, and
ROM0 omission are execution-tested emulator settings. RAM size, timer/IRQ IDs,
MPU parameters, LED/RTC settings and current-task structure assumptions are not
independently verified physical-camera constants. No ML payload, installer,
boot flag, firmware update, or physical-camera action was attempted.

## FlashIF follow-up

The complete 06/9F/05 serial-flash transaction is now traced. The ID wrapper
returns status zero; the caller then loads output manufacturer six. The six
comes from the earlier 06 command byte written into the unmodeled bank window.
All three accepted ID bytes are required; no installed physical chip identity
is proven. The assertion remains unresolved and QEMU behavior is unchanged.
See [flashif.md](flashif.md) for the exact sequence, register map and evidence.
Use `--timeout 15 --flashif-trace` for private diagnostics; complete MMIO-log
coverage and ARM condition checks prevent incomplete or invented accesses.
