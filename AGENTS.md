# AGENTS.md

## Purpose

This repository is an **experimental Magic Lantern port for the Canon EOS 1500D / 2000D / Rebel T7**. Firmware **1.1.0 is the primary implementation target**, matching the user's physical camera. Firmware **1.3.0 remains a separate future port and requires its own exact ROM evidence**.

This file is the operating guide for coding/research agents working in this repository. Read it before making changes.

The highest-priority rule is:

> **Never invent, guess, or blindly copy firmware-specific addresses, structure layouts, patch points, GUI codes, buffer addresses, or hardware register assumptions into active 2000D.130 code.**

A build that compiles is not evidence that it is safe.

---

## Current project state

The project has completed most useful scaffolding that does not require the canonical Canon firmware 1.3.0 ROM. A user-supplied 1.1.0 ROM1 dump is now locally verified and analyzed; no Canon bytes are stored in this repository.

### Completed

- Phase 0 repository baseline / upstream synchronization.
- CI for a known-good reference target (`1100D.105`).
- Safe `platform/2000D.130/` skeleton.
- Current-generation minimal-build path repaired and validated on `1100D.105`.
- ROM manifest / local ROM probe tooling.
- Firmware 1.1.0 ROM1 integrity manifest and startup analysis in `docs/2000D-110/`.
- 1.1.0 QEMU workdir profile requiring ROM1 only; the supplied ROM0 dump fails its logged hash and is not used.
- Cache-hack reverse-engineering map.
- Early diagnostic / LED plan.
- Minimum-stub evidence plan.
- Provisional qemu-eos 2000D model patcher.
- QEMU workdir and smoke-test tooling.
- Physical-camera test/recovery protocol.
- Core/stub/memory/GUI/display bring-up plans.
- Restricted-core policy.
- Feature-validation matrix and CI enforcement.
- Release-hardening / release-manifest preparation.

### Current target and evidence blockers

The user's explicit firmware-1.1.0 scope supersedes older guidance that made
1.3.0 acquisition a prerequisite to every implementation phase. Keep the
camera on 1.1.0. Missing 1.3.0 evidence blocks only the separate 1.3.0 work;
preserve that platform, its guards and original issue acceptance criteria.

For 1.1.0, locate and rehash the existing private ROM1 before use. Do not
request another identical dump without first checking available artifacts.
The invalid ROM0 must never be loaded or fabricated. Read the newer
“Firmware 1.1.0 post-startup observations” before interpreting older waits.

The current 1.1.0 chain is:

```text
canonical 1.1.0 ROM + reproducible private QEMU environment
        ↓
verified loader, reservation, required task/interfaces and exact identity (#44)
        ↓
offline Canon → ML diagnostic → Canon milestone (#45)
        ↓
target-specific physical evidence and recovery gates
```

KI-019 (independent installed flash identity) and KI-020 / #41 (initial
Intercom state and response protocol) remain separate evidence boundaries.
An opt-in C2/25/39 experiment does not close either issue. Static analysis
and independent tooling work may continue while a runtime dependency blocks
a different task. The full task/task_attr variant, safe memory reservation
and minimal diagnostic interface remain unresolved.

The future 1.3.0 chain still needs a canonical 1.3.0 ROM, followed by its own
boot/memory/task/stub verification, minimal build, Canon/ML execution and
physical gates. Never transfer 1.1.0 addresses as 1.3.0 proof.

---

## Source-of-truth documents

Before changing a subsystem, read the relevant document.

### Project status / safety

- `README.md`
- `docs/2000D-porting.md`
- `docs/2000D-issue-backlog.md`

### Phase 2 — firmware analysis

- `docs/2000D-110/rom-analysis.md`
- `docs/2000D-110/rom-manifest.json`
- `docs/2000D-110/startup-map.md`
- `docs/2000D-110/task-structure.md`
- `docs/2000D-110/stub-evidence.json`
- `docs/2000D-110/qemu.md`

- `docs/2000D-130/rom-analysis.md`
- `docs/2000D-130/rom-manifest.json`
- `docs/2000D-130/cache-hack-map.md`
- `docs/2000D-130/early-diagnostics.md`
- `docs/2000D-130/minimal-stubs.md`
- `docs/2000D-130/stub-evidence.json`

