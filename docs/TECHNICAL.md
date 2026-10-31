# Technical notes — tested GM610 application revision

These observations come from one 65,536-byte **sinowisp ISP readout** of a Newmen GM610 and comparison of a successfully flashed nine-byte modification. The original vendor source code is unavailable. Function names below are descriptive, not original symbols.

## Hardware and protocol

- Keyboard normal USB VID:PID: `12C9:6001`.
- USB ISP bootloader VID:PID: `0603:1020`.
- Main controller marking: `BYK916`, associated with the SinoWealth SH68F90A family (8051-compatible).
- Separate wireless controller: `BK3632` (untouched by this patch).
- Known bootloader MD5: `2d169670eae0d36eae8188562c1f66e8`, also present in `sinowisp`'s supported-bootloader table.
- ISP readout: application `0x0000..0xEFFF` (61,440 bytes); bootloader `0xF000..0xFFFF` (4,096 bytes).
- Application entry bytes in the readout: `02 6F 0B` (`LJMP 0x6F0B`).
- The stock application in the vendor's download updater differs from this installed revision; its offsets **must not** be used with this image.

## Five code edits, nine changed bytes

All locations are **offsets in the 61,440-byte application readout** (not a promise about physical flash addresses). All edits preserve instruction lengths.

| Offset | Original | Patched | Interpretation |
| --- | --- | --- | --- |
| `0x1385` | `90 0A 5E` | `90 0A 8E` | Fn red `MOV DPTR,#0x0A5E` -> Tab normal-red pixel |
| `0x139E` | `90 0A 5F` | `90 0B 0C` | Fn green -> Tab normal-green pixel |
| `0x13BB` | `90 0A 60` | `90 0B 8A` | Fn blue -> Tab normal-blue pixel |
| `0x1420` | `70 38` | `80 38` | `JNZ +0x38` -> `SJMP +0x38`, always skip Tab status override |
| `0x4E7E` | `75 F0 05` | `85 19 F0` | `MOV B,#5` -> `MOV B,0x19` (brightness byte) |

### RGB framebuffer rationale

- The observed per-key planes begin at red `0x0A64`, green `0x0AE2`, blue `0x0B60` and are separated by 126 bytes (`0x7E`).
- The Tab LED index read in the application's status-related scan path is `0x2A` (42 decimal).
- Adding `0x2A` produces the addresses `0x0A8E`, `0x0B0C`, `0x0B8A`, which the patch uses for Fn.
- The Tab branch at `0x1420` jumps to `0x145A` after the patch (`0x1420 + 2 + 0x38`).
- In the identified regular RGB processing path, brightness comes from direct-address byte `0x19`; the indicator path previously used a hardcoded `5`.

These are reverse-engineered interpretations supported by instruction bytes and successful solid-color operation. They are **not** proof of correct behavior under every lighting animation, firmware setting, battery state, or wireless mode.

### Why no generic hex editing?

The updater-derived application had different code locations. Changing the same offsets in a different image could corrupt unrelated code. `patch_gm610.py` therefore requires both an exact SHA-256 fingerprint of the original installed application and the identified 4 KiB bootloader MD5. It verifies the original bytes at all five locations, the nine-byte diff, and the expected output SHA-256 before generating a file.

### Checksums (reference tested unit)

| Image | Length | Fingerprint |
| --- | --- | --- |
| Stock full ISP readout | 65,536 | SHA-256 `3d87778be5534dc5018bd8662335af7efdee04bb64a297cb2f09adf4b2fa6836` |
| Stock application segment | 61,440 | SHA-256 `8b5e410ca8c65897f23f560fc86688831f533c684a575e5f2e9c5da363006bca` |
| Patched application segment | 61,440 | SHA-256 `4f16f98a24f1f622f304298dd02697472bb58869c4682bc92f7960be10abd30b` |
| ISP bootloader segment | 4,096 | MD5 `2d169670eae0d36eae8188562c1f66e8` |

The full backup should remain private. `sinowisp` documents boot-control-byte and reset-vector transformations; a readout is **not** necessarily an exact raw physical-flash dump.

## USB HID ISP entry (observed)

The GM610 application exposed five vendor-defined usage-page `FF00` HID collections. The correct one in the test was `Col03`, report ID `0x05`, five payload bytes. The report `05 75 00 00 00 00` initiated a successful transition from `12C9:6001` to `0603:1020`.

The target collection path includes machine-specific Windows device-instance identifiers and **must not** be hard-coded in a public guide. Query it on the reader's machine using `hidapitester --list-detail` and confirm the feature report descriptor. The Windows `HidD_SetFeature` call returned an error in the test while the USB device disconnected and re-enumerated; the matching ISP USB ID established that the switch had actually happened.

## Verification scope

**Confirmed on hardware:** one GM610 successfully booted and the user reported Fn and Tab behaving exactly as intended after flashing this patched image.

**Confirmed offline:** input/app/bootloader hashes, five expected instruction sites, same-length instruction edits, nine changed bytes, identical reproduction of the known patched image.

**Not verified:** independent ISP entry if the application will not boot, external programmer pinout, all lighting animations, firmware revisions with different hashes, or a complete factory restoration after a failed flash.

## References

- `sinowisp` usage and caveats: https://github.com/karstx/sinowisp
- `hidapitester` CLI options: https://github.com/todbot/hidapitester
