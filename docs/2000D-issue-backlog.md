# Canon EOS 2000D / Rebel T7 Magic Lantern Port — Issue Backlog

Target: Canon EOS 1500D / 2000D / Rebel T7. Firmware 1.1.0 is the verified-ROM reverse-engineering baseline; firmware 1.3.0 remains the eventual platform target and must be verified independently.

Google Docs implementation plan:
https://docs.google.com/document/d/1N2eZxIXB4-OioaZRMp44ALhHRFKak4nZpuIrtzg7mAU/edit

> This backlog is intentionally staged. Do not skip milestone gates. The first meaningful success is a verified minimal payload, not a full Magic Lantern feature build.

The existing ML2000D issues below retain their original 1.3.0 acceptance criteria. Use the analyzed 1.1.0 ROM to validate the workflow, startup hypotheses, and QEMU ROM1 path first; create/update corresponding 1.1.0 evidence before transferring any method or assumption. Never treat 1.1.0 values as proof for 1.3.0.

---

## Milestone 0 — Repository baseline

### ML2000D-001 — Sync the fork with current Magic Lantern upstream

**Problem:** The experimental port fork diverged from `reticulatedpines/magiclantern_simplified`. A new camera port should not be built on stale loader/task/build infrastructure.

**Possible implementation**
- Add `reticulatedpines/magiclantern_simplified` as the canonical upstream reference.
- Compare the fork's `dev` branch against upstream `dev`.
- Preserve 2000D-specific README/porting notes.
- Rebase or merge carefully, preferring current upstream infrastructure where conflicts occur.
- Build at least one supported reference camera after synchronization.

**Acceptance criteria**
- Upstream relationship is documented.
- Relevant upstream changes are integrated.
- A known supported target builds from a clean checkout.
- No 2000D-specific addresses are introduced here.

**Dependencies:** None.

---

### ML2000D-002 — Add port status, workflow, and safety documentation

**Problem:** The README describes early porting work but not a reproducible workflow, milestone gates, hardware-test procedure, or recovery protocol.

**Possible implementation**
Create `docs/2000D-porting.md` with:
- exact camera and firmware target;
- ROM hash/size placeholders;
- build environment;
- QEMU workflow;
- hardware-test prerequisites;
- recovery procedure;
- address-discovery conventions;
- current milestone/blockers;
- links to the feature matrix and this backlog.

Update the README to link to it and clearly mark the port experimental.

**Acceptance criteria:** A new contributor can identify the target, current state, build path, safety constraints, and next milestone without reading commit history.

**Dependencies:** ML2000D-001.

---

### ML2000D-003 — Add CI for baseline and future 2000D builds

**Problem:** Low-level port work needs reproducible builds and fast detection of regressions.

**Possible implementation**
- Add GitHub Actions with the supported ARM cross-toolchain.
- Build one known-good camera target first.
- Treat warnings as errors where supported.
- Preserve useful logs/artifacts.
- Later add the 2000D minimal build and QEMU smoke test.

**Acceptance criteria**
- CI is green on the synchronized baseline.
- Build failures produce actionable logs.
- The workflow is reproducible locally.

**Dependencies:** ML2000D-001.

**Milestone 0 exit gate:** current upstream integrated, documentation present, CI builds a known-good target.

---

## Milestone 1 — Create a compilable 2000D platform skeleton

### ML2000D-004 — Create platform/2000D.130 skeleton

**Problem:** There is no actual `platform/2000D.130/` target.

**Possible implementation**
Create:
- `Makefile`
- `internals.h`
- `consts.h`
- `stubs.S`
- `features.h`
- `gui.h`
- minimal module configuration if required

Start conservatively. Do not copy firmware addresses from another camera. Leave unverified capabilities disabled.

**Acceptance criteria**
- `MODEL=2000D FW_VERSION=130` resolves to the new platform.
- Build failures concern genuinely missing camera data rather than missing platform plumbing.
- No foreign camera addresses exist in the target.

**Dependencies:** ML2000D-001.

---

### ML2000D-005 — Determine architecture and memory-map build parameters

**Problem:** The platform Makefile needs verified values for firmware entry, architecture, relocation, reserved memory, and loader choice.

**Possible implementation**
Use the 1.3.0 ROM to:
- confirm the firmware base around `0xFE0C0000`;
- determine CPU/ARM build assumptions;
- map ROM/RAM/BSS/heap regions;
- identify a safe relocation area;
- verify whether `boot-d45-ch.o` is appropriate;
- document evidence for every Makefile constant.