### Phase 3 — QEMU

- `docs/2000D-130/qemu.md`

### Phase 4 — hardware

- `docs/2000D-130/hardware-test-protocol.md`
- `docs/2000D-130/hardware-test-record.template.json`

### Phase 5 — core

- `docs/2000D-130/core-bringup.md`
- `docs/2000D-130/memory-validation.md`
- `docs/2000D-130/gui-bringup.md`
- `docs/2000D-130/display-bringup.md`
- `docs/2000D-130/restricted-core.md`

### Phase 6 — features

- `docs/2000D-130/feature-matrix.md`
- `docs/2000D-130/feature-matrix.json`

### Phase 7 — release

- `docs/2000D-130/release-hardening.md`
- `docs/2000D-130/release-manifest.template.json`

---

## Reference-camera policy

### Preferred references

1. **Historical EOS 2000D firmware 1.1.0 port**
   - exact local ROM1 image identified by SHA-256 and analyzed in `docs/2000D-110/`;
   - verified addresses may be used only for 1.1.0 experiments;
   - remains a same-body structural reference, **not an address source for 1.3.0**;
   - ROM0 dump hash mismatch is documented; never use it as a real ROM image.

2. **EOS 1300D / Rebel T6**
   - useful late DIGIC IV+ architectural cross-check;
   - useful for qemu-eos model structure;
   - **not an address source for 2000D.130**.

3. **EOS 1100D.105**
   - supported build regression target;
   - useful for build-system sanity;
   - not a firmware-address reference for the T7.

### Do not confuse

**EOS 200D / Rebel SL2 is not EOS 2000D / Rebel T7.**

The 200D is a different DIGIC-generation camera.

---

## Firmware evidence standard

Every firmware-specific value promoted into executable code must cite the exact target image: firmware 1.1.0 for a future 2000D.110 path, firmware 1.3.0 for 2000D.130. Keep verified facts, candidates and unresolved assumptions distinct.

The 1.1.0 baseline has its own evidence ledger. Do not transfer its values into 1.3.0 code without finding and validating the corresponding 1.3.0 behavior independently.

For an address or structure decision, record at least:

- canonical exact-target ROM SHA-256;
- address / offset;
- ROM vs RAM callable address when applicable;
- how it was identified;
- nearby strings / xrefs / call graph / instruction signature;
- historical 2000D.110 equivalent if useful;
- confidence / review notes;
- QEMU or hardware evidence when applicable.

Do not use comments such as "same as 1300D" or "probably unchanged" as proof.

---

## Canon firmware files

Do **not** commit Canon firmware/ROM/update binaries to this public repository.

Examples that must stay out of Git:

- raw ROM dumps;
- Canon firmware ZIPs;
- FIR/update binaries;
- extracted copyrighted firmware sections.

What may be committed:

- SHA-256 hashes;
- byte sizes;
- filenames;
- extraction scripts that contain no Canon firmware bytes;
- analysis notes;
- addresses/disassembly summaries;
- reproducible metadata.

---

## Platform rules

Existing future-target directory:

`platform/2000D.130/`

A dedicated 2000D.110 executable path depends on issue #44. Do not add copied
historical constants or speculative platform scaffolding to imply readiness.

### Keep active values conservative

The current platform intentionally blocks a normal build while critical firmware values are unverified.

Do not bypass those guards merely to make the build succeed.

### Stubs

Any active `NSTUB(...)` or `THUMB_FN(...)` must have a matching entry in:

`docs/2000D-130/stub-evidence.json`

CI validates this with:

`tools/eos2000d/stub_evidence.py`

### Features

`platform/2000D.130/features.h` is an **explicit allowlist**.

Do not include:

`all_features.h`

during bring-up.

Any enabled `FEATURE_*` must have an evidence-backed entry in:

`docs/2000D-130/feature-matrix.json`

CI validates this with:

`tools/eos2000d/feature_matrix.py`

### Modules

`platform/2000D.130/modules.included` should remain empty until a module has an evidence-backed feature-matrix entry.

---

## Pre-ROM forbidden changes

Until the canonical ROM is verified and the relevant milestone explicitly changes this policy, do not enable:

