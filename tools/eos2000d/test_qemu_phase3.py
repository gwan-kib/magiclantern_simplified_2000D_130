import sys
import copy
import socket
import tempfile
import unittest
from pathlib import Path

from tools.eos2000d.qemu_eos_patch import patch_texts
from tools.eos2000d.qemu_smoke import find_ordered_markers, run_command, check_startup_report, STARTUP_110_PCS
from tools.eos2000d.qemu_probe import Gdb, arm_register
from tools.eos2000d.qemu_workdir import ROM1_110_SHA256
from tools.eos2000d.qemu_workdir import camera_dir, prepare, launch_command, validate_roms


class QemuPatchTests(unittest.TestCase):
    def test_patch_adds_model_machine_and_registration(self):
        model_h = (
            '#define MODEL_NAME_1300D "1300D"\n'
            '#define MODEL_NAME_A1100 "A1100"\n'
        )
        model_c = (
            '    {\n'
            '        .name                   = MODEL_NAME_A1100,\n'
            '    },\n'
        )
        eos_c = (
            'static void eos_A1100_machine_init(MachineClass *mc)\n'
            '{\n}\n'
            'DEFINE_MACHINE(MODEL_NAME_A1100, eos_A1100_machine_init)\n'
            'static void eos_init_common(void)\n{\n    eos_init_cpu();\n'
            '    if (options)\n    {\n        /* fixme: reinventing the wheel */\n}\n}\n'
        )

        out_h, out_model, out_eos = patch_texts(model_h, model_c, eos_c)
        self.assertIn('MODEL_NAME_2000D "2000D"', out_h)
        self.assertIn(".name                   = MODEL_NAME_2000D,", out_model)
        self.assertIn(".firmware_version       = 130,", out_model)
        self.assertIn("eos_2000D_machine_init", out_eos)
        self.assertIn(
            "DEFINE_MACHINE(MODEL_NAME_2000D, eos_2000D_machine_init)",
            out_eos,
        )
        self.assertIn('atoi(eos2000d_options) == 110', out_eos)
        self.assertLess(out_eos.index('rom0_size = 0'), out_eos.index('    eos_init_cpu();'))
        self.assertIn('firmware_version = 110', out_eos)
        self.assertIn('rom1_addr = 0xF8000000', out_eos)
        self.assertIn('rom1_size = 0x02000000', out_eos)
        self.assertIn('strstr(options, "start=main")', out_eos)
        self.assertIn('firmware_start = 0xFE0C0000', out_eos)
        self.assertIn('env.regs[15] = eos_state->model->firmware_start', out_eos)

        self.assertIn('strstr(options, "vectors=low")', out_eos)
        self.assertIn('cp15.sctlr_ns &= ~SCTLR_V', out_eos)
        self.assertIn('bootloader state assumed', out_eos)

        # Idempotence.
        second = patch_texts(out_h, out_model, out_eos)
        self.assertEqual(second, (out_h, out_model, out_eos))


class QemuSmokeTests(unittest.TestCase):
    def test_ordered_markers_pass(self):
        log = "canon start\nloader entered\nminimal entered\ncanon continued\n"
        ok, _ = find_ordered_markers(
            log,
            ["canon start", "loader entered", "minimal entered", "canon continued"],
        )
        self.assertTrue(ok)

    def test_wrong_order_fails(self):
        log = "loader entered\ncanon start\n"
        ok, reason = find_ordered_markers(log, ["canon start", "loader entered"])
        self.assertFalse(ok)
        self.assertIn("missing marker", reason)

    def test_empty_markers_fail(self):
        ok, _ = find_ordered_markers("anything", [])
        self.assertFalse(ok)

    def test_runner_captures_output_before_timeout(self):
        output, _return_code, timed_out = run_command(
            [
                sys.executable,
                "-c",
                "import time; print('canon start', flush=True); time.sleep(1)",
            ],
            0.1,
        )
        self.assertTrue(timed_out)
        self.assertIn("canon start", output)


