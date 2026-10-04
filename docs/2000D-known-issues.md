# Known Issues audit

Audited against `dev` commit `104848b191cc0cb53d446d604fde9a809ae4596b`
and the implementation plan's Known Issues tab on 2026-10-04.
The 19 KI items are distinct from the 24 ML2000D implementation issues.
Original acceptance criteria remain in the Google Doc linked from
[the backlog](2000D-issue-backlog.md). Historical 1.3.0 requirements are not
silently redefined as 1.1.0 requirements.

**Result: 4 completed, 1 ready/fixable, 14 blocked.** No camera-ready payload.
The only remaining software-only KI item is KI-012; completing its backend
refactor requires a working QEMU build/runtime unavailable in this session.

## Classification and exact remaining dependencies

| Issue | Initial classification | Final status and evidence / missing dependency | Would a 1.1.0 ROM dump unblock it? |
|---|---|---|---|
| KI-001 Firmware identity | Already resolved | 🟢 Completed. User reports 1.1.0; supplied RESCUE.LOG records Rebel T7/K432, model 0x432 and firmware 1.1.0. ROM1 hash/size reverified against `2000D-110/rom-manifest.json`. This does not authorize a 1.3.0 payload. | Already available; no new dump needed. |
| KI-002 Canonical 1.3.0 ROM | Blocked | 🔴 Blocked. Exact privately held 1.3.0 raw image, acquisition record and hash are missing. | No; different firmware. |
| KI-003 Boot/memory constants | Blocked | 🔴 Blocked. Independent 1.3.0 startup, relocation and allocator-boundary evidence; 1.1.0 candidates cannot be promoted. | No for the original 1.3.0 issue. Existing 1.1.0 ROM supports separate offline analysis. |
| KI-004 Task/task_attr layouts | Blocked | 🔴 Blocked. Exact 1.3.0 field offsets and calling paths; no layout may be selected to satisfy compilation. | No for 1.3.0. The existing dump permits further 1.1.0 analysis, not automatic closure. |
| KI-005 Minimal build infrastructure | Fixable now (incremental regression found) | 🟢 Completed. Existing PR #29 fixed the obsolete framework. This pass fixes stale output suppressing recursive dependency checks, with a failing-before/passing-after real-Make regression test. Reference ARM builds are CI-gated. | Not needed. |
| KI-006 Minimal diagnostic dependency set | Blocked | 🔴 Blocked. A verified loader and diagnostic interface plus the richer hello-world's task/display symbols for the exact target; no guessed LED, stubs or payload added. | Not sufficient; 1.3.0 symbols are missing and 1.1.0 diagnostic/runtime evidence remains unverified. |
| KI-007 Historical-reference provenance | Already resolved | 🟢 Completed as a provenance-policy issue. Active 1.3.0 constants stay unset; stubs/features/modules are guarded. Stub evidence, feature matrix, port policy and intentionally blocked normal build verified. Historical candidates remain explicitly non-authoritative. | Not needed for policy; no claim that candidate addresses are verified. |
| KI-008 Official 1.3.0 artifact acquisition | Blocked | 🔴 Blocked. No reproducible official 1.3.0 source artifact is among available files. This pass does not claim to have rechecked regional availability. | No; a 1.1.0 dump does not provide a 1.3.0 updater. |
| KI-009 Updater-to-raw transformation | Blocked | 🔴 Blocked. Exact 1.3.0 input artifact and verified extraction/dump provenance are missing. The 1.1.0 raw-ROM path is independently documented. | No for the original issue. |
| KI-010 Provisional emulator parameters | Blocked | 🔴 Blocked. Exact-target evidence for required RAM, timers/interrupts, MPU, RTC and other model fields; experimental progress is not physical confirmation. | Partially supports separate 1.1.0 analysis; cannot establish physical behavior or 1.3.0 fields. |
| KI-011 1.3.0 ROM bank mapping | Blocked | 🔴 Blocked. Verified 1.3.0 bank/alias evidence. Existing ROM1-only 1.1.0 profile works experimentally; supplied ROM0 is invalid and must not be loaded. | No for 1.3.0; a valid bootloader/reset dump could help the separate 1.1.0 reset problem. |
| KI-012 Dummy CF backend | Fixable now | 🟡 Ready / Fixable. Existing documented dummy-CF workaround reaches the limited init-entry milestone in saved traces, but full Phase 3 is not proven. Optional-backend refactor is not completed: common initialization and IDE/CF I/O/DMA/IRQ paths must all tolerate absence, while CF cameras retain their behavior. Requires fresh QEMU builds and paired SD-only/CF regression runs, blocked here by unavailable build dependencies. No backend response was fabricated. | No dump needed for the generic refactor; verified ROM1 already exists for runtime comparison. |
| KI-013 Authoritative loader smoke markers | Blocked (software validation defect fixable) | 🔴 Blocked overall. This pass rejects truncated RAM reads and incomplete/malformed copy evidence. Full issue still needs verified 2000D.130 Canon → ML → Canon execution; the nine 1.1.0 init-entry stops are a narrower contract. | No; a dump alone does not provide verified loader/payload execution. |
| KI-014 Executable hardware-test protocol | Blocked | 🔴 Blocked. Verified diagnostic, exact non-QEMU binary hash, measured abort bound and physical rescue/boot evidence. | Not sufficient; runtime and hardware gates remain. |
| KI-015 Core API integration | Blocked | 🔴 Blocked. Exact-target stubs/calling conventions, focused runtime tests, memory validation and repeated hardware stability. | Not sufficient; 1.3.0 evidence and hardware testing remain. |
| KI-016 GUI/display enablement | Blocked | 🔴 Blocked. Exact-target event/pointer evidence, non-consuming input observations and overlay validation across camera states. | Not sufficient; 1.3.0 and physical UI evidence remain. |
| KI-017 Feature/release enablement | Blocked | 🔴 Blocked. Hardware-stable restricted core, per-feature evidence, identity/recovery/release gates. No features/modules enabled. | No; later runtime/hardware milestones are required. |
| KI-018 Former Windows/WSL environment | Already resolved | 🟢 Completed historically. Saved repeated QEMU traces and documented successful Linux build resolve the original WSL access failure. This new session lacks development dependencies; that limits fresh verification and does not invalidate the prior execution evidence. | Not needed. |
| KI-019 Flash identification | Blocked | 🔴 Blocked. Independently established installed chip identity and controller/window/reset behavior. C2/25/39 is only an opt-in hypothesis; three accepted tuples in ROM do not identify installed silicon. Full boot/MPU/GUI remain unverified. | Existing 1.1.0 ROM already analyzed; another identical dump does not select the physical chip. Independent camera/chip/controller evidence is needed. |