- `CONFIG_PROP_REQUEST_CHANGE`
- `CONFIG_DUMPER_BOOTFLAG`
- `CONFIG_RAW_LIVEVIEW`
- `CONFIG_RAW_PHOTO`
- `CONFIG_EDMAC_MEMCPY`
- `CONFIG_FRAME_ISO_OVERRIDE`
- `CONFIG_FRAME_SHUTTER_OVERRIDE`
- `CONFIG_DIGIC_POKE`

Also do not:

- add installer FIR files;
- enable modules;
- add persistent property writes;
- add arbitrary hardware pokes;
- remove the intentional 2000D build guards.

CI enforces the current policy through:

`tools/eos2000d/port_policy.py`

---

## QEMU rules

Supported emulator baseline:

`reticulatedpines/qemu-eos` branch `qemu-eos-v4.2.1`

Use:

`tools/eos2000d/qemu_eos_patch.py`

for the provisional 2000D model.

The QEMU model contains provisional values derived from the 1300D model and historical 2000D.110 evidence. Those values are **emulator bring-up assumptions only**.

For firmware 1.1.0, use the ROM1-only profile: `firmware=110` sets `rom0_size=0`, ROM1 at `0xF8000000` with size `0x02000000`, and main entry `0xFE0C0000`. Keep ROM0 out of the workdir. `start=main` is an explicitly labeled reset-bypass experiment, never evidence that the camera's reset path works. Record execution traces before adding smoke markers or changing model parameters. The optional `vectors=low` flag is a bootloader-state experiment guarded by firmware 110 and direct entry; it clears SCTLR.V after the trace-proven high-vector IRQ failure. It does not verify hardware reset. Private `qemu_probe.py` reports now prove the RAM copy and ordered init-task-entry markers; the flash-identification assertion remains a blocker to full boot. Keep raw traces/memory out of Git. The optional `--flashif-trace` debugger mode captures the canonical 06/9F/05 transaction and must match every FlashIF I/O log entry. Check ARM conditions before counting accesses. RAM 27C4 returns status zero; manufacturer six is a caller-loaded output from the unmodeled serial command/data window. Three accepted ID tuples are alternatives, not proof of the installed chip. Do not install an accepted ID as verified hardware or as a default without independent identity evidence. The user-authorized `flash-id=c22539` exception is a narrowly scoped hypothetical QEMU experiment for 2000D firmware 110 only; all post-ID behavior is QEMU + Experiment. Its 2938 initializer and later task startup do not prove physical identity, full boot, MPU handshake or GUI. The repeatable FE2BA330 PowerMgr wait is not established as a fatal blocker. Keep KI-019 open. Preserve disabled defaults, strict option validation, protocol state independent of PCs, ROM backing bytes, full trace equality and safety gates. See `docs/2000D-110/flashif.md`.

Do not copy QEMU-only assumptions into physical-camera platform files without independent firmware evidence.

QEMU builds using `CONFIG_QEMU=y` must never be tested on the physical camera.

---

## Physical-camera rules

Do not test a build on hardware until exact-target evidence and recovery gates
are satisfied. The existing 1.3.0 protocol below remains a future-port record;
it does not authorize or define a 1.1.0 procedure:

`docs/2000D-130/hardware-test-protocol.md`

A 1.1.0 procedure requires a separately validated diagnostic, loader, memory
reservation, exact non-QEMU binary and recovery evidence after issue #45.
Do not operate the camera, alter boot flags or persistent state, prepare an
installer FIR or instruct experimental payload execution during offline work.

For the separate 1.3.0 protocol, first hardware execution requires:

- exact camera model confirmed;
- camera firmware exactly 1.3.0;
- canonical ROM hash known;
- verified loader / minimal stubs;
- passing QEMU execution;
- passing QEMU smoke test;
- verified early diagnostic;
- exact non-QEMU `autoexec.bin` SHA-256;
- rescue card prepared;
- fully charged battery;
- explicit abort threshold.

Never treat "it boots on a related camera" as sufficient evidence.

---

## Development workflow

Use normal GitHub review flow.

1. Start from current `dev`.
2. Create a focused branch.
3. Make the smallest logically complete change.
4. Update code **and** the documentation/evidence that justifies it in the same PR.
5. Run/inspect CI.
6. Do not merge without a separate explicit user instruction; green checks alone are insufficient.
7. Close a GitHub issue only when its actual acceptance criteria are met.

