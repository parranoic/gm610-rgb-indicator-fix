# Technical notes — GM610 RGB indicator fix and Fn+B status overlay (v1.2)

This project changes **one specific firmware revision** from a 65,536-byte `sinowisp` ISP readout of a Newmen GM610. The original firmware source code is unavailable. Names assigned to routines or variables are reverse-engineering descriptions, not vendor symbols.

## Hardware and protocol

- Normal USB VID:PID: `12C9:6001`.
- ISP bootloader VID:PID: `0603:1020`.
- Main controller: marking `BYK916`, identified with the SinoWealth SH68F90A family (8051-compatible).
- Wireless controller: `BK3632` (not modified).
- Known ISP bootloader MD5: `2d169670eae0d36eae8188562c1f66e8`.
- ISP readout layout: 61,440-byte application (`0x0000–0xEFFF`) plus 4,096-byte bootloader (`0xF000–0xFFFF`).
- Application reset vector in readout: `02 6F 0B` (`LJMP 0x6F0B`).
- The manufacturer's downloadable firmware was **not** the same revision as the installed image. These offsets must not be used with another image.

## Five instruction edits, nine modified bytes

All offsets below refer to the 61,440-byte **`sinowisp` application readout**, not guaranteed physical flash addresses. The instruction replacements have the same lengths as the originals.

| Offset | Original bytes | v1.0 Fn → Tab | v1.1 Fn → Enter (default) | Description |
| --- | --- | --- | --- | --- |
| `0x1385` | `90 0A 5E` | `90 0A 8E` | `90 0A AF` | Fn red `MOV DPTR,#RGB_ADDRESS` |
| `0x139E` | `90 0A 5F` | `90 0B 0C` | `90 0B 2D` | Fn green |
| `0x13BB` | `90 0A 60` | `90 0B 8A` | `90 0B AB` | Fn blue |
| `0x1420` | `70 38` | `80 38` | `80 38` | Tab status-color bypass, `JNZ +0x38` → `SJMP +0x38` |
| `0x4E7E` | `75 F0 05` | `85 19 F0` | `85 19 F0` | Indicator brightness multiplier follows byte `0x19` |

A v1.1 Enter application differs from the original v1.0 Tab application at **only three bytes**: `0x1387`, `0x13A0`, and `0x13BD`.

### RGB LED indices

The three observed framebuffer color planes start at:

- Red: `0x0A64`
- Green: `0x0AE2`
- Blue: `0x0B60`

Each plane has 126 (`0x7E`) positions. The Tab index is `0x2A` (42). The Enter index `0x4B` (75) was inferred from the scan layout and subsequently **confirmed by user testing on the actual GM610** on 1 November 2026.

Adding these indices to the plane bases gives:

| Fn reference | Red | Green | Blue |
| --- | --- | --- | --- |
| Tab (`0x2A`) | `0x0A8E` | `0x0B0C` | `0x0B8A` |
| Enter (`0x4B`) | `0x0AAF` | `0x0B2D` | `0x0BAB` |

The Tab status-color branch ends at `0x145A` (`0x1420 + 2 + 0x38`). The Fn indicator previously used a fixed multiplier of 5; the regular lighting path uses the brightness variable at direct address `0x19`. Both variants use the same brightness patch.

**Caveat:** Fn copies the referenced key's framebuffer color; it does not acquire an independent physical key mapping. The Enter match was confirmed by a user on one keyboard, but every animation, profile, wireless state and device revision has **not** been exhaustively tested.

## Firmware fingerprints

| Image | Length | SHA-256 / MD5 |
| --- | --- | --- |
| Full stock ISP readout | 65,536 | SHA-256 `3d87778be5534dc5018bd8662335af7efdee04bb64a297cb2f09adf4b2fa6836` |
| Stock application segment | 61,440 | SHA-256 `8b5e410ca8c65897f23f560fc86688831f533c684a575e5f2e9c5da363006bca` |
| **Fn → Enter (v1.1 default)** | **61,440** | **SHA-256 `314e2292fb083533b82cecd824f37d087e3a1d259f1fa39859a828b202bdf583`** |
| Fn → Tab (v1.0 option) | 61,440 | SHA-256 `4f16f98a24f1f622f304298dd02697472bb58869c4682bc92f7960be10abd30b` |
| Bootloader segment | 4,096 | MD5 `2d169670eae0d36eae8188562c1f66e8` |

