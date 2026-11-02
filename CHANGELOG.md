# Changelog

## v1.2.0 — 2026-11-02

- Added **Fn+B**: temporarily displays the battery's approximate 20/40/60/80/100 *indicator bands* as 2/4/6/8/10 green number-row LEDs in Bluetooth mode.
- **Zero or unavailable battery data** produces **no overlay**. Confirmed on one GM610 in wired USB mode; this is a data-value check, not a USB-mode detection algorithm.
- Kept the v1.1 Fn → Enter and Tab RGB corrections.
- New default `patch` and `verify` output is the **hardware-tested v1.2** image (SHA-256 `e8d9991bbc20bc7dff46ecb6d80c74c84b28c004ba777adc1fd6d74ed04da712`).
- Use `--no-battery` for the v1.1 RGB-only Enter variant, or `--no-battery --fn-source tab` for the v1.0 Tab variant.
- Adds `battery_overlay.py` with exact input/output hash gating, a reproducible reconstructed 8051 hook, and firmware-free tests.
- A first attempt at Fn+B failed; earlier experimental versions were **not released**. This release reproduces the v1.6 private test image that the owner verified working on the physical keyboard.
- Still only one firmware revision/device tested. Firmware binaries and bootloader dumps are not distributed.

## v1.1.0 — 2026-11-01

- **Fn → Enter is now the default**: Fn copies Enter's normal RGB framebuffer values and follows the keyboard brightness setting.
- **Fn → Tab remains available** using `--fn-source tab`. This retains the original v1.0 result; no need for a separate experimental patch generator.
- Tab still follows its own normal RGB instead of showing red/blue connection-status colors.
- The patcher selects the appropriate nine-byte modification from a compatible **stock full ISP readout**, validates the output hash and preserves private rollback files.
- Added tests for both variants and documented their exact hashes, LED indices, and offsets.
- Tested by the project owner on **one** Newmen GM610. Other revisions and recovery after a failed flash are not verified.

**No proprietary firmware files are distributed.** The updated patcher only creates a modified image from a user's own matching backup.

## v1.0.0 — 2026-10-31

- Original nine-byte GM610 firmware patch: Fn mirrors **Tab**; Tab follows its normal RGB color; indicator brightness follows the global setting.
- Verified on one physical GM610 with SinoWealth family controller and `0603:1020` ISP bootloader.