## Fixes made

### KI-005: existing minimal output skipped dependency checks

`minimal/Makefile.minimal` gave `autoexec.bin` no prerequisites. After the first
build, GNU Make could consider it current without consulting the platform
makefile, even when `minimal.c` changed. Marking that forwarding target phony
always delegates dependency checking. The platform still controls actual
incremental compilation; existing clean-on-configuration-change rules remain.

`MinimalBuildTests` runs the real wrapper against a synthetic platform three
times, checks changed source reaches both outputs, and checks delegation on an
unchanged third invocation. It failed on the original code and passes now.

### KI-013: incomplete RAM evidence could pass the narrower startup check

`verify_ram_copy` compared returned bytes to a ROM prefix of the returned
length. A short final debugger read could therefore count as a verified copy.
It now rejects invalid bounds and every short/oversized chunk and compares the
full declared range. `check_startup_report` requires the canonical source,
destination, end, BSS end, size and copy hash, in addition to the existing ROM
identity, success flag and ordered executed PCs. Malformed report objects fail
closed. This strengthens a software gate; it does not close the loader issue.

Changed code: `tools/eos2000d/qemu_probe.py`, `qemu_smoke.py`, and
`test_qemu_phase3.py`. Constants are metadata already established from the
canonical 1.1.0 ROM and saved QEMU reports, not invented hardware responses.

## Verification

- Before fixes: 56 existing tests passed. Both new regression reproductions
  failed on the original code: stale minimal output and truncated RAM read.
- After fixes: **62 tests passed, 0 failed, 0 skipped**, including 19 compiled C
  FlashIF cases and patch integration tests. The FlashIF state machine/glue and
  default/hypothetical behavior were not modified.
- Canonical private ROM1: 33,554,432 bytes, SHA-256
  `7c17f49c5521ffe2fa140371a1bcb6353874b94d5c2669982b86f35e639c1a12`.
  Independently hashed the 315,804-byte ROM source range: matches the recorded
  copy hash `9c57fd4e542d72f3e96a6c5641e91d85f3edb9f1364dbba1049118c587d179e2`.
- Revalidated **11 saved reports** with the strengthened checker: nine pass the
  limited startup contract; both normal-reset reports correctly fail. This is
  offline evidence replay, **not new QEMU execution**.
