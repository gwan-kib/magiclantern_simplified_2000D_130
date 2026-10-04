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
The separate source-build job uses the two documented bundled revisions,
native archive exports and the existing patcher, and records configure/build
diagnostics. Its success would prove source compilation, not Canon execution.

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

## Documentation publication boundary

Automatic approval review rejected full replacements of the existing
“Firmware 1.1.0 post-startup observations” and “Known Issues audit” because
their complete bodies include detailed firmware/trace content. They are left
intact. This separate public-safe record supplies the merged-status correction,
PR #40 clarification and continuation evidence without republishing those
detailed bodies. Direct edits to them require that approval blocker to be
resolved. External Known Issues document tabs have not been modified.

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
