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
            manifest = inspect_image(path)

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


if __name__ == "__main__":
    unittest.main()
