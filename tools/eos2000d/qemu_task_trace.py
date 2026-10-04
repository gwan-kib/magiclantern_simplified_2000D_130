"""Opt-in read-only 2000D.110 observations; every raw capture stays private.

Canonical creation stores, dispatch loads and runtime correlations qualify the
limited fields below. No physical task-structure variant or hardware stub is
selected. Codex-authored under the user's explicit diagnostic-tooling request.
"""
from __future__ import annotations

import struct
import time

CURRENT_SLOT = 0x31170
SWITCH_PCS = frozenset((0x1980, 0x1D28, 0x1D94))
ENTRY_PCS = frozenset((0x7A00, 0xFE129718, 0xFE0D3C94, 0xFE0C12AC,
                       0xFE2C1438, 0xFE2BA2F4, 0xFE0C69DC))
WAIT_PCS = {0x3780: "sleep", 0x75D0: "message-receive", 0x7750: "message-send",
            0x7814: "message-try-send", 0x1B34: "wait-link", 0x19CC: "wake-unlink",
            0x7164: "flag-wait", 0x7328: "flag-set", 0x7370: "flag-clear",
            0x3270: "semaphore-wait", 0x3220: "semaphore-wait-unbounded"}
CONTEXT_PCS = frozenset((0x38FC, 0x43D8, 0x41DC, 0x41F8, 0x4200,
                        0xFE0C08D0, 0xFE0C08F8, 0xFE0D3D1C, 0xFE0D3D64,
                        0xFE2C1480, 0xFE10BC90, 0xFE0D3FF8, 0xFE0D409C,
                        0xFE121ED8, 0xFE0C69F4, 0xFE0C6A7C,
                        0x504, 0x548, 0x588, 0x628, 0xFE0C6C68,
                        0xFE0C8D04, 0xFE0C8DB0, 0xFE2BA314,
                        0xFE0C3A10, 0xFE11F3C8, 0xFE10FBE8, 0xFE10C2AC,
                        0xFE10C6F4, 0xFE10B8F0, 0xFE0C1F9C, 0xFE0C2A1C,
                        0xFE0C2D44, 0xFE0C32F0, 0xFE0C36EC, 0xFE0C3824,
                        0xFE298564, 0xFE10C1DC))
TRACE_PCS = SWITCH_PCS | ENTRY_PCS | set(WAIT_PCS) | CONTEXT_PCS


def u32(memory: bytes, offset=0):
    if offset < 0 or len(memory) < offset + 4:
        raise ValueError("short little-endian word")
    return struct.unpack_from("<I", memory, offset)[0]


def hex32(value):
    return f"0x{value:08X}"


def cstring(debugger, pointer):
    if not (0 < pointer < 0x1000000 or 0xF8000000 <= pointer < 0x100000000):
        return None
    raw = debugger.memory(pointer, 64)
    if b"\0" not in raw:
        return None
    raw = raw.split(b"\0", 1)[0]
    return raw.decode("ascii") if raw and all(32 <= c < 127 for c in raw) else None


def task_snapshot(debugger, pointer):
    if not pointer:
        return {"pointer": hex32(0)}
    if pointer & 3 or not 0x1900 <= pointer <= 0x1000000 - 0x54:
        raise ValueError("task pointer outside aligned low RAM")
    raw = debugger.memory(pointer, 0x54)
    if len(raw) != 0x54:
        raise ValueError("short task record")
    known = getattr(debugger, "observed_tasks", {}).get(pointer)
    fields = {"pointer": hex32(pointer), "name": known["name"] if known else None,
              "name_qualified_by_creation": bool(known),
              "name_pointer": hex32(u32(raw, 0x24)), "entry": hex32(u32(raw, 0xC)),
              "argument": hex32(u32(raw, 0x10)), "stack_base": hex32(u32(raw, 0x1C)),
              "stack_size": u32(raw, 0x20), "object": hex32(u32(raw, 0x14)),
              "id": hex32(u32(raw, 0x40)), "state_byte": raw[0x49],
              "wait_kind_byte": raw[0x4D], "saved_sp": hex32(u32(raw, 0x50)),
              "raw_tcb": raw.hex()}
    if known and any(fields[key] != known[key] for key in ("entry", "name_pointer", "id")):
        raise ValueError("registered task identity changed")
    return fields


