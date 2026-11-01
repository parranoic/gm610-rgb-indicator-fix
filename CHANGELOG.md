# Changelog

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
