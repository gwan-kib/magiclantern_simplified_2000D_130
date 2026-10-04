#!/usr/bin/env python3
"""Bounded private 2000D.110 QEMU probes using hardware debugger breakpoints.

Results contain private firmware disassembly/memory. Keep --log-dir outside Git.
A successful probe/smoke result proves init-task entry, not a complete boot.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
from pathlib import Path
import socket
import struct
import subprocess
import tempfile
import time

try:
    from . import qemu_flash_trace, qemu_task_trace
    from .qemu_smoke import STARTUP_110_PCS
    from .qemu_workdir import validate_roms
except ImportError:
    import qemu_flash_trace
    import qemu_task_trace
    from qemu_smoke import STARTUP_110_PCS
    from qemu_workdir import validate_roms


class Qmp:
    def __init__(self, path: Path):
        self.sock = socket.socket(socket.AF_UNIX)
        self.sock.settimeout(4)
        self.sock.connect(str(path))
        self.stream = self.sock.makefile("rwb")
        self.stream.readline()
        self.command("qmp_capabilities")

    def command(self, name: str, arguments=None):
        request = {"execute": name}
        if arguments:
            request["arguments"] = arguments
        self.stream.write(json.dumps(request).encode() + b"\n")
        self.stream.flush()
        while True:
            line = self.stream.readline()
            if not line:
                raise EOFError("QMP connection closed")
            reply = json.loads(line)
            if "return" in reply:
                return reply["return"]
            if "error" in reply:
                raise RuntimeError(reply["error"])

    def registers(self):
        return self.command("human-monitor-command", {"command-line": "info registers"})

    def close(self):
        self.stream.close()
        self.sock.close()


class Gdb:
    """Small RSP client for stops/registers/memory; never writes firmware bytes."""
    def __init__(self, path: Path):
        self.sock = socket.socket(socket.AF_UNIX)
        self.sock.settimeout(4)
        self.sock.connect(str(path))

    def receive(self, deadline=None):
        deadline = time.monotonic() + 4 if deadline is None else deadline

        def read_byte():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise socket.timeout("GDB receive deadline exceeded")
            self.sock.settimeout(remaining)
            char = self.sock.recv(1)
            if not char:
                raise EOFError("GDB packet truncated or connection closed")
            return char

        while read_byte() != b"$":
            pass
        data = bytearray()
        while True:
            char = read_byte()
            if char == b"#":
                break
            # Pinned qemu-eos gdbstub.c advertises PacketSize=1000 (hex).
            if len(data) >= 4096:
                raise ValueError("GDB packet exceeds supported 4096-byte limit")
            data.extend(char)
        checksum = read_byte() + read_byte()
        if checksum != f"{sum(data) % 256:02x}".encode():
            raise ValueError("GDB checksum mismatch")
        try:
            self.sock.sendall(b"+")
        except BrokenPipeError as exc:
            raise EOFError("GDB peer closed before reply acknowledgement") from exc
        return data.decode("ascii")

    def command(self, text):
        data = text.encode("ascii")
        self.sock.sendall(b"$" + data + b"#" + f"{sum(data) % 256:02x}".encode())
        return self.receive()

    def resume(self):
        self.sock.sendall(b"$c#63")

    def interrupt(self):
        self.sock.sendall(b"\x03")
        return self.receive()

    def memory(self, address, size):
        data = bytes.fromhex(self.command(f"m{address:x},{size:x}"))
        if len(data) != size:
            raise ValueError("short GDB memory reply")
        return data


def arm_register(packet: str, index: int) -> int:
    if len(packet) < 16 * 8:
        raise ValueError("incomplete ARM core register packet")
    return int.from_bytes(bytes.fromhex(packet[index * 8:(index + 1) * 8]), "little")


def verify_ram_copy(debugger: Gdb, rom: bytes) -> dict:
    # Canonical ROM1 startup literals at FE0C00DC..FE0C00E8; end is exclusive.
    source, destination, end, bss_end = struct.unpack_from("<4I", rom, 0xC00DC)
    offset = source & 0x1FFFFFF
    if end <= destination or offset + end - destination > len(rom):
        raise ValueError("invalid ROM-to-RAM copy bounds")
    chunks = []
    for address in range(destination, end, 1024):
        size = min(1024, end - address)
        chunk = debugger.memory(address, size)
        if len(chunk) != size:
            raise ValueError(f"incomplete RAM read at {address:#x}: expected {size}, got {len(chunk)}")
        chunks.append(chunk)
    data = b"".join(chunks)
    return {
        "source": hex(source), "destination": hex(destination), "end": hex(end),
        "bss_end": hex(bss_end), "size": len(data),
        "ram_sha256": hashlib.sha256(data).hexdigest(),
        "matches_rom_source": data == rom[offset:offset + end - destination],
    }


def probe(args, repeat: int) -> dict:
    root = args.root.resolve()
    directory = args.log_dir.resolve() / f"{args.mode}-{repeat}"
    directory.mkdir(parents=True, exist_ok=False)
    rom = (root / "2000D/110/ROM1.BIN").read_bytes()
    result = {
        "schema_version": 1, "firmware": "110", "mode": args.mode,
        "repeat": repeat, "rom1_sha256": hashlib.sha256(rom).hexdigest(),
        "timeout_seconds": args.timeout, "stages": [],
    }
    task_trace = getattr(args, "task_trace", False)
    sample_interval = getattr(args, "sample_interval", 0)
    debugger = monitor = process = None
    # Keep Unix sockets short even when Windows-mounted results paths are long.
    with tempfile.TemporaryDirectory(prefix="eos-qemu-") as temporary:
        sockets = Path(temporary)
        selector = "110" + (";start=main" if args.start_main else "")
        if args.low_vectors:
            selector += ";vectors=low"
        if args.flash_id:
            selector += ";flash-id=" + args.flash_id
            result["experimental_flash_id"] = args.flash_id
        command = [str(args.binary.resolve()), "-M", f"2000D,firmware={selector}",
                   "-drive", f"file={root}/cf.img,if=ide,format=raw",
                   "-drive", f"file={root}/sd.img,if=sd,format=raw",
                   "-serial", f"file:{directory}/serial.log", "-display", "none",
                   "-monitor", "none", "-d", "in_asm,io,int,guest_errors",
                   "-D", str(directory / "trace.log"), "-S", "-qmp",
                   f"unix:{sockets}/qmp.sock,server,nowait", "-gdb",
                   f"unix:{sockets}/gdb.sock,server,nowait"]
        if task_trace:
            command[command.index("-d") + 1] += ",tasks,mpu"
            result["task_trace_classification"] = "QEMU + Experiment; observation fields only"
        result["command"] = command
        environment = os.environ.copy()
        environment["QEMU_EOS_WORKDIR"] = str(root)
        with (directory / "output.log").open("wb") as output:
            try:
                process = subprocess.Popen(command, env=environment, stdout=output,
                                           stderr=subprocess.STDOUT, cwd=args.binary.resolve().parent)
                deadline = time.monotonic() + 5
                while not all((sockets / name).exists() for name in ["qmp.sock", "gdb.sock"]):
                    if process.poll() is not None:
                        raise RuntimeError(f"QEMU exited during setup: {process.returncode}")
                    if time.monotonic() >= deadline:
                        raise TimeoutError("QEMU debugger setup timed out")
                    time.sleep(.03)
                monitor, debugger = Qmp(sockets / "qmp.sock"), Gdb(sockets / "gdb.sock")
                debugger.command("?")
                result["initial_registers"] = monitor.registers()
                addresses = set(int(pc, 16) for pc in STARTUP_110_PCS) | set(args.stop_at) | set(args.watch_at)
                if args.flashif_trace:
                    addresses.update(qemu_flash_trace.TRACE_PCS)
                if task_trace:
                    addresses.update(qemu_task_trace.TRACE_PCS)
                    addresses.add(0x3CBC)
                addresses.add(0xFE0C3B34)  # Startup pointer literal, not an expected instruction.
                for address in addresses:
                    if debugger.command(f"Z1,{address:x},4") != "OK":
                        raise RuntimeError(f"Cannot set hardware breakpoint at {address:#x}")
                deadline = time.monotonic() + args.timeout
                debugger.resume()
                next_sample = time.monotonic() + sample_interval
                while True:
                    try:
                        stop = debugger.receive(min(deadline,next_sample) if sample_interval else deadline)
                    except socket.timeout:
                        if sample_interval and time.monotonic() < deadline:
                            debugger.interrupt()
                            sample = qemu_task_trace.capture(debugger,debugger.command("g"),arm_register,"sample")
                            sample["step"] = result.get("task_events",0)+1
                            result["task_events"] = sample["step"]
                            with (directory/"tasks.jsonl").open("a") as stream:
                                stream.write(json.dumps(sample)+"\n")
                            next_sample = time.monotonic()+sample_interval
                            debugger.resume()
                            continue
                        result["bounded_stop"] = True
                        debugger.interrupt()
                        break
                    packet = debugger.command("g")
                    pc = arm_register(packet, 15)
                    if sample_interval and time.monotonic() >= next_sample:
                        sample = qemu_task_trace.capture(debugger, packet, arm_register, "sample")
                        sample["step"] = result.get("task_events", 0) + 1
                        result["task_events"] = sample["step"]
                        with (directory / "tasks.jsonl").open("a") as stream:
                            stream.write(json.dumps(sample) + "\n")
                        next_sample = time.monotonic() + sample_interval
                    if not stop.startswith(("S05", "T05")):
                        raise RuntimeError(f"Unexpected debugger stop: {stop}")
                    task_event = (qemu_task_trace.capture(debugger,packet,arm_register)
                                  if task_trace and pc in qemu_task_trace.TRACE_PCS else None)
                    trace_event = None
                    if args.flashif_trace and pc in qemu_flash_trace.TRACE_PCS:
                        psr = re.search(r"PSR=([0-9a-fA-F]+)", monitor.registers())
                        if not psr:
                            raise RuntimeError("Cannot read ARM condition flags")
                        trace_event = qemu_flash_trace.capture(debugger, packet, arm_register,
                                                              int(psr.group(1), 16))
                    if (pc in [int(p, 16) for p in STARTUP_110_PCS] or pc in args.watch_at or pc in args.stop_at
                            or (pc not in qemu_task_trace.TRACE_PCS and
                                (not args.flashif_trace or pc not in qemu_flash_trace.TRACE_PCS))):
                        result["stages"].append({"pc": f"0x{pc:08X}", "stop": stop,
                                                 "registers": monitor.registers()})
                    if pc == 0xFE0C3A38:
                        result["ram_copy"] = verify_ram_copy(debugger, rom)
                        result["vectors_at_cstart"] = debugger.memory(0, 0x38).hex()
                    if pc in args.stop_at or (task_trace and pc == 0x3CBC):
                        result["stop_address"] = f"0x{pc:08X}"
                        if pc == 0x3CBC:
                            result["assertion"] = qemu_task_trace.assertion_capture(debugger, packet, arm_register)
                        sp = arm_register(packet, 13)
                        result["stack_at_stop"] = debugger.memory(sp, 0x80).hex()
                        break
                    if pc not in addresses:
                        raise RuntimeError(f"Unexpected breakpoint PC: {pc:#x}")
                    debugger.command(f"z1,{pc:x},4")
                    if trace_event is not None or task_event is not None:
                        stepped = debugger.command("s")
                        if not stepped.startswith(("S05", "T05")):
                            raise RuntimeError(f"Unexpected single-step stop: {stepped}")
                        after = debugger.command("g")
                        after_pc = arm_register(after, 15)
                        if after_pc != (pc + 4) & 0xFFFFFFFF:
                            raise RuntimeError(f"Trace step interrupted at {after_pc:#x}")
                        if task_event is not None:
                            if task_event["operation"] == "switch":
                                pointer=qemu_task_trace.u32(debugger.memory(qemu_task_trace.CURRENT_SLOT,4))
                                if f"0x{pointer:08X}" != task_event["new"]["pointer"]:
                                    raise RuntimeError("scheduler pointer did not match stepped switch")
                                task_event["committed_pointer"]=f"0x{pointer:08X}"
                            if task_event["operation"] == "irq-reason":
                                reason = arm_register(after, 4)
                                task_event.update(reason=reason, irq=reason // 4)
                            if task_event["operation"] == "gpio-read":
                                task_event["value"] = arm_register(after, 2)
                            task_event["step"]=result.get("task_events",0)+1
                            result["task_events"]=task_event["step"]
                            with (directory/"tasks.jsonl").open("a") as stream:
                                stream.write(json.dumps(task_event)+"\n")
                        if trace_event is not None and trace_event["operation"] == "read":
                            trace_event["value"] = arm_register(after, trace_event["register"])
                        if trace_event is not None:
                            trace_event["step"] = result.get("flashif_events", 0) + 1
                            result["flashif_events"] = trace_event["step"]
                            with (directory / "flashif.jsonl").open("a") as stream:
                                stream.write(json.dumps(trace_event) + "\n")
                        if debugger.command(f"Z1,{pc:x},4") != "OK":
                            raise RuntimeError("Cannot restore trace breakpoint")
                    if time.monotonic() >= deadline:
                        result["bounded_stop"] = True
                        break
                    debugger.resume()
                result["final_registers"] = monitor.registers()
                for address in [0, 0x5254, 0x29898]:
                    result[f"memory_{address:08x}"] = debugger.memory(address, 0x80).hex()
                monitor.command("quit")
                result["returncode"] = process.wait(timeout=4)
            except Exception as error:
                result["error"] = str(error)
            finally:
                if process is not None and process.poll() is None:
                    process.kill()
                    result["returncode"] = process.wait(timeout=4)
                if debugger:
                    debugger.sock.close()
                if monitor:
                    monitor.close()
    if args.flashif_trace and not result.get("error"):
        try:
            events = [json.loads(line) for line in (directory / "flashif.jsonl").read_text().splitlines()]
            result["flashif_mmio_coverage"] = qemu_flash_trace.check_mmio_coverage(
                events, (directory / "output.log").read_text(errors="replace"))
        except (OSError, ValueError) as error:
            result["error"] = str(error)
    (directory / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"result": str(directory / "result.json"),
                      "stages": [stage["pc"] for stage in result["stages"]],
                      "error": result.get("error")}), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="private QEMU workdir")
    parser.add_argument("--binary", required=True, type=Path)
    parser.add_argument("--log-dir", required=True, type=Path, help="private results directory outside Git")
    parser.add_argument("--start-main", action="store_true")
    parser.add_argument("--flash-id", choices=["c22539"],
                        help="explicit hypothetical JEDEC identity; not a physical T7 fact")
    parser.add_argument("--watch-at", action="append", type=lambda value: int(value, 0), default=[],
                        help="record registers at an additional PC and continue")
    parser.add_argument("--task-trace", action="store_true", help="private read-only scheduler/task observations")
    parser.add_argument("--sample-interval", type=float, default=0, help="periodic debugger sampling in seconds; zero disables")
    parser.add_argument("--flashif-trace", action="store_true",
                        help="private register/width/command trace for the canonical flash path")
    parser.add_argument("--low-vectors", action="store_true")
    parser.add_argument("--repeat", type=int, default=2)
    parser.add_argument("--timeout", type=float, default=3)
    parser.add_argument("--stop-at", action="append", type=lambda value: int(value, 0), default=[])
    args = parser.parse_args()
    if not math.isfinite(args.sample_interval) or args.sample_interval < 0 or (args.sample_interval and not args.task_trace):
        parser.error("sample interval must be nonnegative and requires --task-trace")
    if args.task_trace and not (args.start_main and args.low_vectors and args.flash_id == "c22539"):
        parser.error("--task-trace requires the explicit C2/low-vector/main experiment")
    if args.flashif_trace and not (args.start_main and args.low_vectors):
        parser.error("--flashif-trace requires --start-main and --low-vectors")
    if args.low_vectors and not args.start_main:
        parser.error("--low-vectors requires --start-main")
    if args.repeat < 1 or not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("repeat and timeout must be positive")
    if args.log_dir.resolve().is_relative_to(Path(__file__).resolve().parents[2]):
        parser.error("private firmware traces must stay outside the repository")
    errors = validate_roms(args.root, "110")
    if errors:
        parser.error("; ".join(errors))
    args.mode = "low-vectors" if args.low_vectors else "main" if args.start_main else "reset"
    results = [probe(args, repeat) for repeat in range(1, args.repeat + 1)]
    return 1 if any(result.get("error") for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
