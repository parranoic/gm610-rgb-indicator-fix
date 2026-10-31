#!/usr/bin/env python3
"""Offline patch generator for one verified Newmen GM610 firmware revision.

Uses only the Python standard library. Never connects to a USB device.
This tool intentionally refuses unknown application or bootloader images.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys

APP_SIZE = 0xF000       # 61,440 bytes
FULL_SIZE = 0x10000     # 65,536 bytes
STOCK_APP_SHA256 = "8b5e410ca8c65897f23f560fc86688831f533c684a575e5f2e9c5da363006bca"
STOCK_FULL_SHA256 = "3d87778be5534dc5018bd8662335af7efdee04bb64a297cb2f09adf4b2fa6836"
BOOTLOADER_MD5 = "2d169670eae0d36eae8188562c1f66e8"
PATCHED_APP_SHA256 = "4f16f98a24f1f622f304298dd02697472bb58869c4682bc92f7960be10abd30b"

# (file offset, original bytes, replacement bytes, meaning)
# These are offsets in the 61,440-byte *sinowisp application readout*, not
# physical-flash addresses. The original and patched bytes have equal lengths.
PATCHES = (
    (0x1385, "90 0A 5E", "90 0A 8E", "Fn red -> normal Tab pixel"),
    (0x139E, "90 0A 5F", "90 0B 0C", "Fn green -> normal Tab pixel"),
    (0x13BB, "90 0A 60", "90 0B 8A", "Fn blue -> normal Tab pixel"),
    (0x1420, "70 38", "80 38", "Tab bypasses status-color override"),
    (0x4E7E, "75 F0 05", "85 19 F0", "Indicator brightness follows global value"),
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def md5(data: bytes) -> str:
    # MD5 is used only to identify the known bootloader version, not for security.
    return hashlib.md5(data).hexdigest()


def inspect_dump(full: bytes) -> dict[str, str | int | bool]:
    """Calculate fingerprints without making any changes."""
    if len(full) != FULL_SIZE:
        raise ValueError(
            f"Expected a {FULL_SIZE}-byte full sinowisp readout; got {len(full)} bytes. "
            "Do not use the manufacturer's updater EXE or a 60 KiB application here."
        )
    app, boot = full[:APP_SIZE], full[APP_SIZE:]
    return {
        "size": len(full),
        "full_sha256": sha256(full),
        "app_sha256": sha256(app),
        "boot_md5": md5(boot),
        "matches_stock_application": sha256(app) == STOCK_APP_SHA256,
        "matches_known_bootloader": md5(boot) == BOOTLOADER_MD5,
        "matches_original_unit_dump": sha256(full) == STOCK_FULL_SHA256,
    }


def validate_stock(full: bytes) -> bytes:
    info = inspect_dump(full)
    if not info["matches_stock_application"]:
        raise ValueError(
            "Unsupported firmware revision: application SHA-256 is not the tested stock version. "
            "No patch generated."
        )
    if not info["matches_known_bootloader"]:
        raise ValueError(
            "Bootloader fingerprint differs from the successfully tested unit. "
            "No patch generated."
        )
    return full[:APP_SIZE]


def patch_application(stock_app: bytes) -> tuple[bytes, tuple[int, ...]]:
    """Apply checked, same-length edits to an application image.

    Call validate_stock() before using this function with a real image.
    This lower-level function exists so structural tests can use synthetic data.
    """
    if len(stock_app) != APP_SIZE:
        raise ValueError(f"Expected {APP_SIZE}-byte application; got {len(stock_app)}")
    out = bytearray(stock_app)
    allowed_changed = set()
    for offset, old_hex, new_hex, label in PATCHES:
        old, new = bytes.fromhex(old_hex), bytes.fromhex(new_hex)
        if len(old) != len(new) or out[offset:offset + len(old)] != old:
            raise ValueError(f"Unexpected bytes at 0x{offset:04X} ({label}); refusing to patch")
        out[offset:offset + len(old)] = new
        allowed_changed.update(offset + i for i, (a, b) in enumerate(zip(old, new)) if a != b)

    changed = tuple(i for i, (a, b) in enumerate(zip(stock_app, out)) if a != b)
    if len(changed) != 9 or set(changed) != allowed_changed:
        raise AssertionError("Patch unexpectedly changed bytes outside the approved nine")
    if out[0x1420:0x1422] != bytes.fromhex("80 38") or 0x1420 + 2 + 0x38 != 0x145A:
        raise AssertionError("Tab branch target mismatch")
    if tuple(out[p:p+3] for p in (0x1385, 0x139E, 0x13BB)) != (
        bytes.fromhex("90 0A 8E"), bytes.fromhex("90 0B 0C"), bytes.fromhex("90 0B 8A")
    ):
        raise AssertionError("Fn framebuffer addresses mismatch")
    return bytes(out), changed


def build(full: bytes) -> tuple[bytes, bytes, tuple[int, ...]]:
    stock = validate_stock(full)
    patched, changes = patch_application(stock)
    if sha256(patched) != PATCHED_APP_SHA256:
        raise AssertionError("Patched SHA-256 does not match the known working image")
    return stock, patched, changes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    inspect_cmd = commands.add_parser("inspect", help="Print compatibility fingerprints (read-only)")
    inspect_cmd.add_argument("full_dump", type=Path)
    patch_cmd = commands.add_parser("patch", help="Generate patched and rollback applications locally")
    patch_cmd.add_argument("full_dump", type=Path)
    patch_cmd.add_argument("--output-dir", type=Path, default=Path("local-output"))
    verify_cmd = commands.add_parser("verify", help="Verify a generated patch against a full stock dump")
    verify_cmd.add_argument("full_dump", type=Path)
    verify_cmd.add_argument("patched_application", type=Path)
    args = parser.parse_args(argv)

    try:
        full = args.full_dump.read_bytes()
        if args.command == "inspect":
            for key, value in inspect_dump(full).items():
                print(f"{key}: {value}")
            return 0
        stock, patched, changed = build(full)
        if args.command == "verify":
            candidate = args.patched_application.read_bytes()
            if candidate != patched:
                raise ValueError("Candidate differs from the known-good nine-byte patch")
            print("PASS: candidate exactly matches the known working patch")
            print("SHA-256:", sha256(candidate))
            return 0
        if args.command == "patch":
            args.output_dir.mkdir(parents=True, exist_ok=True)
            patched_file = args.output_dir / "gm610_rgb_patched.bin"
            rollback_file = args.output_dir / "gm610_stock_application.bin"
            # Refuse to silently overwrite previous outputs.
            for file in (patched_file, rollback_file):
                if file.exists():
                    raise FileExistsError(f"Output already exists: {file}. Rename/move it first.")
            patched_file.write_bytes(patched)
            rollback_file.write_bytes(stock)
            print(f"Generated {patched_file} ({len(patched)} bytes)")
            print(f"Generated {rollback_file} ({len(stock)} bytes; PRIVATE rollback backup)")
            print(f"Nine changed bytes at: {', '.join(f'0x{x:04X}' for x in changed)}")
            print("Patched SHA-256:", sha256(patched))
            print("No USB access or flashing was performed.")
            return 0
    except (OSError, ValueError, AssertionError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
