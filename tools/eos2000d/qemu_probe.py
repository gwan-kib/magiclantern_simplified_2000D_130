#!/usr/bin/env python3
"""Bounded private 2000D.110 QEMU probes using hardware debugger breakpoints.

Results contain private firmware disassembly/memory. Keep --log-dir outside Git.
A successful probe/smoke result proves init-task entry, not a complete boot.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import struct
import subprocess
import tempfile
import time

try:
    from .qemu_smoke import STARTUP_110_PCS
    from .qemu_workdir import validate_roms
except ImportError:
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
        self.sock.settimeout(max(.05, deadline - time.monotonic()) if deadline else 4)
        while True:
            prefix = self.sock.recv(1)
            if not prefix:
                raise EOFError("GDB connection closed")
            if prefix == b"$":
                break
        data = bytearray()
        while True:
            char = self.sock.recv(1)
            if not char:
                raise EOFError("GDB packet truncated")
            if char == b"#":
                break
            data.extend(char)
        checksum = self.sock.recv(1) + self.sock.recv(1)
        if checksum != f"{sum(data) % 256:02x}".encode():
            raise ValueError("GDB checksum mismatch")
        self.sock.sendall(b"+")
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
    chunks = [debugger.memory(address, min(1024, end - address))
              for address in range(destination, end, 1024)]
    data = b"".join(chunks)
    offset = source & 0x1FFFFFF
    return {
        "source": hex(source), "destination": hex(destination), "end": hex(end),
        "bss_end": hex(bss_end), "size": len(data),
        "ram_sha256": hashlib.sha256(data).hexdigest(),
        "matches_rom_source": data == rom[offset:offset + len(data)],
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
    debugger = monitor = process = None
    # Keep Unix sockets short even when Windows-mounted results paths are long.
    with tempfile.TemporaryDirectory(prefix="eos-qemu-") as temporary:
        sockets = Path(temporary)
        selector = "110" + (";start=main" if args.start_main else "")
        if args.low_vectors:
            selector += ";vectors=low"
        command = [str(args.binary.resolve()), "-M", f"2000D,firmware={selector}",
                   "-drive", f"file={root}/cf.img,if=ide,format=raw",
                   "-drive", f"file={root}/sd.img,if=sd,format=raw",
                   "-serial", f"file:{directory}/serial.log", "-display", "none",
                   "-monitor", "none", "-d", "in_asm,io,int,guest_errors",
                   "-D", str(directory / "trace.log"), "-S", "-qmp",
                   f"unix:{sockets}/qmp.sock,server,nowait", "-gdb",
                   f"unix:{sockets}/gdb.sock,server,nowait"]
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
                addresses = set(int(pc, 16) for pc in STARTUP_110_PCS) | set(args.stop_at)
                addresses.add(0xFE0C3B34)  # Startup pointer literal, not an expected instruction.
                for address in addresses:
                    if debugger.command(f"Z1,{address:x},4") != "OK":
                        raise RuntimeError(f"Cannot set hardware breakpoint at {address:#x}")
                deadline = time.monotonic() + args.timeout
                debugger.resume()
                while True:
                    try:
                        stop = debugger.receive(deadline)
                    except socket.timeout:
                        result["bounded_stop"] = True
                        debugger.interrupt()
                        break
                    packet = debugger.command("g")
                    pc = arm_register(packet, 15)
                    if not stop.startswith(("S05", "T05")):
                        raise RuntimeError(f"Unexpected debugger stop: {stop}")
                    result["stages"].append({"pc": f"0x{pc:08X}", "stop": stop,
                                             "registers": monitor.registers()})
                    if pc == 0xFE0C3A38:
                        result["ram_copy"] = verify_ram_copy(debugger, rom)
                        result["vectors_at_cstart"] = debugger.memory(0, 0x38).hex()
                    if pc in args.stop_at:
                        result["stop_address"] = f"0x{pc:08X}"
                        sp = arm_register(packet, 13)
                        result["stack_at_stop"] = debugger.memory(sp, 0x80).hex()
                        break
                    if pc not in addresses:
                        raise RuntimeError(f"Unexpected breakpoint PC: {pc:#x}")
                    debugger.command(f"z1,{pc:x},4")
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
    parser.add_argument("--low-vectors", action="store_true")
    parser.add_argument("--repeat", type=int, default=2)
    parser.add_argument("--timeout", type=float, default=3)
    parser.add_argument("--stop-at", action="append", type=lambda value: int(value, 0), default=[])
    args = parser.parse_args()
    if args.low_vectors and not args.start_main:
        parser.error("--low-vectors requires --start-main")
    if args.repeat < 1 or args.timeout <= 0:
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