def qualify_created(debugger, pointer, descriptor):
    task = task_snapshot(debugger, pointer)
    expected = {"entry": hex32(u32(descriptor, 4)),
                "argument": hex32(u32(descriptor, 8)),
                "stack_size": u32(descriptor, 0x10),
                "name_pointer": hex32(u32(descriptor, 0x14))}
    if any(task[key] != value for key, value in expected.items()):
        raise ValueError("task fields do not match the canonical creation descriptor")
    name = cstring(debugger, u32(descriptor, 0x14))
    if not name:
        raise ValueError("creation descriptor lacks a bounded ASCII task name")
    if not hasattr(debugger, "observed_tasks"):
        debugger.observed_tasks = {}
    debugger.observed_tasks[pointer] = {**task, "name": name}
    return task_snapshot(debugger, pointer)


def current_snapshot(debugger):
    return task_snapshot(debugger, u32(debugger.memory(CURRENT_SLOT, 4)))


def capture(debugger, packet, arm_register, operation="context"):
    registers = [arm_register(packet, i) for i in range(16)]
    pc = registers[15]
    event = {"time_monotonic_ns": time.monotonic_ns(), "pc": hex32(pc),
             "sp": hex32(registers[13]), "lr": hex32(registers[14]),
             "registers": [hex32(r) for r in registers], "operation": operation,
             "current": current_snapshot(debugger)}
    if operation == "sample":
        return event
    event["operation"] = WAIT_PCS.get(pc, operation)
    if pc in SWITCH_PCS:
        event.update(operation="switch", old=event["current"],
                     new=task_snapshot(debugger, registers[4]))
    elif pc in (0x504, 0x548, 0x588, 0x628):
        event["operation"] = {0x504: "irq-reason", 0x548: "irq-handler",
                              0x588: "irq-ack", 0x628: "irq-return"}[pc]
        if pc == 0x548:
            event.update(irq=registers[4] // 4, handler=hex32(registers[1]))
        elif pc == 0x588:
            event["irq"] = registers[4]
    elif pc == 0x43D8:
        descriptor = debugger.memory(registers[5], 24)
        event.update(operation="created-tcb", creation_descriptor=descriptor.hex(),
                     created=qualify_created(debugger, registers[4], descriptor))
    elif pc == 0x38FC:
        event.update(operation="create-call", name=cstring(debugger, registers[0]),
                     fifth_argument=debugger.memory(registers[13], 4).hex())
    elif pc in ENTRY_PCS:
        if event["current"].get("entry") != hex32(pc):
            raise ValueError("task entry stop disagrees with its creation record")
        event["operation"] = "entry"
    elif pc == 0xFE0D3D64:
        event["sequencer"] = debugger.memory(registers[4], 36).hex()
    elif pc == 0xFE0D3D1C:
        event["dispatch_record"] = debugger.memory(registers[0], 12).hex()
    elif pc == 0xFE0D3FF8:
        event.update(operation="sequence-notify", sequencer=debugger.memory(registers[0], 36).hex())
    elif pc == 0xFE0D409C:
        event.update(operation="sequence-mask-updated", sequencer=debugger.memory(registers[4], 36).hex())
    elif pc == 0xFE2C1480:
        event.update(operation="manager-dispatch", manager=debugger.memory(registers[4], 24).hex(),
                     message=debugger.memory(registers[13] + 12, 16).hex())
    elif pc == 0xFE298564:
        size = registers[1]
        if not 0 < size <= 128:
            raise ValueError("invalid bounded Intercom send size")
        event.update(operation="intercom-send", payload=debugger.memory(registers[0], size).hex())
    elif pc == 0xFE10C1DC:
        event.update(operation="intercom-configured", callback_state=debugger.memory(registers[5], 16).hex())
    elif pc == 0xFE11F3C8:
        event.update(operation="debug-call", format_string=cstring(debugger, registers[2]))
    elif pc == 0xFE2BA314:
        event.update(operation="power-mode", power_state=debugger.memory(registers[5], 16).hex())
    elif pc == 0xFE0C6C68:
        event.update(operation="flag-wait-result", return_value=registers[0])
    elif pc == 0xFE10BC90:
        event["operation"] = "property-dispatch"
    elif pc == 0xFE121ED8:
        event.update(operation="gpio-read", logical_input=registers[0],
                     address=hex32(registers[2]),
                     mask=u32(debugger.memory(registers[1] + registers[0] * 8 + 4, 4)))
    return event


def assertion_capture(debugger, packet, arm_register):
    return {"caller_return": hex32(arm_register(packet, 14)),
            "expression": cstring(debugger, arm_register(packet, 0)),
            "filename_pointer": hex32(arm_register(packet, 1)),
            "filename": cstring(debugger, arm_register(packet, 1)),
            "line": arm_register(packet, 2),
            "arguments": [hex32(arm_register(packet, i)) for i in range(4)]}