The 1300D may be used as a structural reference only.

**Acceptance criteria:** Every camera-specific build constant has ROM/disassembly evidence.

**Dependencies:** ML2000D-004, ML2000D-008.

---

### ML2000D-006 — Determine DryOS task and task_attr layouts

**Problem:** `struct task` is a known blocker, and a wrong layout could corrupt task-hook behavior even if compilation succeeds.

**Possible implementation**
Reverse engineer task creation, task lookup/info, dispatch, and current-task access. Determine offsets for:
- entry point;
- stack address/size;
- task name;
- task ID;
- state;
- context;
- linkage fields;
- CPU fields if present.

Compare against existing `CONFIG_TASK_STRUCT_V*` and `CONFIG_TASK_ATTR_STRUCT_V*` definitions. Add a new layout only if needed.

**Acceptance criteria**
- Selected layouts match ROM evidence.
- Compile-time size checks pass.
- No define is chosen merely to silence the compiler.

**Dependencies:** ML2000D-004, ML2000D-008.

---

### ML2000D-007 — Get minimal/hello-world compiling cleanly

**Problem:** The first target should be a minimal payload, not the full Magic Lantern application.

**Possible implementation**
- Build `minimal/hello-world` for `MODEL=2000D`.
- Link only required symbols.
- Fix platform configuration/header issues.
- Keep menu/modules/RAW/property-changing code out.
- Never use dummy addresses just to satisfy the linker.

**Acceptance criteria**
- Clean checkout builds the minimal 2000D payload reproducibly.
- No unresolved symbols.
- No guessed or borrowed addresses.

**Dependencies:** ML2000D-004, 005, 006, 011.

**Milestone 1 exit gate:** a real `2000D.130` platform exists and minimal/hello-world builds cleanly.

---

## Milestone 2 — Reverse engineer the loader and minimum firmware interface

### ML2000D-008 — Verify and document the firmware 1.3.0 ROM dump

**Problem:** All hard-coded addresses need to refer to one exact firmware image.

**Possible implementation**
Record without committing Canon ROM bytes:
- ROM size;
- cryptographic hash;
- firmware/version strings;
- ROM base;
- startup signature observations;
- extraction method;
- analysis project conventions.

**Acceptance criteria**
- One canonical ROM image is identified by hash.
- Future address discoveries cite that image.
- No Canon firmware binary is committed.

**Dependencies:** ML2000D-001.

---

### ML2000D-009 — Reverse engineer cache-hack boot addresses

**Problem:** `boot-d45-ch.o` requires exact firmware-specific startup and patch locations.

**Possible implementation**
Locate and verify:
- firmware entry;
- `cstart`;
- `bzero32`;
- `create_init_task`;
- `init_task`;
- init-task patch/pointer;
- BSS/allocator-end setup;
- required branch/relocation fixes.

Cross-check against `src/boot-d45-ch.c` and known late DIGIC 4+ patterns.

**Acceptance criteria:** Every boot constant has disassembly context and manual verification.

**Dependencies:** ML2000D-008.

---

### ML2000D-010 — Identify card LED and early-boot diagnostics

**Problem:** Early failures may occur before display or file I/O exists.

**Possible implementation**
- Locate the card-access LED register or safe Canon LED routine.
- Define unique blink patterns for loader entry, ML init, success, and failure.
- Investigate serial/debug output as a second channel.
- Keep diagnostics independent of the full GUI.

**Acceptance criteria:** Minimal code has at least one low-level, observable diagnostic channel.

**Dependencies:** ML2000D-008.

---

### ML2000D-011 — Build the minimum verified stubs.S for minimal boot

**Problem:** The platform needs real Canon/DryOS entry points, not copied stubs from another camera.

**Possible implementation**
Add only symbols required by the minimal loader/payload. Locate them with:
- string references;
- function signatures;
- control-flow comparison;
- manual Ghidra/IDA confirmation.

Comment each stub with how it was found.

**Acceptance criteria**
- Minimal path uses only verified 1.3.0 stubs.
- No placeholder or foreign-camera addresses remain.

**Dependencies:** ML2000D-008, 009.

**Milestone 2 exit gate:** verified minimal boot map, diagnostic channel, and no copied foreign addresses.

---

## Milestone 3 — QEMU first execution

### ML2000D-012 — Add or adapt qemu-eos support for the 2000D

**Problem:** Loader assumptions should be tested in emulation before a physical camera.