Do not close an issue simply because scaffolding exists.

When work is blocked, leave the issue open and document:

- exact blocker;
- evidence missing;
- possible next steps;
- exit criterion.

---

## Core commands

### Safe 2000D structural check

```bash
make -C platform/2000D.130 preflight
```

A normal 2000D build is currently expected to fail on intentionally unset verified firmware values.

### Reference full build

```bash
make -C platform/1100D.105 clean
make -C platform/1100D.105 FATAL_WARNINGS=y -j2
```

### Reference minimal build

```bash
make -C minimal/hello-world clean MODEL=1100D
make -C minimal/hello-world MODEL=1100D FATAL_WARNINGS=y -j2
```

### ROM tooling tests

```bash
python3 -m unittest tools.eos2000d.test_rom_manifest
```

### QEMU scaffolding tests

```bash
python3 -m unittest tools.eos2000d.test_qemu_phase3
```

### Later-phase preparation tests

```bash
python3 -m unittest tools.eos2000d.test_phase4_7_prep
```

### Stub evidence guard

```bash
python3 tools/eos2000d/stub_evidence.py \
  --stubs platform/2000D.130/stubs.S \
  --evidence docs/2000D-130/stub-evidence.json
```

### Feature evidence guard

```bash
python3 tools/eos2000d/feature_matrix.py \
  --features platform/2000D.130/features.h \
  --modules platform/2000D.130/modules.included \
  --matrix docs/2000D-130/feature-matrix.json
```

### Current pre-ROM safety policy

```bash
python3 tools/eos2000d/port_policy.py --root . --mode pre-rom
```

---

## When the 1.3.0 ROM becomes available

Do not immediately start adding addresses.

Use this order:

1. Hash the source artifact and raw analysis image.
2. Update `docs/2000D-130/rom-manifest.json`.
3. Verify model/version evidence.
4. Confirm ROM bank/base/alias mapping.
5. Verify startup entry and cache-hack path.
6. Verify RAM/BSS/allocator boundaries.
7. Determine task/task_attr layouts.
8. Identify only the minimum stubs required for the first payload.
9. Update evidence records.
10. Build for QEMU first.
11. Obtain a repeatable Canon → ML → Canon trace.
12. Freeze smoke markers.
13. Only then prepare the exact hardware binary/test record.

---

## Definition of a useful first executable milestone

The first success is **not** "Magic Lantern menu appears."

The preferred milestone is:

```text
Canon firmware starts
→ ML loader/cache patch executes
→ minimal diagnostic payload executes
→ Canon init task continues
→ Canon firmware remains operational
```

Prove this in QEMU before physical hardware.

---

## Known Issues document

A separate Google Doc tracks detailed blockers and possible solutions.

Repository agents should also keep GitHub issue comments current so important engineering state is not available only in an external document.

If a new blocker is discovered:

1. document it in the relevant repository Markdown file;
2. add a concise update to the affected GitHub issue;
3. add it to the external Known Issues tab when the working environment has access to that document.

---

## Final agent checklist

Before handing off work, confirm:

- no guessed firmware address was activated;
- no Canon firmware bytes were committed;
- no physical-camera test was implied without the required gates;
- docs/evidence changed alongside code when needed;
- feature/module/stub guards still pass;
- reference build still passes;
- issue status matches reality;
- new blockers are documented;
- README / porting docs reflect any major phase-state change.

## Firmware-110 post-startup evidence boundary

Read `docs/2000D-110/post-startup.md` before extending the experimental task
observer. Canonical creation/dispatch/store evidence now qualifies limited
TCB observation fields and current-task slot 31170 for 1.1.0 analysis; no
physical structure variant or 1.3.0 stub is selected. PowerMgr repeatedly
wakes; do not bypass its WFI or HotPlug's timed flag wait. The first unserved
Intercom request is a separate initial-state/handshake limitation; do not
inject a reply, event or guessed request-line state to call it fixed.
Keep all raw captures private, all downstream results QEMU + Experiment,
KI-019 open, and the physical camera/card and active 1.3.0 platform untouched.
