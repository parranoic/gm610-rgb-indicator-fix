"""Offline unit tests; run without hardware, firmware, or external dependencies."""
import hashlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import patch_gm610 as gm


class GM610PatchTests(unittest.TestCase):
    def setUp(self):
        self.synthetic = bytearray([0xCC] * gm.APP_SIZE)
        for address, old_hex, _, _ in gm.patches_for("enter"):
            old = bytes.fromhex(old_hex)
            self.synthetic[address:address + len(old)] = old

    def test_both_variants_change_only_nine_bytes(self):
        for source in ("enter", "tab"):
            with self.subTest(source=source):
                patched, changed = gm.patch_application(bytes(self.synthetic), source)
                self.assertEqual(len(changed), 9)
                self.assertEqual(len(patched), gm.APP_SIZE)
                self.assertEqual(
                    [i for i, (a, b) in enumerate(zip(self.synthetic, patched)) if a != b],
                    list(changed),
                )
                for offset, old_hex, new_hex, _ in gm.patches_for(source):
                    self.assertEqual(
                        bytes(self.synthetic[offset:offset + len(bytes.fromhex(old_hex))]),
                        bytes.fromhex(old_hex),
                    )
                    self.assertEqual(patched[offset:offset + len(bytes.fromhex(new_hex))], bytes.fromhex(new_hex))

    def test_enter_is_default(self):
        default_image, _ = gm.patch_application(bytes(self.synthetic))
        enter_image, _ = gm.patch_application(bytes(self.synthetic), "enter")
        self.assertEqual(default_image, enter_image)

    def test_enter_differs_from_tab_at_exactly_three_bytes(self):
        enter, _ = gm.patch_application(bytes(self.synthetic), "enter")
        tab, _ = gm.patch_application(bytes(self.synthetic), "tab")
        diff = tuple(i for i, (a, b) in enumerate(zip(enter, tab)) if a != b)
        self.assertEqual(diff, (0x1387, 0x13A0, 0x13BD))
        self.assertEqual(enter[0x1420:0x1422], tab[0x1420:0x1422])
        self.assertEqual(enter[0x4E7E:0x4E81], tab[0x4E7E:0x4E81])

    def test_enter_addresses(self):
        enter, _ = gm.patch_application(bytes(self.synthetic), "enter")
        for offset, expected in ((0x1385, "90 0A AF"), (0x139E, "90 0B 2D"), (0x13BB, "90 0B AB")):
            self.assertEqual(enter[offset:offset + 3], bytes.fromhex(expected))

    def test_tab_addresses(self):
        tab, _ = gm.patch_application(bytes(self.synthetic), "tab")
        for offset, expected in ((0x1385, "90 0A 8E"), (0x139E, "90 0B 0C"), (0x13BB, "90 0B 8A")):
            self.assertEqual(tab[offset:offset + 3], bytes.fromhex(expected))

    def test_rejects_wrong_bytes_both_variants(self):
        self.synthetic[0x1386] ^= 1
        for source in ("enter", "tab"):
            with self.subTest(source=source), self.assertRaisesRegex(ValueError, "Unexpected bytes"):
                gm.patch_application(bytes(self.synthetic), source)

    def test_rejects_wrong_length(self):
        with self.assertRaisesRegex(ValueError, "Expected 61440-byte"):
            gm.patch_application(bytes(self.synthetic[:-1]))

    def test_rejects_bad_source(self):
        with self.assertRaisesRegex(ValueError, "Unsupported Fn source"):
            gm.patch_application(bytes(self.synthetic), "space")

    def test_public_build_rejects_synthetic_image(self):
        fake = bytes(self.synthetic) + bytes([0] * (gm.FULL_SIZE - gm.APP_SIZE))
        with self.assertRaisesRegex(ValueError, "Unsupported firmware revision"):
            gm.build(fake)

    def test_expected_hashes_well_formed(self):
        for value in (gm.STOCK_APP_SHA256, gm.STOCK_FULL_SHA256, *gm.PATCHED_APP_SHA256.values()):
            self.assertEqual(len(value), 64)
            self.assertTrue(all(c in "0123456789abcdef" for c in value))
        self.assertEqual(len(gm.BOOTLOADER_MD5), 32)

    def test_rejects_short_dump(self):
        with self.assertRaisesRegex(ValueError, "Expected a 65536-byte"):
            gm.inspect_dump(bytes([0] * gm.APP_SIZE))


if __name__ == "__main__":
    unittest.main()
