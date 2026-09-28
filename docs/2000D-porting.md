# Canon EOS 2000D / Rebel T7 porting guide

> **Experimental development only. There is no camera-ready 2000D/T7 build in this repository yet.**
>
> Do not put an experimental `autoexec.bin`, QEMU build, installer, or firmware-update file on a physical camera until the relevant hardware-test milestone has been completed and documented.

## Target

This port targets the same camera family sold as:

- Canon EOS 2000D
- Canon EOS 1500D
- Canon EOS Rebel T7

The intended firmware target is **1.3.0**.

The port is based on the current `dev` branch of `reticulatedpines/magiclantern_simplified`. The Phase 0 synchronization branch was based on upstream commit `1a0600a153476a6af740b3036d3aabc2b3318339`.

The older experimental fork contained notes claiming a successful ROM dump, a firmware signature near `0xFE0C0000`, and an intended cache-hack loader. Those observations are treated as **leads, not verified port constants**, until ML2000D-008 and the related reverse-engineering issues document the exact ROM hash and supporting disassembly.

## Current status

Current milestone: **Phase 0 — Repository baseline**

The repository is not yet a functioning 2000D port. In particular:

- there is no verified `platform/2000D.130/` implementation;
- the correct DryOS task/task-attribute layouts still need to be established from firmware 1.3.0;
- cache-hack patch points and other firmware addresses still need ROM-backed verification;
- `minimal/hello-world` has not yet been demonstrated for this camera;
- QEMU execution has not yet been demonstrated for this camera;
- no physical-camera execution is approved at this stage.

See [2000D-issue-backlog.md](2000D-issue-backlog.md) and the GitHub issue tracker for the staged implementation plan.

## Upstream synchronization

This fork should remain close to:

`https://github.com/reticulatedpines/magiclantern_simplified`

Recommended local setup:

```bash
git remote add upstream https://github.com/reticulatedpines/magiclantern_simplified.git
git fetch upstream
```

Before starting a new porting phase:

```bash
git checkout dev
git fetch upstream
git log --oneline --left-right dev...upstream/dev
```

Prefer integrating upstream changes through a dedicated branch/PR so 2000D-specific documentation and future platform work can be reviewed separately from upstream changes.

Do not silently copy old camera-specific files over newer upstream versions just to resolve conflicts.

## Build environment

Magic Lantern's upstream build documentation describes a GNU Make build using Python 3 and an ARM bare-metal GCC toolchain.

Typical Linux/WSL dependencies:

- GNU Make
- Python 3
- `arm-none-eabi-gcc` and related binutils
- Newlib headers for the ARM bare-metal toolchain (for Debian/Ubuntu: `libnewlib-arm-none-eabi`)
- `git`
- `zip`

A reference supported-camera build used by Phase 0 CI is:

```bash
make -C platform/1100D.105 clean
make -C platform/1100D.105 FATAL_WARNINGS=y -j2
```

This reference build only checks that the synchronized upstream baseline and toolchain still work. It does **not** indicate that the 2000D target exists or is safe.

When a real 2000D target is added, the first intended build target is `minimal/hello-world`, not the full Magic Lantern feature set.

### Important build-safety note

Changing build options can leave stale objects. Upstream specifically warns that switching options such as `CONFIG_QEMU` without cleaning may produce dangerous binaries. Run the relevant `make clean` whenever changing build modes.

## ROM analysis policy

Do **not** commit Canon ROM images or firmware-update binaries to this public repository.

For the canonical firmware 1.3.0 ROM, document:

- SHA-256 hash;
- exact byte size;
- firmware/version strings found in the image;
- assumed ROM base;
- extraction/dump method;
- analysis-tool version;
- any loader/task/address findings with enough context to reproduce them.

Suggested evidence format for an address:

```text
Symbol / purpose:
Firmware: 2000D 1.3.0
ROM SHA-256:
Address:
How found:
Nearby strings / cross-references:
Equivalent pattern in reference camera:
Manual verification notes:
```

An address from another model is never sufficient evidence on its own.

## Reference cameras

The EOS 1300D / Rebel T6 is a useful **late DIGIC 4+ structural reference** for some reverse-engineering patterns.

It is not an address source.

Likewise, the EOS 200D / Rebel SL2 is a different DIGIC-generation camera and must not be confused with the EOS 2000D / Rebel T7 because of the similar product name.

## QEMU workflow

The sibling emulator project is:

`https://github.com/reticulatedpines/qemu-eos`

QEMU should be used before physical-camera testing for loader and early-init work wherever practical.

A build made with:

```bash
CONFIG_QEMU=y
```

is for emulation. Upstream warns that QEMU builds are not for physical cameras and may hang a real camera until the battery is removed.

Planned QEMU progression:

1. boot the Canon 1.3.0 ROM far enough to inspect startup;
2. verify the cache-hack patch points;
3. execute a minimal ML payload;
4. prove Canon execution continues afterward;
5. automate the expected log markers in CI/local smoke tests.

## Physical-camera safety gate

No physical-camera test should occur before the QEMU/minimal milestones and a written test/recovery procedure are complete.

When hardware testing eventually begins:

- verify the camera is exactly the intended model and firmware revision;
- use a fully charged battery;
- use a known-good SD card dedicated to development;
- keep a second non-bootable rescue card available;
- test only the smallest payload needed for the current milestone;
- do not enable modules, RAW capture, timing hacks, sensor-register writes, or persistent property changes during first execution;
- define the expected LED/log behavior before powering on;
- define a maximum wait time before aborting a hung test;
- if the camera is unresponsive, power off and remove/reinsert the battery according to the documented test procedure;
- confirm the camera boots normally with the ML card removed before continuing.

## Persistent state and installer policy

Persistent Canon properties, boot flags, installer firmware files, and similar state-changing mechanisms are **late-stage work**.

Until the core port is stable:

- do not reuse another camera's `ML-SETUP.FIR`;
- do not guess property IDs or write persistent properties;
- do not claim an installer path is safe because it works on a related model.

Installer/recovery work must have its own test plan.

## Milestone gates

### Phase 0 — Repository baseline

Exit only when:

- current upstream is integrated;
- porting/safety documentation exists;
- CI builds a known-good supported camera from the synchronized baseline.

### Phase 1 — Platform skeleton

Exit only when:

- `platform/2000D.130/` exists;
- architecture/memory/task layout decisions are evidence-backed;
- `minimal/hello-world` compiles with no guessed addresses.

### Phase 2 — Minimum firmware interface

Exit only when:

- the canonical ROM is identified by hash;
- cache-hack addresses are verified;
- early diagnostics exist;
- minimal stubs are ROM-backed.

### Phase 3 — QEMU execution

Exit only when:

- the Canon ROM reaches a useful repeatable point in QEMU;
- the minimal payload executes;
- Canon execution continues;
- a repeatable smoke test exists.

### Phase 4 — Controlled hardware execution

Exit only after repeated minimal physical-camera boots and documented recovery behavior.

Later phases then bring up core ML services, the restricted menu, and individual features one subsystem at a time.

## Project tracking

- [Issue backlog](2000D-issue-backlog.md)
- [GitHub issues](https://github.com/gwan-kib/magiclantern_simplified_2000D_130/issues)
- [Detailed implementation plan](https://docs.google.com/document/d/1N2eZxIXB4-OioaZRMp44ALhHRFKak4nZpuIrtzg7mAU/edit)

Keep these documents current as the port progresses. When evidence changes an assumption, update the documentation in the same PR as the code that depends on it.
