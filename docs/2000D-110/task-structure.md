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
