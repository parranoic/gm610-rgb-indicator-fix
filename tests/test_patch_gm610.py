"""Offline unit tests; no device, stock firmware or external dependencies needed."""
import hashlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import patch_gm610 as gm


class GM610PatchTests(unittest.TestCase):
    def setUp(self):
        self.synthetic = bytearray([0xCC] * gm.APP_SIZE)
        for address, old_hex, _, _ in gm.PATCHES:
            original = bytes.fromhex(old_hex)
            self.synthetic[address:address + len(original)] = original

    def test_changes_exactly_nine_bytes(self):
        patched, changed = gm.patch_application(bytes(self.synthetic))
        self.assertEqual(len(changed), 9)
        for offset, old_hex, new_hex, _ in gm.PATCHES:
            self.assertEqual(bytes(self.synthetic[offset:offset + len(bytes.fromhex(old_hex))]), bytes.fromhex(old_hex))
            self.assertEqual(patched[offset:offset + len(bytes.fromhex(new_hex))], bytes.fromhex(new_hex))
        self.assertEqual([i for i, (a, b) in enumerate(zip(self.synthetic, patched)) if a != b], list(changed))

    def test_rejects_wrong_bytes(self):
        self.synthetic[0x1386] ^= 0x01
        with self.assertRaisesRegex(ValueError, "Unexpected bytes"):
            gm.patch_application(bytes(self.synthetic))

    def test_rejects_wrong_length(self):
        with self.assertRaises(ValueError):
            gm.patch_application(bytes(self.synthetic[:-1]))

    def test_public_build_rejects_synthetic_firmware(self):
        fake_full = bytes(self.synthetic) + bytes([0] * (gm.FULL_SIZE - gm.APP_SIZE))
        with self.assertRaisesRegex(ValueError, "Unsupported firmware revision"):
            gm.build(fake_full)

    def test_hashes_are_well_formed(self):
        for value in (gm.STOCK_APP_SHA256, gm.PATCHED_APP_SHA256, gm.STOCK_FULL_SHA256):
            self.assertEqual(len(value), 64)
            self.assertTrue(all(ch in '0123456789abcdef' for ch in value))
        self.assertEqual(len(gm.BOOTLOADER_MD5), 32)

    def test_rejects_forged_header_short_dump(self):
        with self.assertRaisesRegex(ValueError, "Expected a 65536-byte"):
            gm.inspect_dump(bytes([0] * gm.APP_SIZE))


if __name__ == "__main__":
    unittest.main()
