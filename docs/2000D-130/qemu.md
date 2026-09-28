# EOS 2000D / Rebel T7 Phase 3 QEMU bring-up

## Status

Phase 3 preparatory work is implemented, but a real 2000D firmware 1.3.0 boot
cannot be demonstrated until Phase 2 provides verified firmware images and
startup constants.

The supported emulator baseline is:

`reticulatedpines/qemu-eos`, branch `qemu-eos-v4.2.1`.

The Magic Lantern upstream repository currently identifies this as the ML
team's supported qemu-eos branch.

## What can be prepared before the ROM exists

The repository now provides:

- an idempotent qemu-eos source patcher for a provisional 2000D model;
- a qemu-eos work-directory validator;
- sparse SD/CF test-image creation;
- a bounded QEMU smoke-test runner;
- ordered boot-marker validation;
- unit tests for all of the above.

These tools deliberately do not fabricate Canon ROM files or claim successful
emulation.

## Provisional model basis

qemu-eos already contains a late DIGIC IV **1300D** model. It is the closest
existing emulator model to the 2000D.

The historical Magic Lantern **2000D.110** port also provides useful
same-body evidence.

The provisional QEMU model uses:

| Parameter | Provisional value | Basis / confidence |
|---|---:|---|
| DIGIC | 4 | hardware fact; high |
| RAM | 0x10000000 (256MB) | 1300D model; provisional |
| ROM0 size | 0x02000000 | 1300D model; provisional |
| ROM1 size | 0x02000000 | 1300D model; provisional |
| qemu `firmware_start` | 0xFF0C0000 | 1300D qemu model; needs 2000D validation |
| firmware version selector | 130 | target naming convention |
| current task address | 0x31170 | matches historical 2000D.110 and 1300D.110 |
| card LED | 0xC0220134 | historical 2000D.110 and 1300D.110 |
| timer / IRQ / MPU values | 1300D-derived | provisional QEMU bring-up values |

These values are for the emulator scaffold only. They are not evidence for
physical-camera Magic Lantern constants.

## Important address distinction

There is a known point requiring validation:

- historical Magic Lantern 2000D.110 startup analysis uses addresses in the
  `0xFE0C....` region;
- qemu-eos' existing 1300D model records
  `firmware_start = 0xFF0C0000`.

qemu-eos also contains 1300D-specific code comments referencing execution at
`0xFE0C038C`.

Therefore `firmware_start` should not be interpreted as identical to
Magic Lantern's `MAIN_FIRMWARE_ADDR` without understanding qemu-eos' ROM
mirroring/alias behavior. Phase 2/3 traces must resolve this before using
QEMU observations as physical-camera address evidence.

## Patch qemu-eos

Clone the supported branch:

```bash
git clone --depth 1 --branch qemu-eos-v4.2.1 \
  https://github.com/reticulatedpines/qemu-eos.git
```

From this Magic Lantern repository:

```bash
python3 tools/eos2000d/qemu_eos_patch.py ../qemu-eos
```

The patcher modifies only:

- `hw/eos/model_list.h`;
- `hw/eos/model_list.c`;
- `hw/eos/eos.c`.

It adds the model name, provisional descriptor, QEMU machine initializer and
machine registration. It is idempotent and fails if expected source anchors
are absent.

The initial scaffold intentionally does **not** automatically enable every
1300D-specific special-case workaround in `eos.c`. If the real 1.3.0 ROM
stalls on the same checks, enable an equivalent workaround only after the
trace proves it is needed.

## Build qemu-eos

Typical QEMU 4.2 build flow:

```bash
cd ../qemu-eos
./configure --target-list=arm-softmmu
make -j"$(nproc)"
```

Host package requirements vary by Linux distribution and qemu-eos/QEMU
version. Treat build-system compatibility problems separately from camera
model correctness.

## Prepare the work directory

qemu-eos loads EOS firmware files from:

