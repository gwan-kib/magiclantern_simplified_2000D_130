# Canon EOS 2000D / Rebel T7 porting guide

> **Experimental development only. There is no camera-ready 2000D/T7 build in this repository yet.**
>
> Do not put an experimental `autoexec.bin`, QEMU build, installer, or firmware-update file on a physical camera until the relevant hardware-test milestone has been completed and documented.

## Target

This port targets the same camera family sold as:

- Canon EOS 2000D
- Canon EOS 1500D
- Canon EOS Rebel T7

The primary implementation target is **firmware 1.1.0**, matching the user's camera. Keep it on 1.1.0. Its existing private ROM1 is identified by hash and must be rehashed before each new analysis environment uses it. Firmware **1.3.0 remains a separate future port**, requiring its own canonical ROM and independent validation. Missing 1.3.0 evidence does not block independent 1.1.0 work; do not promote 1.1.0 values into 1.3.0 code.

The port is based on the current `dev` branch of `reticulatedpines/magiclantern_simplified`. The Phase 0 synchronization branch was based on upstream commit `1a0600a153476a6af740b3036d3aabc2b3318339`.

The local 1.1.0 analysis now confirms the reported entry and several startup call targets against the exact ROM1 hash. Other historical values remain candidates or are rejected; see [2000D-110 ROM analysis](2000D-110/rom-analysis.md). No 1.3.0 port constants are verified by the 1.1.0 image.

## Current status

Current active work: **1.1.0 loader/memory/minimum-interface verification and bounded offline diagnostic execution**. The original 1.3.0 backlog remains separate.

The repository is not yet a functioning 2000D port, but the project has moved beyond the repository-baseline stage.

Completed groundwork:

- Phase 0 repository synchronization/documentation/CI;
- a safe `platform/2000D.130/` skeleton;
- a current-generation minimal-build path, validated on supported camera 1100D.105;
- Phase 2 ROM-manifest/probe tooling and reverse-engineering documentation.

