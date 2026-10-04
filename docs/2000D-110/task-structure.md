# EOS 2000D firmware 1.1.0 task structures

**Status: limited observation fields qualified; no task or task-attribute variant selected.** A
compilable guess would create a risk of corrupting DryOS task state.

| Field or behavior | Status | Evidence still needed |
|---|---|---|
| Entry function | Unresolved | Trace task creation through allocation and task initialization |
| Stack base and size | Unresolved | Identify stack setup, bounds, and alignment |
| Name | Unresolved | Follow name writes and task enumeration/lookup consumers |
| Task ID | Unresolved | Trace ID assignment and lookup use |
| State | Unresolved | Follow scheduler state transitions and dispatch checks |
| Saved context | Unresolved | Identify context frame layout at task switch/restore |
| Linkage/list fields | Unresolved | Trace insertion/removal and traversal |
| CPU-specific fields | Unresolved | Confirm ARM context and any target-specific extension |
| `task_attr` layout | Unresolved | Trace attribute reads at task creation call sites |
| Current-task access | Unresolved | Locate scheduler/current-task accessor and validate against dispatch |

ROM1 `cstart` calls a RAM routine at `0x00005254` consistent with the
historical `create_init_task` name, and contains a pointer to candidate init
task code at `0xFE129718`. These facts identify useful reverse-engineering
targets; they do not establish field offsets or match an existing
`CONFIG_TASK_STRUCT_V*` / `CONFIG_TASK_ATTR_STRUCT_V*` definition.

Before selecting a variant, record ROM1 hash, disassembly context, caller and
callee behavior, and cross-check at least task creation, lookup/enumeration,
dispatch, and current-task access. Then add compile-time size/offset checks
where the project supports them.

## Emulator observation

Repeated direct-entry debugger probes reached RAM `0x5254`, then Canon entry
`0xFE129718` with SP `0x0014B728` and LR `0x00004200`. This demonstrates task
creation/scheduler handoff through initialized RAM code in the emulator. It
does not prove any of the field offsets above; no structure variant is chosen.

## Experimental task-call observations

**QEMU + Experiment:** after hypothetical C2/25/39, RAM 38FC is called with
R0=name, R1=priority, R2=stack-size argument, R3=entry, plus a fifth stack
argument. Repeated calls name PowerMgr, DbgMgr, Startup, TaskMain, PropMgr,
NFCMgr, HotPlug and EventMgr. Actual entry stops confirm Startup FE0D3C94,
TaskMain FE0C12AC, shared manager FE2C1438, PowerMgr FE2BA2F4 and HotPlug
FE0C69DC. These are call/entry observations, not task-field layout evidence.
No CONFIG_TASK_STRUCT or CONFIG_TASK_ATTR variant is selected. In particular,
manager creation does not establish successful property or MPU initialization.

## Canonical creation and scheduler cross-check

**QEMU + Experiment**, firmware 1.1.0 only: the two 120-second runs in
[post-startup.md](post-startup.md) qualify these observation fields against
the canonical bootstrap copy (SHA-256 recorded there). This supersedes the
historical unresolved rows above for these limited observations.

| Field | Offset / address | Canonical and runtime qualification |
|---|---|---|
| Current task | RAM `31170` | Stores at `1980`, `1D28`, `1D94` select R4; observer steps the store and checks the committed pointer |
| Entry / argument | TCB `+0C` / `+10` | Creation descriptor `+04` / `+08`; dispatch loads at `41F4` / `41F8`, branch through `41FC`; observed entry agrees |
| Allocated stack base / size | `+1C` / `+20` | Allocation/setup and descriptor size `+10` cross-checked at completed creation `43D8`; full stack bounds/context frame still unresolved |
| Name pointer | `+24` | Descriptor `+14`; bounded ASCII name qualified only by matching creation fields, not a printable-pointer scan |
| ID | `+40` | Assignment and ID lookup stride `54` (21 words) cross-check |
| State byte / wait kind | `+49` / `+4D` | Wait linkage at `1B34`, wake unlink at `19CC`; observed kind 1 for kernel semaphore and 2 for HotPlug flag |
| Wait object | `+14` | Wait linkage associates each task with its live queue/semaphore/flag object |
| Saved SP | `+50` | Scheduler save/restore use; does not qualify the full saved context structure |

All ten created tasks entered in both runs. Manager names sharing `FE2C1438`
are distinguished by their qualified TCB identities. Stack allocation address
is not automatically the public API's stack-bottom field. Linkage, CPU context,
`task_attr`, physical reset state and structure variant remain unresolved.
No `CONFIG_TASK_STRUCT_V*`, `CONFIG_TASK_ATTR_STRUCT_V*`, active stub or
firmware-1.3.0 value is selected. Follow [post-startup.md](post-startup.md) for
creation callers, task wait objects, IRQ observations and limitations.