**Possible implementation**
Adapt qemu-eos using the 1300D only as a structural reference:
- ROM mapping;
- RAM ranges;
- DIGIC generation;
- CPU entry point;
- minimum required MMIO/peripherals;
- debug tracing.

Initially tolerate unrelated unimplemented peripherals if startup reaches the loader path deterministically.

**Acceptance criteria:** Canon 1.3.0 reaches a repeatable boot point in QEMU with useful traces.

**Dependencies:** ML2000D-005, 008, 009.

---

### ML2000D-013 — Execute minimal/hello-world in QEMU

**Problem:** Compilation does not prove relocation, cache patches, or task handoff are correct.

**Possible implementation**
Instrument:
- Canon firmware entry;
- `copy_and_restart`;
- init-task patch/handoff;
- ML pre/local init;
- minimal payload entry;
- continued Canon execution.

Use qprintf/log markers and breakpoints.

**Acceptance criteria:** A repeatable trace proves Canon startup → ML loader → minimal payload → continued Canon execution.

**Dependencies:** ML2000D-007, 012.

---

### ML2000D-014 — Add automated QEMU loader smoke tests

**Problem:** Once the loader works, regressions should be detected automatically.

**Possible implementation**
- Launch QEMU with a bounded timeout.
- Capture debug output.
- Assert ordered markers for Canon startup, ML loader, payload, and continued boot.
- Fail on missing markers, crash, or timeout.
- Run in CI if practical.

**Acceptance criteria:** Deliberately broken loader changes fail; known-good builds pass repeatedly.

**Dependencies:** ML2000D-013, 003.

**Milestone 3 exit gate:** minimal ML execution is demonstrated in QEMU and regression-tested.

---

## Milestone 4 — First controlled physical-camera execution

### ML2000D-015 — Document first hardware-test and recovery protocol

**Problem:** Early camera-port testing can hang the camera or create boot loops.

**Possible implementation**
Document:
- exact firmware verification;
- full battery requirement;
- SD-card preparation;
- exact card files;
- expected LED behavior;
- maximum wait before recovery;
- battery-removal recovery;
- non-bootable rescue card;
- log collection;
- prohibition on QEMU-only builds on hardware.

**Acceptance criteria:** Another developer can execute and recover from the first test without undocumented steps.

**Dependencies:** ML2000D-013, 014.

---

### ML2000D-016 — Achieve first physical minimal LED/hello-world execution

**Problem:** QEMU cannot validate every hardware-specific startup detail.

**Possible implementation**
Run only the minimal loader/payload:
- emit the verified diagnostic LED pattern;
- do not load modules/full menu;
- do not change persistent properties;
- do not enable RAW/EDMAC/timing hacks;
- continue Canon startup afterward;
- log outcomes.

**Acceptance criteria**
- 10 cold boots and 10 warm/restart cycles succeed.
- Canon reaches normal operation afterward.
- Removing the ML card restores stock behavior.

**Dependencies:** ML2000D-015, 010, 011.

---

### ML2000D-017 — Validate shutdown, sleep, card-door, and recovery behavior

**Problem:** A port that boots can still fail during shutdown or power-state transitions.

**Possible implementation**
Test:
- normal power-off;
- battery removal/reinsert;
- auto power-off;
- wake;
- card-door handling;
- boot without `autoexec.bin`;
- boot with non-bootable card;
- Live View entry/exit if safe.

**Acceptance criteria:** No persistent boot loop or unrecoverable state; stock behavior returns when ML is absent.

**Dependencies:** ML2000D-016.

**Milestone 4 exit gate:** minimal code runs repeatedly on hardware and recovery is reliable.

---

## Milestone 5 — Core Magic Lantern integration

### ML2000D-018 — Expand stubs.S for core DryOS, memory, timers, and file I/O

**Problem:** A restricted ML core needs more verified Canon/DryOS entry points.

**Possible implementation**
Expand by subsystem:
- tasks;
- semaphores;
- message queues;
- timers;
- allocation/free;
- DebugMsg;
- FIO open/read/write/seek/close/create/remove/rename;
- property registration/delivery without enabling unsafe writes.

Add a small validation for each subsystem before using it elsewhere.

**Acceptance criteria**
- Core stubs are verified and grouped by subsystem.
- Tests/logs demonstrate plausible operation.
- No enabled path contains placeholder addresses.

**Dependencies:** ML2000D-017, 008.

---

### ML2000D-019 — Validate ML memory reservation and allocator behavior

**Problem:** ML must reserve memory without overlapping Canon heaps, BSS, or frame buffers.