class StartupReportTests(unittest.TestCase):
    def setUp(self):
        self.report = {
            "returncode": 0, "rom1_sha256": ROM1_110_SHA256,
            "ram_copy": {"matches_rom_source": True},
            "stages": [{"pc": pc} for pc in STARTUP_110_PCS],
        }

    def test_measured_startup_report_passes(self):
        self.assertTrue(check_startup_report(self.report)[0])

    def test_missing_or_out_of_order_stop_fails(self):
        for stages in [self.report["stages"][:-1], list(reversed(self.report["stages"]))]:
            bad = copy.deepcopy(self.report)
            bad["stages"] = stages
            self.assertFalse(check_startup_report(bad)[0])

    def test_hash_copy_and_execution_failures_rejected(self):
        for field, value in [("rom1_sha256", "wrong"), ("returncode", -9),
                             ("error", "launch failed"),
                             ("ram_copy", {"matches_rom_source": False})]:
            bad = copy.deepcopy(self.report)
            bad[field] = value
            self.assertFalse(check_startup_report(bad)[0])

    def test_setup_text_does_not_count_as_execution(self):
        bad = copy.deepcopy(self.report)
        bad["stages"] = [{"pc": "setup message " + pc} for pc in STARTUP_110_PCS]
        self.assertFalse(check_startup_report(bad)[0])


class DebuggerPacketTests(unittest.TestCase):
    def test_receives_packet_with_ack_prefix(self):
        client, server = socket.socketpair()
        try:
            debugger = object.__new__(Gdb)
            debugger.sock = client
            server.sendall(b"+$OK#9a")
            self.assertEqual(debugger.receive(), "OK")
            self.assertEqual(server.recv(1), b"+")
        finally:
            client.close()
            server.close()

    def test_rejects_checksum_mismatch(self):
        client, server = socket.socketpair()
        try:
            debugger = object.__new__(Gdb)
            debugger.sock = client
            server.sendall(b"$OK#00")
            with self.assertRaises(ValueError):
                debugger.receive()
        finally:
            client.close()
            server.close()

    def test_disconnect_does_not_spin(self):
        client, server = socket.socketpair()
        debugger = object.__new__(Gdb)
        debugger.sock = client
        server.close()
        try:
            with self.assertRaises(EOFError):
                debugger.receive()
        finally:
            client.close()

    def test_arm_pc_is_little_endian(self):
        packet = (b"\0" * 60 + (0xFE0C0000).to_bytes(4, "little")).hex()
        self.assertEqual(arm_register(packet, 15), 0xFE0C0000)
        with self.assertRaises(ValueError):
            arm_register("00", 15)


class QemuWorkdirTests(unittest.TestCase):
    def test_110_needs_canonical_rom1_and_forbids_rom0(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            messages = prepare(root, True, False, "110")
            self.assertTrue(camera_dir(root, "110").is_dir())
            self.assertTrue(any("ROM1.BIN" in message for message in messages))
            self.assertFalse(any("ROM0.BIN" in message for message in messages))
            (camera_dir(root, "110") / "ROM1.BIN").write_bytes(b"invalid synthetic image")
            (camera_dir(root, "110") / "ROM0.BIN").write_bytes(b"invalid")
            errors = validate_roms(root, "110")
            self.assertTrue(any("canonical" in error for error in errors))
            self.assertTrue(any("ROM0" in error for error in errors))

    def test_main_entry_is_explicit_and_only_for_110(self):
        command = launch_command(Path("private"), "qemu", "110")
        self.assertIn('firmware=110"', command)
        self.assertNotIn("start=main", command)
        self.assertIn("110;start=main", launch_command(Path("private"), "qemu", "110", True))
        with self.assertRaises(ValueError):
            launch_command(Path("private"), "qemu", "130", True)

    def test_low_vectors_requires_direct_entry_and_raw_disks(self):
        with self.assertRaises(ValueError):
            launch_command(Path("private"), "qemu", "110", low_vectors=True)
        with self.assertRaises(ValueError):
            launch_command(Path("private"), "qemu", "130", True, True)
        command = launch_command(Path("private"), "qemu", "110", True, True)
        self.assertIn("110;start=main;vectors=low", command)
        self.assertIn("if=sd,format=raw", command)

    def test_prepare_creates_layout_but_not_roms(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            messages = prepare(root, create=True, create_disks=True)
            self.assertTrue(camera_dir(root).is_dir())
            self.assertTrue((root / "sd.img").is_file())
            self.assertTrue((root / "cf.img").is_file())
            self.assertFalse((camera_dir(root) / "ROM0.BIN").exists())
            self.assertFalse((camera_dir(root) / "ROM1.BIN").exists())
            self.assertTrue(any("MISSING" in item for item in messages))


if __name__ == "__main__":
    unittest.main()
