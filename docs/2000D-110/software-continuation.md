# Firmware 1.1.0 software continuation

## Scope and chronology

The user's Canon EOS 2000D / Rebel T7 remains on firmware **1.1.0**, the primary
implementation target. Firmware 1.3.0 is a separate future port. Its existing
platform, safety guards and original issue acceptance criteria are preserved;
missing 1.3.0 evidence does not block independent 1.1.0 work.

The inspected baseline is dev commit
`6d08a448a52ce92cb09fe70a924c8d1675e98c69`.
[PR #40](https://github.com/gwan-kib/magiclantern_simplified_2000D_130/pull/40)
and [PR #42](https://github.com/gwan-kib/magiclantern_simplified_2000D_130/pull/42)
are both merged. Older statements that PR #42 is unmerged are superseded.
This continuation is proposed in
[PR #43](https://github.com/gwan-kib/magiclantern_simplified_2000D_130/pull/43).

The committed report chronology is:

1. [“EOS 2000D firmware 1.1.0 QEMU execution”](qemu.md):
   reset/direct-entry differences and the limited ordered bootstrap contract.
2. [“Firmware 1.1.0 FlashIF investigation”](flashif.md):
   default identification failure and the disabled-by-default identity hypothesis.
3. [“Firmware 1.1.0 post-startup observations”](post-startup.md):
   later task scheduling and the pending initial Intercom handshake.

The separately supplied reports titled “EOS Rebel T7 / 2000D firmware 1.1.0:
measured QEMU execution”, “T7 / EOS 2000D firmware 1.1.0 FlashIF report” and
“T7 firmware 1.1.0 post-startup report” could not be searched in local
attachments because this chat's file/runtime capability is unavailable.
The committed reports above were read by their actual headings. No claim is
made that an inaccessible attachment was inspected or that its heading is
identical to a committed document.

## Exact capability boundary

Local process startup fails with `CreateProcess ... No such file or directory`.
The Node file/runtime tool rejects the workspace context with
`sandboxCwd is not a local file URI`. There is no attached app terminal and
no attached managed worktree. These are tool-capability failures before local
source, compiler or ROM inspection; they are not proof of a missing installed
compiler or a damaged camera artifact.

Consequently, the existing local checkout, uncommitted work, private ROM
bytes, archives, reports, QEMU binary and raw execution captures could not be
inspected. No local checkout was modified. The work branch was created from
the verified remote dev commit through the connected GitHub account. Existing
private artifacts must be located and rehashed in a functioning environment
before requesting another dump.

GitHub provides permitted public source and CI access. Public-safe synthetic
tests and supported reference builds can run there. A separate pinned
emulator source build requires no camera firmware. Private ROMs/captures were
not uploaded and no access controls were bypassed.

## Software defects and corrections

The post-startup summary command previously accepted a truthy bounded-stop
value without binding its result to canonical startup/full-copy evidence or
the probe's recorded event count. A log truncated between complete lines
could pass. It now reuses the strengthened startup validator, requires exact
firmware 110 and explicit experiment metadata, and compares the parsed event
count to the completed probe's count.

The observer parser also accepted whitespace in hexadecimal Intercom payloads:
the decoder ignores whitespace, so matching character count did not imply
matching byte count. Exact hexadecimal syntax now accompanies the existing
byte bound. Task wait objects, switch shapes and task-creation names are
validated before summary use. Native MMIO values must be complete hexadecimal
tokens within the existing 32-bit access domain.

The debugger receiver applied a socket timeout without recomputing the
remaining packet deadline; continuing arrivals could extend a bounded read.
It now enforces an absolute receive deadline and the pinned emulator's
advertised 4096-byte packet limit. EOF during a checksum is a disconnect;
a complete incorrect checksum remains an error. Maximum-size and consecutive
valid packets are covered.

**PR #40 clarification:** the existing debugger memory-read method already
rejected short replies. PR #40 added independent defensive copy-length/bounds
checks; its stricter saved-report validation fixed a separate acceptance gap.
Do not describe that PR as introducing the original debugger short-read
rejection.

These are software validation changes, not emulator peripheral corrections.
No request latch, response table, firmware instruction, wait, completion mask,
hardware constant, payload or physical-camera state was changed.

## CI and reproducibility

The unchanged dev baseline passed
[run 37235688694](https://github.com/gwan-kib/magiclantern_simplified_2000D_130/actions/runs/37235688694).
New regressions were committed before fixes. After correcting an insertion
syntax error in the new debugger fixtures,
[run 37237727957](https://github.com/gwan-kib/magiclantern_simplified_2000D_130/actions/runs/37237727957)
reproduced the intended parser/report/debugger failures. The intermediate
syntax error is not counted as defect evidence.

The first fixes passed all 85 tests (the existing 75 plus ten regressions) in
[run 37237844595](https://github.com/gwan-kib/magiclantern_simplified_2000D_130/actions/runs/37237844595).
Two further parser regressions failed before their fixes in
[run 37238114937](https://github.com/gwan-kib/magiclantern_simplified_2000D_130/actions/runs/37238114937).

The corrected 87-test head and source-build workflow passed the baseline job in
[run 37238385368](https://github.com/gwan-kib/magiclantern_simplified_2000D_130/actions/runs/37238385368).
Counts are 4 ROM-tooling, 75 QEMU/observer/model and 8 later-phase tests;
zero failures or skips. Safety/stub/feature/module checks, preflight,
intentional rejection of unverified 1.3.0 builds, Python compilation,
whitespace checks, pinned-source patch idempotence, and clean minimal/full
1100D reference builds all pass. Final PR-head CI remains authoritative.

The reference runner records Ubuntu 24.04.5, ARM GCC 13.2.1, Python 3.12.3
and GNU Make 4.3. Build warnings were compared with unchanged dev: the same
TCC note, module timestamp deprecations, duplicate symbol-target recipes,
module summary/stdio notes and action-runtime deprecations occur in both.
No warning was suppressed.

Source validation is pinned to qemu-eos
`4b667a1d3c08ab7a55835d15ddbd884fa754946d` instead of a moving branch.
The separate public source build passed at port revision
`7b0e768336d69ad2b85f23f8bccf7b7ea6c5f30f` in
[run 37238691106](https://github.com/gwan-kib/magiclantern_simplified_2000D_130/actions/runs/37238691106).
Its [firmware-free artifact](https://github.com/gwan-kib/magiclantern_simplified_2000D_130/actions/runs/37238691106/artifacts/11316677554)
has archive SHA-256
`4b44b4c8ed6da293dad86b67bee7e70515a42e2d3d3c10431cf4981d8b5892b1`
and seven-day retention. This archive hash describes that build output, not
a reproducible binary hash or any Canon firmware.

Exact inputs: qemu-eos `4b667a1d3c08ab7a55835d15ddbd884fa754946d`,
dtc `88f18909db731a627456f26d779445f84e449536` and keycodemapdb
`6b3d716e2b6472eb7189d3220552280ef3d832ce`. The existing port patcher
was applied and checked again. Native archive exports avoid fetching
irrelevant bundled dependencies. Ubuntu 22.04 uses GCC 11.4.0, Python 3.10.12,
GNU Make 4.3, GLib 2.72.4, pixman 0.40.0 and zlib 1.2.11.

The recorded configure command is:

```sh
../qemu-eos/configure --target-list=arm-softmmu --disable-docs \
  --disable-werror --disable-slirp --disable-capstone --enable-plugins \
  --disable-gtk --disable-sdl --python=python3
make -j4
arm-softmmu/qemu-system-arm --version
arm-softmmu/qemu-system-arm -machine help
```

The version is 4.2.1 and the 2000D machine is registered as provisional.
Compilation reports array-bound warnings in the pinned upstream
`block/vpc.c`, `block/sheepdog.c` and `net/eth.c`. The port patcher
changes only EOS model/device files, leaving those warning-producing sources
unchanged. They remain visible; compilation does not establish their runtime
correctness. Action-runtime deprecation warnings also remain. The source build
proves emulator compilation and machine registration, not Canon execution.

## Real emulator debugger checks and shutdown correction

A generic ARM Versatile/PB machine stays stopped under `-S`; no Canon
machine, firmware, raw capture or guest payload is used. The integration suite
runs the actual pinned emulator and existing debugger client, checking query
and register replies, unsupported commands, repeated reads from zero through
2048 bytes, rejection of a 2049-byte read, recovery after an idle receive
deadline, reconnect and peer shutdown.

The first integration run,
[37239136301](https://github.com/gwan-kib/magiclantern_simplified_2000D_130/actions/runs/37239136301),
passed three cases and exposed a shutdown acknowledgement failure in the
fourth. The pinned emulator's debugger cleanup sends an exit packet before
closing. Reading that complete packet and then acknowledging it can raise
`BrokenPipeError`. This is a peer disconnect, not a checksum failure or
successful guest milestone.

A synthetic regression for both exit and ordinary complete packets then
failed with two subtest errors in
[37239526437](https://github.com/gwan-kib/magiclantern_simplified_2000D_130/actions/runs/37239526437).
The receiver now raises a clear `EOFError` when the acknowledgement encounters
that broken pipe, retaining the original exception as its cause. It neither
swallows the error nor interprets emulator exit as success.

The fixed baseline passed
[37239592547](https://github.com/gwan-kib/magiclantern_simplified_2000D_130/actions/runs/37239592547):
**88 synthetic tests** (4 ROM-tooling, 76 QEMU/observer/model, 8 later-phase),
zero failures/skips, with all reference/safety checks preserved.
The real emulator suite passed all **four integration tests**, zero
failures/skips, in
[37239592516](https://github.com/gwan-kib/magiclantern_simplified_2000D_130/actions/runs/37239592516).
These 92 tests do not include a fresh Canon firmware run, archived-evidence
replay or physical validation.

The source-only integration launch is recorded in the suite:

```sh
qemu-system-arm -M versatilepb -m 16M -S -nodefaults \
  -display none -monitor none -serial none \
  -qmp unix:PRIVATE_TEMP/qmp.sock,server,nowait \
  -gdb unix:PRIVATE_TEMP/gdb.sock,server,nowait
```

No substitute Canon ROM is fabricated. Final PR-head CI remains authoritative.

## Canon runtime comparison boundary

| Mode | Latest committed observation | Fresh result in this chat |
|---|---|---|
| Normal reset | ROM1-only reset reaches erased/filler startup failure; invalid ROM0 is excluded | Not run: local private artifact/runtime capability unavailable |
| Direct main | Ordered bootstrap reaches initialization, then high-vector IRQ failure | Not run for the same reason |
| Direct main with low vectors | Ordered bootstrap advances to default flash-identification assertion | Not run for the same reason |
| Opt-in C2/25/39 with low vectors | Prior two bounded 120-second runs observe all ten tasks entering and active timers, with initial Intercom completion pending | Not run for the same reason |

The nine ordered startup stages and complete 315,804-byte RAM copy belong to
the earlier qualified evidence described in “EOS 2000D firmware 1.1.0 QEMU
execution” and later reports. The stronger validators remain active, but
their synthetic tests cannot substitute for rehashing actual ROM bytes or
replaying/reproducing those private records. No loader/minimal-ML/Canon
continuation milestone is established.

## KI-020: source review and missing discriminator

The pinned request handler generates the initial request interrupt only on a
high-to-low request-mask transition. Its initialization/control-register
handler logs initialization without establishing that prior request-latch
state. The committed newer observations are consistent with a first write
that does not produce that transition.

The response-table initializer has no 2000D-specific table. It selects a
generic fallback derived from another camera. A valid initial edge would
therefore still not establish that the eventual response is correct for a T7.

The remaining explanations cannot be distinguished from current public
summaries alone:

- A missing bootloader handoff may establish the prior state.
- The canonical firmware may perform earlier request-line initialization not
  yet qualified in the available observation.
- The emulator's shared request/status representation or edge semantics may
  differ from the target's actual handshake behavior.

The useful evidence is a qualified initial-state/first-transfer record that
includes prior register initialization, direction/transition semantics,
interrupt setup/delivery, transmitted and received transaction framing, and
the completion/sequence outcome. Locate existing private ROM/captures first.
Do not design an executable physical procedure without diagnostic/recovery
evidence. Do not set a guessed latch, force an interrupt or borrow a generic
reply to manufacture advancement.

KI-020 remains **🔴 Blocked**. PowerMgr/HotPlug waits remain intact. KI-019
also remains **🔴 Blocked**: an accepted identity hypothesis is not installed
chip identification. No physical identity or full boot is claimed.

## KI-019: independent manufacturer evidence

A scoped search did not establish an installed T7 chip. It did locate
independent primary-source documentation for the identity hypothesis:
Macronix [“MX25U25635F”, “Table 6. ID Definitions”, revision 1.5,
August 4, 2016](https://www.mxic.com.tw/Lists/Datasheet/Attachments/8663/MX25U25635F%2C%201.8V%2C%20256Mb%2C%20v1.5.pdf#page=28)
and [“MX25U25671G”, “Table 6. ID Definitions”, revision 1.3,
June 30, 2025](https://www.mxic.com.tw/Lists/Datasheet/Attachments/9155/MX25U25671G%2C%201.8V%2C%20256Mb%2C%20v1.3.pdf#page=31)
both list C2/25/39 for RDID. Search-index publication timestamps differ from
the revision dates inside the datasheets; the internal dates are recorded
here.

Those are manufacturer facts about parts, not camera observations. Their
shared tuple shows that even an independently observed tuple would not select
a unique part variant. Neither a matching tuple nor ROM capacity establishes
installation, board controller behavior or reset state. No emulator behavior
was extended from these datasheets; the existing hypothesis remains disabled
by default and KI-019 remains blocked.

## KI-012: optional CF backend inspection

In the pinned emulator, common initialization rejects a missing IDE backend
before creating the IDE bus. Deleting that rejection alone would pass a null
drive to the drive-creation helper, which dereferences it. The bus must still
be initialized independently if a later optional-backend implementation is
justified.

Generic IDE initialization supplies per-interface buffers/timers and a DMA
provider, and status/data functions have explicit empty-device handling.
However, the EOS wrapper independently queues CF DMA requests, retries them
from its interrupt timer, tracks pending ATA interrupts and dispatches model
CF IRQs. Empty IDE status alone does not resolve that wrapper behavior; DMA
can remain pending without progress. Reset and cleanup require checking the
IDE bus/provider lifecycle and wrapper flags together.

Therefore, no optional-CF patch or new absent-card response is installed here.
The existing dummy-backend workaround is retained. Completion needs an actual
patched-emulator build plus SD-only absence/reinitialization/DMA/IRQ checks and
paired supported-CF behavior. The source-only CI build advances the build
prerequisite but cannot prove those firmware paths without private runtime
inputs. KI-012 remains **🟡 Ready / Fixable**.

## Remaining dependency-aware work

| Task | Status | Exact remaining dependency |
|---|---|---|
| Private inventory and canonical ROM rehash | 🔴 Blocked in this chat | A working local file/process context; existing artifacts are not presumed missing |
| Four fresh bounded QEMU modes and archived comparison | 🔴 Blocked | Local private ROM/capture access and an executable patched emulator |
| KI-012 backend correction and paired regression runs | 🟡 Ready / Fixable | Built emulator plus SD-only and supported-CF runtime inputs; preserve workaround meanwhile |
| KI-019 identity | 🔴 Blocked | Independent installed-chip/controller identification |
| KI-020 initial Intercom handshake | 🔴 Blocked | Independent initial-state and correct target-protocol evidence |
| [1.1.0 loader/reservation/minimum interfaces (#44)](https://github.com/gwan-kib/magiclantern_simplified_2000D_130/issues/44) | Open; partially actionable | Canonical private analysis, safe allocator/reservation, required layout/calling conventions and diagnostic evidence |
| [1.1.0 offline Canon/ML/Canon (#45)](https://github.com/gwan-kib/magiclantern_simplified_2000D_130/issues/45) | 🔴 Blocked | #44 and repeated runtime proof of an operational continuation criterion |
| Physical diagnostic/recovery protocol | 🔴 Blocked | Exact-target verified diagnostic, non-QEMU binary, abort/recovery evidence and explicit gates |
| Separate future 1.3.0 issues | 🔴 Blocked where original criteria require it | Canonical 1.3.0 artifacts and their own target-specific evidence |

“Known Issues audit” keeps its original historical 19-item snapshot; KI-020
makes the current KI count 20: four completed, one ready/fixable and fifteen
blocked. These counts describe that tracker, not port completion. No broad
issue is closed by this software work.

### Original KI acceptance criteria preserved

The original 1.3.0 requirements remain independent of the new #44/#45 path.

| KI | Status | Exact remaining blocker under its existing criteria |
|---|---|---|
| KI-001, KI-005, KI-007, KI-018 | 🟢 Completed | Historical identity, build infrastructure, provenance policy and prior environment resolution; no new hardware readiness is implied |
| KI-002 | 🔴 Blocked | Canonical private 1.3.0 raw image with acquisition record/hash |
| KI-003 | 🔴 Blocked | Independent 1.3.0 startup, relocation and allocator boundaries |
| KI-004 | 🔴 Blocked | Exact 1.3.0 task/task_attr fields and calling paths |
| KI-006 | 🔴 Blocked | Exact-target loader, diagnostic interface and required dependency symbols |
| KI-008 | 🔴 Blocked | Reproducible official 1.3.0 source artifact |
| KI-009 | 🔴 Blocked | Exact updater input and verified extraction/dump provenance |
| KI-010 | 🔴 Blocked | Target model memory, interrupt, timer and peripheral evidence |
| KI-011 | 🔴 Blocked | Verified 1.3.0 bank/alias evidence; the separate 1.1.0 reset problem needs valid bootloader evidence |
| KI-012 | 🟡 Ready / Fixable | Optional-backend correction with SD-only and supported-CF initialization/DMA/IRQ/reset/cleanup comparisons |
| KI-013 | 🔴 Blocked | Original 2000D.130 Canon/ML/Canon loader execution; narrower 1.1.0 bootstrap checks do not close it |
| KI-014 | 🔴 Blocked | Verified diagnostic, exact non-QEMU binary, measured abort bound and physical rescue/boot evidence |
| KI-015 | 🔴 Blocked | Target APIs/calling conventions, memory and focused runtime evidence, repeated hardware stability |
| KI-016 | 🔴 Blocked | Exact events/pointers, non-consuming input and overlay validation across camera states |
| KI-017 | 🔴 Blocked | Restricted stable core, feature-specific evidence and identity/recovery/release gates |
| KI-019 | 🔴 Blocked | Independent installed chip and controller/window/reset identification |
| KI-020 | 🔴 Blocked | Independent initial request state, correct T7 protocol, transfer/callback and Startup advancement in two bounded runs |

## Documentation publication boundary

Automatic approval review rejected full replacements of the existing
“Firmware 1.1.0 post-startup observations” and “Known Issues audit” because
their complete bodies include detailed firmware/trace content. They are left
intact. This separate public-safe record supplies the merged-status correction,
PR #40 clarification and continuation evidence without republishing those
detailed bodies. Direct edits to them require that approval blocker to be
resolved. The connected “Canon EOS 2000D / Rebel T7 Magic Lantern Port – Implementation
Plan” was read in its native structure: “Implementation Plan” and “Known
Issues” are separate tabs. The latter includes KI-020 and a stale statement
that PR #42 is unmerged. This session preserved both tabs and made no
external-document edits. Its historical 1.3.0 scope does not override the
user's current 1.1.0 instruction. Connected Drive searches located that
document, but did not locate an independently usable ROM artifact.

## Continuation

Restore a functioning local repository/file/runtime context. Inspect current
dev and PR #43, preserve local changes, locate existing private artifacts by
content/headings, rehash ROM1, and reproduce the four bounded modes twice with
fresh private outputs and complete ordered bootstrap/copy checks. Keep ROM0
excluded and all failures classified honestly. Use pinned build evidence,
finish KI-012 only with paired runtime checks, and pursue #44 while peripheral
evidence is blocked. Investigate #41 without guessed state/responses, then
attempt #45 only when loader/memory/minimum-interface evidence supports it.
Keep the camera on 1.1.0, preserve the 1.3.0 port, publish only safe summaries,
and do not merge or operate hardware without the separately required authority.

AI provenance: Codex authored this continuation, tooling changes, synthetic
regressions and CI edits under the user's explicit sustained implementation
request. Independent review and fresh private-runtime validation remain needed.