**Possible implementation**
- Verify `RESTARTSTART` and reserved-memory calculation at runtime.
- Measure memory regions with/without ML.
- Add canaries/assertions where practical.
- Exercise repeated allocate/free cycles.
- Track memory statistics across repeated boots.

**Acceptance criteria:** No overlap, progressive leak, unstable reserved-size calculation, or Canon heap corruption is observed.

**Dependencies:** ML2000D-018, 005.

---

### ML2000D-020 — Reverse engineer GUI events and button mappings

**Problem:** ML cannot expose a usable menu until T7 input events are known.

**Possible implementation**
Use a minimal button logger or safe GUI hooks to map:
- MENU;
- SET;
- D-pad;
- Q;
- INFO/DISP;
- playback;
- Live View;
- zoom;
- shutter half/full press;
- relevant wheel/dial events.

Populate `gui.h` only with observed values.

**Acceptance criteria:** A diagnostic build reliably identifies every control needed to open, navigate, select, and exit the ML menu.

**Dependencies:** ML2000D-017, 018.

---

### ML2000D-021 — Reverse engineer bitmap display and basic Live View buffers

**Problem:** Overlays need correct bitmap VRAM, display geometry, palette, redraw handling, and basic Live View buffers.

**Possible implementation**
Identify:
- bitmap VRAM;
- LCD palette/equivalent;
- screen geometry/pitch;
- display-state object;
- redraw mechanism;
- basic YUV Live View buffers.

Start with a harmless overlay. Do not enable RAW/EDMAC capture here.

**Acceptance criteria:** A test overlay draws and clears correctly without corrupting Canon UI.

**Dependencies:** ML2000D-017, 018.

---

### ML2000D-022 — Bring up a restricted Magic Lantern core and menu

**Problem:** This is the first integrated proof of loader, tasking, memory, file I/O, input, and display.

**Possible implementation**
Enable only:
- basic menu framework;
- debug/about/status pages;
- safe settings/log files.

Keep disabled:
- RAW video;
- FPS override;
- sensor timing hacks;
- persistent Canon property changes;
- unverified modules.

**Acceptance criteria**
- Menu opens, navigates, selects, and exits reliably.
- Settings/log files work.
- Normal Canon capture behavior remains functional.
- Repeated boot/use/shutdown tests remain stable.

**Dependencies:** ML2000D-018, 019, 020, 021.

**Milestone 5 exit gate:** a restricted but stable ML core/menu runs on hardware.

---

## Milestone 6 — Controlled feature enablement

### ML2000D-023 — Create and maintain a per-feature validation matrix

**Problem:** A camera should not be called globally supported when only some features are proven.

**Possible implementation**
Create `docs/feature-matrix.md` with statuses:
- Disabled
- Compiles
- QEMU-tested
- Hardware-tested
- Experimental
- Stable

For each feature record dependencies, required stubs/constants, test procedure, limitations, and last tested commit.

**Acceptance criteria:** No feature is enabled without a matrix entry and supporting evidence.

**Dependencies:** ML2000D-022.

---

### ML2000D-024 — Enable low-risk features first; defer hardware-intensive features

**Problem:** ML features have very different risk profiles.

**Possible implementation**
Enable in tiers:
1. UI/status/info features using established APIs.
2. Intervalometer/task/file-I/O features.
3. Display/exposure helpers after backing APIs are validated.
4. Separate future issues for RAW video, EDMAC raw capture, FPS/timing overrides, sensor-register changes, installer firmware files, and persistent Canon property changes.

Each feature needs its own focused test and rollback path.

**Acceptance criteria:** A useful subset of features is hardware-tested and documented while unverified high-risk features remain disabled.

**Dependencies:** ML2000D-023.

**Milestone 6 exit gate:** a useful experimental feature subset works without unverified low-level hacks.

---

## Later release-hardening work

After ML2000D-024, create separate release issues for:
- exact camera/firmware identity guards;
- reproducible release artifacts and checksums;
- installer/boot-flag work only after runtime stability;
- limited external beta testing;
- structured crash/log collection;
- final known-issues and recovery documentation.

## Critical dependency path

`001 → 004 → 005/006 → 007 → 008/009/010/011 → 012 → 013 → 014 → 015 → 016 → 017 → 018/019/020/021 → 022 → 023 → 024`

Documentation and CI can run in parallel with ROM analysis. GUI/display work should wait until minimal hardware execution is proven. Feature work should wait until the restricted ML menu is stable.