For the primary 1.1.0 target, [issue #44](https://github.com/gwan-kib/magiclantern_simplified_2000D_130/issues/44) tracks loader/reservation/minimum interfaces and [issue #45](https://github.com/gwan-kib/magiclantern_simplified_2000D_130/issues/45) tracks Canon → ML diagnostic → Canon execution. The newer “Firmware 1.1.0 post-startup observations” identifies a pending Intercom handshake ([issue #41](https://github.com/gwan-kib/magiclantern_simplified_2000D_130/issues/41)), not a PowerMgr deadlock. Full task/task_attr, safe reservation, minimum callable interfaces and a diagnostic channel remain unverified.

Still unresolved for the separate 1.3.0 port:

- a canonical firmware 1.3.0 ROM image and SHA-256;
- the exact 1.3.0 memory map and cache-hack patch locations;
- the exact DryOS task/task-attribute layouts;
- the minimum verified 1.3.0 stubs;
- the first real 2000D.130 minimal payload;
- a real QEMU boot of Canon firmware 1.3.0 (the model/workdir/smoke-test scaffolding is already prepared);
- physical-camera execution.

Prepared in advance, but not yet executable:

- Phase 4 hardware-test/recovery protocol;
- Phase 5 core, memory, GUI and display validation plans;
- Phase 6 feature matrix with CI evidence enforcement;
- release-hardening and reproducible-artifact gates.

Phase 1 issues #5–#7 remain open because their evidence must come from Phase 2. This is an intentional dependency, not a reason to pause Phase 2.

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
- Docutils / `rst2html` for module documentation generation (for Debian/Ubuntu: `python3-docutils`)
- `git`
- `zip`

A reference supported-camera build used by CI is:

```bash
make -C platform/1100D.105 clean
make -C platform/1100D.105 FATAL_WARNINGS=y -j2
```

This reference build checks that the synchronized upstream baseline and toolchain still work. CI also validates the 2000D platform skeleton and builds the modernized minimal/hello-world path on 1100D.105.

The first intended 1.1.0 executable milestone is the smallest evidence-backed offline diagnostic, without unnecessary display/task/menu dependencies. A physical LED interface is still unverified and must not be assumed. The richer hello-world follows only after its actual dependencies are verified.

### Important build-safety note

Changing build options can leave stale objects. Upstream specifically warns that switching options such as `CONFIG_QEMU` without cleaning may produce dangerous binaries. Run the relevant `make clean` whenever changing build modes.

## ROM analysis policy

Do **not** commit Canon ROM images or firmware-update binaries to this public repository.

For each firmware ROM, document:

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
Firmware: exact camera firmware version
ROM SHA-256:
Address:
How found:
Nearby strings / cross-references:
Equivalent pattern in reference camera:
Manual verification notes:
```

An address from another model is never sufficient evidence on its own.

## Reference cameras

The **EOS 2000D firmware 1.1.0** ROM is the exact same-body reverse-engineering baseline for 1.1.0 work and an index for locating analogous 1.3.0 routines. Its firmware addresses are not valid evidence for 1.3.0 on their own. Its supplied ROM0 dump fails the logged checksum and must not be used as a genuine bank.

The EOS 1300D / Rebel T6 is also a useful **late DIGIC 4+ structural reference** for cross-checking patterns.

Neither reference is an address source for firmware 1.3.0.

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

1. boot the verified Canon 1.1.0 ROM1 in an explicitly labeled direct-main experiment, then repeat for 1.3.0 once its ROM is available;
2. verify the cache-hack patch points;
3. execute a minimal ML payload;
4. prove Canon execution continues afterward;
5. automate the expected log markers in CI/local smoke tests.

## Physical-camera safety gate

No physical-camera test should occur before exact-target QEMU/minimal milestones and a validated written test/recovery procedure are complete. The existing 1.3.0 protocol is not a 1.1.0 authorization or procedure; it requires an exact-target counterpart before any future 1.1.0 physical test. This offline session authorizes no camera/card operation, installer FIR, boot flags or persistent changes.

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

Structural Phase 1 work is complete: `platform/2000D.130/` exists and the minimal-build infrastructure has been repaired.

The remaining Phase 1 acceptance criteria are evidence-dependent and intentionally feed from Phase 2:

- architecture is established, but memory/boot constants still need 1.3.0 ROM evidence;
- task/task_attr layouts still need 1.3.0 ROM evidence;
- the 2000D minimal payload still needs verified boot constants and stubs.

Those issues remain open until Phase 2 supplies the evidence.

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

The test/recovery procedure is prepared, but execution remains blocked by Phase 2/3 evidence.

Exit only after repeated minimal physical-camera boots and documented recovery behavior.

### Phase 5 — Core integration

Preparation is complete for staged stub evidence, memory analysis, GUI event mapping, display bring-up, and a restricted core policy.

Exit only after the restricted menu works with hardware-tested core dependencies and normal Canon behavior remains intact.

### Phase 6 — Feature enablement

A machine-readable feature matrix and CI validator are already in place.

Exit only after a useful low-risk feature subset is hardware-tested and every enabled feature/module has supporting evidence.

### Phase 7 — Release hardening

Release gates, artifact metadata, identity-guard requirements, beta-test rules, and installer restrictions are documented in advance.

Do not distribute a public test build until all earlier evidence gates are satisfied.

## Phase 2 analysis documents

- [ROM acquisition and manifest workflow](2000D-130/rom-analysis.md)
- [Verified 1.1.0 ROM analysis and manifest](2000D-110/rom-analysis.md)
- [1.1.0 startup map](2000D-110/startup-map.md)
- [1.1.0 task-structure findings](2000D-110/task-structure.md)
- [1.1.0 QEMU preparation](2000D-110/qemu.md)
- [Cache-hack candidate map](2000D-130/cache-hack-map.md)
- [Early diagnostic strategy](2000D-130/early-diagnostics.md)
- [Minimum stub checklist](2000D-130/minimal-stubs.md)
- [Phase 3 QEMU bring-up guide](2000D-130/qemu.md)
- [Phase 4 hardware-test protocol](2000D-130/hardware-test-protocol.md)
- [Phase 5 core bring-up](2000D-130/core-bringup.md)
- [Memory validation](2000D-130/memory-validation.md)
- [GUI bring-up](2000D-130/gui-bringup.md)
- [Display bring-up](2000D-130/display-bringup.md)
- [Restricted core policy](2000D-130/restricted-core.md)
- [Phase 6 feature matrix](2000D-130/feature-matrix.md)
- [Release hardening](2000D-130/release-hardening.md)

## Project tracking

- [Issue backlog](2000D-issue-backlog.md)
- [GitHub issues](https://github.com/gwan-kib/magiclantern_simplified_2000D_130/issues)
- [Detailed implementation plan](https://docs.google.com/document/d/1N2eZxIXB4-OioaZRMp44ALhHRFKak4nZpuIrtzg7mAU/edit)

Keep these documents current as the port progresses. When evidence changes an assumption, update the documentation in the same PR as the code that depends on it.
