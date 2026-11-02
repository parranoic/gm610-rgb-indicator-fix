#!/usr/bin/env python3
"""Offline GM610 RGB indicator patcher for one verified firmware revision.

Default (v1.2): Fn follows Enter and Fn+B displays battery status bands.
Pass --no-battery for RGB-only v1.1; combine with --fn-source tab for v1.0.
Uses only the Python standard library. Never communicates with USB hardware.
This tool intentionally refuses unknown application and bootloader images.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys

from battery_overlay import inject_battery_overlay, V12_HASH

APP_SIZE = 0xF000       # 61,440 bytes
FULL_SIZE = 0x10000     # 65,536 bytes
STOCK_APP_SHA256 = "8b5e410ca8c65897f23f560fc86688831f533c684a575e5f2e9c5da363006bca"
STOCK_FULL_SHA256 = "3d87778be5534dc5018bd8662335af7efdee04bb64a297cb2f09adf4b2fa6836"
BOOTLOADER_MD5 = "2d169670eae0d36eae8188562c1f66e8"
PATCHED_APP_SHA256 = {
    "enter": "314e2292fb083533b82cecd824f37d087e3a1d259f1fa39859a828b202bdf583",
    "tab": "4f16f98a24f1f622f304298dd02697472bb58869c4682bc92f7960be10abd30b",
}
DEFAULT_FN_SOURCE = "enter"
LED_INDEX = {"tab": 0x2A, "enter": 0x4B}
RGB_PLANES = (0x0A64, 0x0AE2, 0x0B60)
FN_DPTR_OFFSETS = (0x1385, 0x139E, 0x13BB)
STOCK_INDICATOR_ADDRESSES = (0x0A5E, 0x0A5F, 0x0A60)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def md5(data: bytes) -> str:
    # MD5 only identifies a known bootloader variant; not used for authentication.
    return hashlib.md5(data).hexdigest()


def patches_for(fn_source: str = DEFAULT_FN_SOURCE) -> tuple[tuple[int, str, str, str], ...]:
    """Return five same-length instruction edits for the selected Fn key."""
    if fn_source not in LED_INDEX:
        raise ValueError(f"Unsupported Fn source {fn_source!r}; choose enter or tab")
    index = LED_INDEX[fn_source]
    edits = []
    for offset, old_addr, plane, channel in zip(
        FN_DPTR_OFFSETS, STOCK_INDICATOR_ADDRESSES, RGB_PLANES, ("red", "green", "blue")
    ):
        new_addr = plane + index
        edits.append((
            offset,
            f"90 {old_addr >> 8:02X} {old_addr & 0xFF:02X}",
            f"90 {new_addr >> 8:02X} {new_addr & 0xFF:02X}",
            f"Fn {channel} -> normal {fn_source.title()} pixel",
        ))
    edits.extend((
        (0x1420, "70 38", "80 38", "Tab bypasses status-color override"),
        (0x4E7E, "75 F0 05", "85 19 F0", "Indicator brightness follows global value"),
    ))
    return tuple(edits)


# Backwards-compatible read-only constant for users importing the module.
PATCHES = patches_for()


def inspect_dump(full: bytes) -> dict[str, str | int | bool]:
    """Calculate compatibility fingerprints; does not modify data."""
    if len(full) != FULL_SIZE:
        raise ValueError(
            f"Expected a {FULL_SIZE}-byte full sinowisp readout; got {len(full)} bytes. "
            "Do not use a vendor EXE or a 60 KiB application here."
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
        raise ValueError("Unsupported firmware revision: application SHA-256 differs. No patch generated.")
    if not info["matches_known_bootloader"]:
        raise ValueError("Bootloader fingerprint differs from the tested unit. No patch generated.")
    return full[:APP_SIZE]


def patch_application(
    stock_app: bytes, fn_source: str = DEFAULT_FN_SOURCE
) -> tuple[bytes, tuple[int, ...]]:
    """Perform instruction-checked edits; callers must validate the full dump first.

    This lower-level function is also used for synthetic offline unit tests.
    """
    if len(stock_app) != APP_SIZE:
        raise ValueError(f"Expected {APP_SIZE}-byte application; got {len(stock_app)}")
    edits = patches_for(fn_source)
    out = bytearray(stock_app)
    allowed_changed = set()
    for offset, old_hex, new_hex, label in edits:
        old, new = bytes.fromhex(old_hex), bytes.fromhex(new_hex)
        if len(old) != len(new) or out[offset:offset + len(old)] != old:
            raise ValueError(f"Unexpected bytes at 0x{offset:04X} ({label}); refusing to patch")
        out[offset:offset + len(new)] = new
        allowed_changed.update(offset + i for i, (a, b) in enumerate(zip(old, new)) if a != b)
    changed = tuple(i for i, (a, b) in enumerate(zip(stock_app, out)) if a != b)
    if len(changed) != 9 or set(changed) != allowed_changed:
        raise AssertionError("Patch unexpectedly changed bytes outside the approved nine")
    if out[0x1420:0x1422] != bytes.fromhex("80 38") or 0x1420 + 2 + 0x38 != 0x145A:
        raise AssertionError("Tab branch target mismatch")
    if out[0x4E7E:0x4E81] != bytes.fromhex("85 19 F0"):
        raise AssertionError("Brightness instruction mismatch")
    for offset, plane in zip(FN_DPTR_OFFSETS, RGB_PLANES):
        address = plane + LED_INDEX[fn_source]
        if out[offset:offset + 3] != bytes((0x90, address >> 8, address & 0xFF)):
            raise AssertionError(f"Fn {fn_source} framebuffer address mismatch at 0x{offset:04X}")
    return bytes(out), changed


def build(
    full: bytes, fn_source: str = DEFAULT_FN_SOURCE
) -> tuple[bytes, bytes, tuple[int, ...]]:
    stock = validate_stock(full)
    patched, changed = patch_application(stock, fn_source)
    if sha256(patched) != PATCHED_APP_SHA256[fn_source]:
        raise AssertionError("Patched SHA-256 differs from the hardware-tested variant")
    return stock, patched, changed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    inspect_cmd = commands.add_parser("inspect", help="Print compatibility fingerprints (offline)")
    inspect_cmd.add_argument("full_dump", type=Path)
    patch_cmd = commands.add_parser("patch", help="Generate modified application + private rollback image")
    patch_cmd.add_argument("full_dump", type=Path)
    patch_cmd.add_argument("--fn-source", choices=tuple(LED_INDEX), default=DEFAULT_FN_SOURCE)
    patch_cmd.add_argument("--output-dir", type=Path, default=Path("local-output"))
    patch_cmd.add_argument("--no-battery", action="store_true", help="Generate RGB-only v1.1 (or v1.0 with --fn-source tab)")
    verify_cmd = commands.add_parser("verify", help="Compare a local patch to a verified reference variant")
    verify_cmd.add_argument("full_dump", type=Path)
    verify_cmd.add_argument("patched_application", type=Path)
    verify_cmd.add_argument("--fn-source", choices=tuple(LED_INDEX), default=DEFAULT_FN_SOURCE)
    verify_cmd.add_argument("--no-battery", action="store_true", help="Verify RGB-only v1.1 or v1.0 instead of battery v1.2")
    args = parser.parse_args(argv)
    try:
        full = args.full_dump.read_bytes()
        if args.command == "inspect":
            for key, value in inspect_dump(full).items():
                print(f"{key}: {value}")
            return 0
        stock, base_image, base_changes = build(full, args.fn_source)
        battery = not args.no_battery
        if battery and args.fn_source != "enter":
            raise ValueError("The battery overlay is hardware-tested only with Fn -> Enter. Use --no-battery with --fn-source tab.")
        if battery:
            patched, battery_changes = inject_battery_overlay(base_image)
            changed = tuple(i for i, (a, b) in enumerate(zip(stock, patched)) if a != b)
            output_name = "gm610_fn_enter_battery_v1_2.bin"
            variant = "v1.2 Fn -> Enter + Fn+B status bands"
        else:
            patched, changed = base_image, base_changes
            output_name = f"gm610_rgb_{args.fn_source}_patched.bin"
            variant = f"RGB-only Fn -> {args.fn_source.title()}"
        if args.command == "verify":
            candidate = args.patched_application.read_bytes()
            if candidate != patched:
                raise ValueError(f"Candidate differs from the expected {variant} image")
            print(f"PASS: candidate matches the verified {variant} image")
            print("SHA-256:", sha256(candidate))
            return 0
        if args.command == "patch":
            args.output_dir.mkdir(parents=True, exist_ok=True)
            patched_file = args.output_dir / output_name
            rollback_file = args.output_dir / "gm610_stock_application.bin"
            if patched_file.exists():
                raise FileExistsError(f"Output already exists: {patched_file}. Move or rename it first.")
            if rollback_file.exists() and rollback_file.read_bytes() != stock:
                raise FileExistsError(f"Existing rollback image differs: {rollback_file}. Stop and investigate.")
            patched_file.write_bytes(patched)
            if not rollback_file.exists():
                rollback_file.write_bytes(stock)
            print(f"Generated {patched_file} ({len(patched)} bytes)")
            print(f"Rollback image: {rollback_file} ({len(stock)} bytes; KEEP PRIVATE)")
            print(f"Build: {variant}; Tab uses its own RGB color")
            print(f"Modified byte count vs stock: {len(changed)}")
            print("Patched SHA-256:", sha256(patched))
            print("No USB access or flashing was performed.")
            return 0
    except (OSError, ValueError, AssertionError, KeyError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
