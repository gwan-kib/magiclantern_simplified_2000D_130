#!/usr/bin/env python3
"""Real debugger transport checks on a stopped generic ARM machine.

Run only with QEMU_DEBUGGER_TEST_BINARY pointing to the pinned source build.
No Canon machine, firmware, memory capture or executing guest payload is used.
"""
from __future__ import annotations

import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
import unittest

from tools.eos2000d.qemu_probe import Gdb, Qmp, arm_register


class DebuggerIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        configured = os.environ.get("QEMU_DEBUGGER_TEST_BINARY")
        if not configured:
            raise RuntimeError("QEMU_DEBUGGER_TEST_BINARY is required for integration checks")
        cls.binary = Path(configured).resolve()
        if not cls.binary.is_file():
            raise RuntimeError(f"QEMU debugger integration binary not found: {cls.binary}")

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="qemu-gdb-check-")
        self.addCleanup(self.directory.cleanup)
        root = Path(self.directory.name)
        self.output = (root / "qemu.log").open("w+b")
        self.addCleanup(self.output.close)
        environment = dict(os.environ, QEMU_AUDIO_DRV="none")
        self.process = subprocess.Popen([
            str(self.binary), "-M", "versatilepb", "-m", "16M", "-S",
            "-nodefaults", "-display", "none", "-monitor", "none", "-serial", "none",
            "-qmp", f"unix:{root}/qmp.sock,server,nowait",
            "-gdb", f"unix:{root}/gdb.sock,server,nowait",
        ], stdout=self.output, stderr=subprocess.STDOUT, env=environment)
        self.addCleanup(self.stop_process)
        deadline = time.monotonic() + 5
        while not all((root / name).exists() for name in ("qmp.sock", "gdb.sock")):
            if self.process.poll() is not None:
                self.output.seek(0)
                self.fail("generic QEMU setup failed: " + self.output.read().decode(errors="replace"))
            if time.monotonic() >= deadline:
                self.fail("generic QEMU debugger setup exceeded five seconds")
            time.sleep(.02)
        self.monitor = Qmp(root / "qmp.sock")
        self.addCleanup(self.monitor.close)
        self.debugger = Gdb(root / "gdb.sock")
        self.addCleanup(self.debugger.sock.close)
        self.assertRegex(self.debugger.command("?"), r"^[ST][0-9a-fA-F]{2}")

    def stop_process(self):
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=4)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=4)

    def test_query_registers_and_unsupported_command(self):
        supported = self.debugger.command("qSupported")
        self.assertIn("PacketSize=1000", supported.split(";"))
        registers = self.debugger.command("g")
        for index in (0, 15):
            self.assertIsInstance(arm_register(registers, index), int)
        self.assertEqual(self.debugger.command("qUnimplementedProbeIntegrationCheck"), "")
        self.assertRegex(self.debugger.command("?"), r"^[ST][0-9a-fA-F]{2}")

    def test_consecutive_boundary_memory_reads(self):
        # Generic Versatile/PB maps RAM at zero; the CPU stays stopped throughout.
        for size in (0, 1, 1024, 2048):
            with self.subTest(size=size):
                first = self.debugger.memory(0, size)
                self.assertEqual(len(first), size)
                self.assertEqual(self.debugger.memory(0, size), first)
        self.assertEqual(self.debugger.command("m0,801"), "E22")
        self.assertEqual(len(self.debugger.memory(0, 1024)), 1024)

    def test_idle_deadline_then_command(self):
        with self.assertRaises(socket.timeout):
            self.debugger.receive(time.monotonic() + .05)
        self.assertRegex(self.debugger.command("?"), r"^[ST][0-9a-fA-F]{2}")

    def test_reconnect_and_guest_disconnect(self):
        self.debugger.sock.close()
        path = Path(self.directory.name) / "gdb.sock"
        reconnect = Gdb(path)
        self.addCleanup(reconnect.sock.close)
        self.assertRegex(reconnect.command("?"), r"^[ST][0-9a-fA-F]{2}")
        self.monitor.command("quit")
        self.process.wait(timeout=4)
        with self.assertRaises(EOFError):
            reconnect.receive()


if __name__ == "__main__":
    unittest.main()