The patcher requires a byte-identical stock application and recognized bootloader, verifies the instructions at all five sites, checks that exactly nine bytes changed, and verifies the output SHA-256. This is **not** evidence that a different GM610 revision is compatible.

## v1.2: battery-status display (hardware-tested on one GM610)

The earlier nine-byte v1.1 Fn → Enter image is still the base. The v1.2 application adds reconstructed 8051 machine-code routines into verified zero-filled application space; it is **not** a nine-byte-only patch. These are **application-readout offsets**, not guaranteed physical flash addresses.

| Site | Effect |
| --- | --- |
| `0x0DC0` | Replace `MOV DPTR,#0DD0h` with `LCALL 0x9000`; key hook executes displaced instruction and returns |
| `0x8536` | Replace call to `0x7C3F` with call to `0x9020`; initialization hook retains original call and clears the overlay timer |
| `0x4E88` | Enter 8051 hook at `0x9040` from the common LED-output path; preserve displaced comparison/carry before returning |
| `0x9000` | Scan handler: when Fn (bit `33h`) is held and matrix index `34` (B) is scanned, load the temporary countdown into XDATA `0x0E30` |
| `0x9020` | Startup timer initialization |
| `0x9040` | PWM-output overlay for number-row indices `0x16–0x1F`; uses battery nibble in XDATA `0x0E05` |
| `0x90C3–0x90D2` | 16-byte lookup table: `0,2,2,2,4,4,6,8,8,10,10,10,10,10,10,10` |
| `0x906D` | `JZ` displacement `0x32` skips the color override for level zero/unavailable; originally `0x18` in the preceding experimental build |

**Behavioral limits:** These represent the original firmware's coarse battery-status bands, **not** accurate 10% steps. The tested Bluetooth mode showed all ten green LEDs when Windows reported 100%. The tested wired-USB mode supplied a zero/unavailable battery value; Fn+B left the existing color profile unchanged. This is not an explicit USB-mode check. Future wireless states could behave differently. Timeout uses 120 LED update passes, not a verified wall-clock duration.

**Important testing history:** Initial v1.2–v1.3 experimental hooks did not trigger due to incorrect matrix-index assumptions; v1.4 corrected B index 34; v1.5 matched the stock battery bands; private v1.6 suppressed the zero-status overlay. **Public v1.2.0 is based only on the final v1.6 candidate that the user confirmed working.** Tests run an intentionally limited 8051 interpreter and do not emulate hardware interrupts, timings or LED electronics.

| v1.2 built application | Length | SHA-256 |
| --- | --- | --- |
| Fn → Enter + Fn+B | 61,440 bytes | `e8d9991bbc20bc7dff46ecb6d80c74c84b28c004ba777adc1fd6d74ed04da712` |

The public `battery_overlay.py` requires the exact v1.1 Enter application as input, then verifies the final v1.2 SHA-256. Unsupported source firmware is rejected before patching. This is **not** a bootloader patch; only the 60 KiB application should be flashed.

## ISP entry observed on test keyboard

The application exposed five vendor-defined HID collections with usage page `FF00`. The relevant collection in the test was `Col03`, feature report ID `0x05`, five payload bytes. Sending `05 75 00 00 00 00` caused a transition from `12C9:6001` to `0603:1020`.

The Windows HID path contains computer-specific instance values and must be discovered locally. Windows returned `HidD_SetFeature` error `0x1F` during disconnect; the subsequent `0603:1020` enumeration, **not the error itself**, confirmed entry.

## What was tested

- **Hardware, one GM610:** Fn → Tab + Tab indicator fix worked on 31 October 2026; Fn → Enter + same Tab fix worked on 1 November 2026, as confirmed by its owner.
- **Offline:** Both images recreated from the same 65,536-byte stock dump. Only nine bytes differ from stock in either variant, and the three-byte difference between variants matches the documented offsets. Expected SHA-256 fingerprints match both hardware-tested outputs.
- **Unverified:** Recovery after a completely corrupted application; external programming pad/pin mapping; other firmware revisions; comprehensive lighting effects and edge conditions.

A `sinowisp` readout may involve boot-control and reset-vector transformations; it is **not guaranteed to be a raw physical-flash dump**. Never flash the full 65,536-byte readout as the 61,440-byte application. See [RECOVERY.md](RECOVERY.md).

## References

- [`sinowisp`](https://github.com/karstx/sinowisp)
- [`hidapitester`](https://github.com/todbot/hidapitester)