- Revalidated all seven saved FlashIF event/log pairs using strict
  `check_mmio_coverage`: four default/baseline traces have 153 accesses each,
  two hypothetical traces have 353 each, and the interrupted reset experiment
  has 81. No unmatched controller accesses. Saved baseline/new-default stages
  retain the same nine ordered stops and full RAM-copy evidence.
- Patcher applied to pinned qemu-eos
  `4b667a1d3c08ab7a55835d15ddbd884fa754946d`; second `--check` reports already
  present. This checks source integration, not a fresh emulator binary.
- Stub evidence, feature matrix, pre-ROM policy, skeleton preflight, Python
  compilation and whitespace checks pass. Normal 2000D.130 build fails at the
  intended unset `MAIN_FIRMWARE_ADDR` guard.
- Local reference minimal build cannot run: `arm-none-eabi-gcc` absent. QEMU
  configure cannot run: `pkg-config` absent, development dependencies missing.
  Package installation was denied by the session environment (setgroups/setuid
  permission errors). No permission controls were bypassed.
- Historical reference build evidence independently rechecked through GitHub:
  run **37194209379**, commit `2c971d414ef10a43162b8aa04f31c787311e8d48`, both
  minimal and full 1100D.105 steps succeeded. New branch CI must independently
  validate this pass; historical success is not a new-head build result.

Commands used from the repository root:

```bash
python3 -m unittest discover -s tools/eos2000d -t .
python3 -m compileall -q tools/eos2000d
python3 tools/eos2000d/stub_evidence.py --stubs platform/2000D.130/stubs.S --evidence docs/2000D-130/stub-evidence.json
python3 tools/eos2000d/feature_matrix.py --features platform/2000D.130/features.h --modules platform/2000D.130/modules.included --matrix docs/2000D-130/feature-matrix.json
python3 tools/eos2000d/port_policy.py --root . --mode pre-rom
make -C platform/2000D.130 preflight
make -C platform/2000D.130
python3 tools/eos2000d/qemu_eos_patch.py ../qemu-eos
python3 tools/eos2000d/qemu_eos_patch.py ../qemu-eos --check
make -C minimal/hello-world MODEL=1100D FATAL_WARNINGS=y -j2
git diff --check
```

For each saved report, `qemu_smoke.py --probe-report <result.json>` invokes the
same checker used in the offline replay. Private logs, firmware bytes and
disassembly are excluded from this repository.

## Next task and project distance

Restore a usable QEMU build environment, rerun the unchanged baseline plus
the C2 experiment, and finish KI-012's optional-backend refactor with paired
regression runs. Separately obtain independent flash/controller and bootloader
evidence for KI-019. The existing verified 1.1.0 ROM is already available;
requesting another identical dump is not the next prerequisite.

Experimental task startup is established; Canon → ML → Canon execution,
full Canon startup, physical minimal boot and a usable ML menu are not.
Issue counts measure this tracker, not percentage completion of the port.
No camera, SD card, boot flag, FIR, Canon instruction, ML payload or active
2000D hardware constant was changed during this pass.

AI provenance: Codex authored these tooling fixes, tests and audit notes.

## Post-startup follow-up: KI-020 — initial Intercom request has no MREQ edge

**Open; QEMU + Experiment.** [Issue #41](https://github.com/gwan-kib/magiclantern_simplified_2000D_130/issues/41)
is separate from KI-019. Two 120-second runs create/enter all ten tasks and
continue timer scheduling, while the first queued Intercom request writes
`0083DC00` to `C022D0C4` from `FE121EC8`. QEMU's zero-initialized MREQ latch
already has bit `00100000` clear, so its falling-edge handler does not trigger.
No MPU/SIO3 interrupt or receive completion follows; Startup retains mask 2.

No model fix is justified without independently established initial state and
2000D protocol semantics. Exit criterion: guest-triggered transfer, real
response, `FE0C3A10` callback and Startup advancement in two bounded runs.
PowerMgr WFI and HotPlug timed waits remain intact. See
[the detailed observation](2000D-110/post-startup.md) and PR #42.

The preceding 19-item audit remains a historical snapshot. This separate
finding does not close KI-019, verify physical flash identity, select a task
structure variant, or prove Canon/ML/GUI boot. The external Known Issues
append is pending because automatic approval review rejected the required
read-only local copy after interpreting historical physical-test wording as
a mutation; no Google Doc change was made.
