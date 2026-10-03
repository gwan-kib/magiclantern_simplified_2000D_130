import tempfile
import unittest
from pathlib import Path

from tools.eos2000d.rom_manifest import inspect_image


class RomManifestTests(unittest.TestCase):
    def test_manifest_detects_expected_entry_and_version_string(self):
        # 0xEA000001 at 0xFE0C0000 is ARM B to base + 0xC.
        image = (
            bytes.fromhex("01 00 00 EA")
            + b"\x00" * 28
            + b"Canon EOS 2000D Firmware Version 1.3.0\x00"
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "synthetic-rom.bin"
            path.write_bytes(image)
            manifest = inspect_image(path, 0xFE0C0000, firmware="1.3.0")

        self.assertEqual(manifest["mapping"]["first_word_le"], "0xEA000001")
        self.assertTrue(manifest["mapping"]["expected_first_word_matches"])
        self.assertEqual(
            manifest["mapping"]["decoded_first_branch_target"], "0xFE0C000C"
        )
        self.assertEqual(manifest["source"]["byte_size"], len(image))
        self.assertEqual(len(manifest["source"]["sha256"]), 64)
        self.assertTrue(
            any("1.3.0" in item["text"] for item in manifest["ascii_evidence"])
        )

    def test_bank_base_is_distinct_from_main_entry_and_mirrors(self):
        image = bytes(0x20) + bytes.fromhex("01 00 00 EA") + bytes(12)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "synthetic-bank.bin"
            path.write_bytes(image)
            result = inspect_image(path, 0xF8000000, main_offset=0x20,
                                   aliases=(0xFA000000, 0xFE000000), firmware="1.1.0")
        mapping = result["mapping"]
        self.assertEqual(mapping["first_word_le"], "0x00000000")
        self.assertEqual(mapping["entry_word_le"], "0xEA000001")
        self.assertEqual(mapping["main_firmware_address"], "0xF8000020")
        self.assertEqual(mapping["decoded_entry_branch_target"], "0xF800002C")
        self.assertEqual(mapping["aliases"][1]["main_firmware_address"], "0xFE000020")
        self.assertEqual(mapping["aliases"][1]["decoded_entry_branch_target"], "0xFE00002C")
        self.assertEqual(result["target"]["firmware"], "1.1.0")

    def test_no_mapping_or_firmware_is_invented(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "synthetic.bin"
            path.write_bytes(bytes.fromhex("01 00 00 EA"))
            result = inspect_image(path)
        self.assertIsNone(result["mapping"]["bank_base"])
        self.assertIsNone(result["mapping"]["main_firmware_address"])
        self.assertIsNone(result["mapping"]["decoded_entry_branch_target"])
        self.assertIsNone(result["target"]["firmware"])

    def test_invalid_offsets_and_address_wrap_fail(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "synthetic.bin"
            path.write_bytes(bytes(16))
            for options in ({"main_offset": -1}, {"main_offset": 13},
                            {"aliases": (0xFE000000,)}):
                with self.assertRaises(ValueError):
                    inspect_image(path, **options)
            with self.assertRaises(ValueError):
                inspect_image(path, 0xFFFFFFF8)


if __name__ == "__main__":
    unittest.main()
