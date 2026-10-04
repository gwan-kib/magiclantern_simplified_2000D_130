import sys
import tempfile
import unittest
from pathlib import Path

from tools.eos2000d.qemu_eos_patch import patch_texts
from tools.eos2000d.qemu_smoke import find_ordered_markers, run_command
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