```text
$QEMU_EOS_WORKDIR/<CAMERA>/<FIRMWARE>/
```

For this scaffold:

```text
$QEMU_EOS_WORKDIR/2000D/130/ROM0.BIN
$QEMU_EOS_WORKDIR/2000D/130/ROM1.BIN
```

Create the directory and disposable block-device images:

```bash
python3 tools/eos2000d/qemu_workdir.py ~/qemu-2000d \
  --create --create-disks --command
```

The tool intentionally exits with a missing-ROM status until verified
`ROM0.BIN` and `ROM1.BIN` are supplied.

### Why there is a dummy CF image

Current qemu-eos initialization unconditionally expects an IDE/CF backend,
even for an SD-camera model. The helper therefore creates a small sparse
`cf.img` so the emulator can progress through that generic initialization
path. It does not imply that the EOS 2000D has a CF slot.

## Provisional launch form

After qemu-eos is patched/built and verified ROM files exist, the helper
prints a command equivalent to:

```bash
QEMU_EOS_WORKDIR=~/qemu-2000d \
  ./arm-softmmu/qemu-system-arm \
  -M 2000D,firmware=130 \
  -drive file=~/qemu-2000d/cf.img,if=ide,format=raw \
  -sd ~/qemu-2000d/sd.img \
  -serial stdio -display none -d io,int
```

This command is a bring-up starting point, not a claim that the current
unverified model will boot.

## Phase 3 trace progression

### Stage 1 — Canon ROM startup

First target:

- QEMU recognizes `-M 2000D`;
- ROM files load from the expected directory;
- CPU executes stable Canon startup code;
- repeated runs stop/fail at the same point.

Record the PC, MMIO access and interrupt behavior at the first deterministic
stall.

### Stage 2 — Magic Lantern loader

After Phase 2 supplies the verified loader constants, build Magic Lantern
with `CONFIG_QEMU=y`.

Required trace evidence:

1. Canon firmware begins execution.
2. `copy_and_restart` is entered.
3. the cache-hack init-task replacement is applied.
4. `my_init_task` is entered.

### Stage 3 — Minimal payload

Use the smallest verified 2000D diagnostic payload before the graphical
hello-world.

Required evidence:

1. minimal payload entry;
2. observable/log diagnostic;
3. Canon `init_task` is still called;
4. Canon execution continues beyond the ML handoff.

Only after this works should the richer bitmap hello-world be attempted.

## Smoke-test harness

Analyze an existing log:

```bash
python3 tools/eos2000d/qemu_smoke.py \
  --log-in qemu.log \
  --expect "[EOS] loading" \
  --expect "[BOOT] changing init_task" \
  --expect "[BOOT] calling post_init_task" \
  --expect "[BOOT] my_init_task completed."
```

Or run QEMU with a bounded timeout:

```bash
python3 tools/eos2000d/qemu_smoke.py \
  --timeout 20 \
  --log-out qemu.log \
  --expect "[EOS] loading" \
  --expect "[BOOT] changing init_task" \
  -- \
  ./arm-softmmu/qemu-system-arm ...
```

A timeout is acceptable if every expected marker was reached in order because
the camera firmware/emulator normally continues running. An early crash or a
missing/out-of-order marker fails the smoke test.

The exact marker list remains provisional until the first real 1.3.0
execution trace exists.

## Phase 3 issue status

### ML2000D-012

Scaffolding is implementable now, but the acceptance criterion remains open:
the real 1.3.0 ROM must reach a repeatable boot point.

### ML2000D-013

Instrumentation plan and harness are ready. Actual ML execution remains
blocked by the verified Phase 2 boot constants/stubs and a 2000D QEMU build.

### ML2000D-014

The generic bounded smoke-test runner and ordered-marker assertion are ready
and unit-tested. The issue remains open until a known-good 2000D QEMU run
exists so the test can prove both success and deliberate-regression failure.
