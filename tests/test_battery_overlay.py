"""Firmware-free 8051 hook tests. These are not physical keyboard tests."""
import hashlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import battery_overlay as overlay
import patch_gm610 as gm
from mini8051 import Mini8051


def simulate(level, led, channel, *, timer=120, brightness=5, bank=0):
    rom = bytearray(b"\x00" * gm.APP_SIZE)
    hook = overlay.led_hook()
    rom[0x9040:0x9040+len(hook)] = hook
    emulator = Mini8051(bytes(rom))
    emulator.pc = 0x9040
    emulator.x[0x0E05] = level
    emulator.x[0x0E30] = timer
    emulator.m[0x15] = led
    emulator.m[0x16] = channel
    emulator.m[0x14] = led % 21
    emulator.m[0x19] = brightness
    emulator.m[0x12] = 0x03
    emulator.m[0x13] = 0xAA
    emulator.m[0xD0] = bank << 3
    emulator.m[0xE0] = 0x13
    emulator.m[0xF0] = 0x37
    emulator.m[0x82] = 0x55
    emulator.m[0x83] = 0x66
    emulator.m[7] = 0x77
    emulator.run_until(0x4E8D)
    assert emulator.m[0x81] == 0x7B and emulator.m[7] == 0x77
    assert emulator.m[0xF0] == 0x37 and emulator.dptr() == 0x6655
    assert (emulator.m[0xD0] & 0x7F) == bank << 3
    return (emulator.m[0x12]<<8 | emulator.m[0x13], emulator.x[0x0E30])


class BatteryOverlayTests(unittest.TestCase):
    def test_level_table_is_sixteen_entries(self):
        self.assertEqual(len(overlay.LEVEL_TO_BARS), 16)
        self.assertEqual(overlay.LEVEL_TO_BARS, [0,2,2,2,4,4,6,8,8,10,10,10,10,10,10,10])

    def test_fn_b_uses_real_scan_index(self):
        k = overlay.key_hook()
        self.assertIn(bytes.fromhex("E5 08 B4 22"), k)
        self.assertEqual(overlay.B_MATRIX, 34)
        self.assertTrue(k.endswith(bytes.fromhex("90 0D D0 22")))

    def test_battery_zero_preserves_rgb_all_channels(self):
        for led in range(0x16,0x20):
            for channel in range(3):
                duty, _ = simulate(0,led,channel)
                self.assertEqual(duty, 0x03AA, (led,channel))

    def test_battery_zero_still_expires(self):
        self.assertEqual(simulate(0,0x16,0)[1], 119)
        self.assertEqual(simulate(0,0x16,1)[1], 120)
        self.assertEqual(simulate(0,0x17,0)[1], 120)
        self.assertEqual(simulate(0,0x16,0,timer=1)[1], 0)

    def test_highest_band_ten_green_keys(self):
        for led in range(0x16,0x20):
            self.assertEqual(simulate(10,led,1)[0], 255*5)
            self.assertEqual(simulate(10,led,0)[0], 0)
            self.assertEqual(simulate(10,led,2)[0], 0)

    def test_level_bands(self):
        for level, bars in enumerate(overlay.LEVEL_TO_BARS):
            for i in range(10):
                duty,_ = simulate(level, 0x16+i, 1)
                expected = 0x03AA if level==0 else (1275 if i<bars else 0)
                self.assertEqual(duty,expected,(level,i))

    def test_non_number_led_stays_normal(self):
        for level in (0,2,7,11,15):
            for ch in range(3):
                self.assertEqual(simulate(level,0x21,ch)[0],0x03AA)

    def test_brightness_and_register_banks(self):
        for bank in range(4):
            for brightness in range(1,6):
                self.assertEqual(simulate(15,0x16,1,brightness=brightness,bank=bank)[0],255*brightness)
                self.assertEqual(simulate(0,0x16,1,brightness=brightness,bank=bank)[0],0x03AA)

    def test_no_active_timer_does_nothing(self):
        self.assertEqual(simulate(15,0x16,1,timer=0)[0],0x03AA)

    def test_reject_wrong_v11_hash(self):
        with self.assertRaisesRegex(ValueError,'exact tested v1.1'):
            overlay.inject_battery_overlay(bytes(gm.APP_SIZE))

    def test_known_hash_and_code_cave_positions(self):
        for value in (overlay.V11_HASH,overlay.V12_HASH):
            self.assertEqual(len(value),64)
            int(value,16)
        key, init, led=overlay.key_hook(), overlay.init_hook(), overlay.led_hook()
        self.assertLessEqual(0x9000+len(key),0x9020)
        self.assertLessEqual(0x9020+len(init),0x9040)
        self.assertEqual(0x9040+len(led),0x90D3) # 16-byte status mapping ends at D3
        self.assertEqual(led[0x90C3-0x9040:0x90D3-0x9040],bytes(overlay.LEVEL_TO_BARS))


if __name__=='__main__': unittest.main()
