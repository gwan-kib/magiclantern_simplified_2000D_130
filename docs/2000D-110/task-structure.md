# EOS 2000D firmware 1.1.0 task structures

**Status: unresolved. No task or task-attribute variant is selected.** A
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
