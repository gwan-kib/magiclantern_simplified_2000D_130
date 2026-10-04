"""Read-only debugger diagnostics for the canonical 2000D.110 FlashIF path.

Addresses are evidence-qualified PCs, not physical-camera constants. Output
contains private instructions/registers and must stay outside the repository.
"""
from __future__ import annotations
import struct
import time

MMIO_PCS = frozenset(
    [0xFE0C0014, 0x1D278, 0x1D280, 0x1D288, 0x1D290, 0x1D298,
     0x1D2A0, 0x1D2A8, 0x1D2B0, 0x1D2C0, 0x1D2C8, 0x1D2D0,
     0x1D2D8, 0x1D2E0, 0x1D2E8, 0x1D2F0, 0x1D2F8, 0x1D31C,
     0x1D328, 0x1D330, 0x1D338, 0x1D340, 0x1D348, 0x1D350,
     0x1D358, 0x1D360, 0x1D36C, 0x1D374, 0x1D37C, 0x1D384,
     0x1D38C, 0x1D394, 0x1D39C])
BANK_PCS = frozenset([0x1D554, 0x1D58C, 0x1D4E4])
CONTEXT_PCS = frozenset([0x27C4, 0x2828, 0xB444, 0x1D3A8,
                         0xFE0C1BC0, 0xFE0C1BC4])
TRACE_PCS = MMIO_PCS | BANK_PCS | CONTEXT_PCS


def condition_passed(instruction: int, cpsr: int) -> bool:
    n, z, c, v = (bool(cpsr & (1 << bit)) for bit in (31, 30, 29, 28))
    conditions = [z, not z, c, not c, n, not n, v, not v,
                  c and not z, not c or z, n == v, n != v,
                  not z and n == v, z or n != v, True, False]
    return conditions[instruction >> 28]


def decode_transfer(instruction: int, registers: list[int]) -> dict:
    """Decode the unsigned ARM halfword/byte/word transfers observed on this path.

    Never execute an MMIO read through GDB to obtain a value: step the guest
    instruction and sample its destination register instead.
    """
    rn, rd = (instruction >> 16) & 15, (instruction >> 12) & 15
    if instruction & 0x0E0000F0 == 0x000000B0:
        width = 16
        offset = (((instruction >> 4) & 0xF0) | (instruction & 15)
                  if instruction & (1 << 22) else registers[instruction & 15])
    elif instruction & 0x0C000000 == 0x04000000:
        width = 8 if instruction & (1 << 22) else 32
        if instruction & (1 << 25):
            if instruction & 0xFF0:
                raise ValueError("shifted/register byte offset is unsupported")
            offset = registers[instruction & 15]
        else:
            offset = instruction & 0xFFF
    else:
        raise ValueError("unsupported FlashIF access instruction")
    base = registers[rn] + (8 if rn == 15 else 0)
    if not instruction & (1 << 23):
        offset = -offset
    address = (base + offset if instruction & (1 << 24) else base) & 0xFFFFFFFF
    return {"operation": "read" if instruction & (1 << 20) else "write",
            "address": f"0x{address:08X}", "width": width, "register": rd}


def capture(debugger, packet: str, arm_register, cpsr: int) -> dict:
    registers = [arm_register(packet, i) for i in range(16)]
    pc = registers[15]
    event = {"time_monotonic_ns": time.monotonic_ns(), "pc": f"0x{pc:08X}",
             "registers": [f"0x{r:08X}" for r in registers],
             "lr": f"0x{registers[14]:08X}"}
    if pc in MMIO_PCS | BANK_PCS:
        instruction, = struct.unpack("<I", debugger.memory(pc, 4))
        event["instruction"] = f"0x{instruction:08X}"
        event["cpsr"] = f"0x{cpsr:08X}"
        event["executed"] = condition_passed(instruction, cpsr)
        if not event["executed"]:
            event["operation"] = "skipped"
            return event
        event.update(decode_transfer(instruction, registers))
        event["instruction"] = f"0x{instruction:08X}"
        if event["operation"] == "write":
            event["value"] = registers[event["register"]] & ((1 << event["width"]) - 1)
    else:
        event["operation"] = "context"
        if pc == 0x1D3A8:
            event["descriptor"] = debugger.memory(registers[0], 28).hex()
        elif pc == 0x27C4:
            event["fifth_argument"] = debugger.memory(registers[13], 4).hex()
        elif pc in (0xFE0C1BC0, 0xFE0C1BC4):
            event["caller_outputs"] = debugger.memory(registers[13] + 8, 16).hex()
        elif pc == 0xB444:
            event["received_bytes"] = debugger.memory(registers[13] + 32, 4).hex()
    return event


def check_mmio_coverage(events: list[dict], output: str) -> int:
    """Compare every FlashIF I/O log entry with executed debugger accesses.

    This detects missing instrumentation for new controller PCs. Width and
    register state come from the debugger, not the width-less upstream log.
    """
    import re
    output = re.sub(r"\x1b\[[0-9;]*m", "", output)
    expected = []
    for line in output.splitlines():
        if "[FlashIF]" not in line:
            continue
        match = re.search(r"(?:0x|:)([0-9A-Fa-f]{8}):[0-9A-Fa-f]{8} ", line)
        access = re.search(r"\[0x([0-9A-Fa-f]{8})\] (->|<-) 0x([0-9A-Fa-f]+)", line)
        if not match or not access:
            raise ValueError("cannot parse a FlashIF log entry")
        expected.append((int(match[1], 16), int(access[1], 16),
                         "read" if access[2] == "->" else "write", int(access[3], 16)))
    actual = [(int(e["pc"], 16), int(e["address"], 16), e["operation"], e["value"])
              for e in events if e.get("address", "").startswith("0xC000")]
    if not expected or actual != expected:
        raise ValueError("debugger FlashIF sequence differs from emulator I/O log")
    return len(actual)
