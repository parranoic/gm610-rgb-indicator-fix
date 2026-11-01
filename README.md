# Newmen GM610 — Fn / Tab RGB indicator fix

A **nine-byte firmware patch** for a specific Newmen GM610 keyboard firmware revision. It makes the always-on status LEDs behave like normal keyboard lighting:

- **Fn:** no longer displays a permanently different battery-status color. By default it mirrors **Enter's normal RGB framebuffer color** and follows global brightness. The original **Fn → Tab** option is still available.
- **Tab:** no longer forces blue/red wireless connection status colors. It displays its own configured RGB color.
- Both Fn → Tab (31 October 2026) and Fn → Enter (1 November 2026) were **tested successfully on one physical GM610**. This is not general compatibility certification or proof every lighting effect works.

**This project was vibe-coded:** the reverse engineering, patch generator, and test code were created with AI assistance, with human-directed experimentation and a real-device test. There has been no formal code audit. Treat the scripts and offsets as experimental even though the specific result worked on one unit.

> [!CAUTION]
> **Risk of permanently bricking your keyboard.** Flashing can fail, interrupt power, destroy application firmware, or leave the device unable to re-enter its ISP bootloader. **You perform every action entirely at your own risk.** The author/contributors accept no responsibility or liability for damage, lost data, broken devices, or any other consequences. The code is provided **AS IS, without warranty**; this notice is not a guarantee of legal immunity.
>
> **The patcher only works with a *byte-identical supported application revision* and the known bootloader.** Another GM610, even with the same model name, may have incompatible firmware. **Never bypass the hash checks.**

## v1.1 — Fn now follows Enter by default

- **New default:** Fn uses the RGB color of **Enter**, confirmed on a real GM610 on 1 November 2026.
- **Original option retained:** add `--fn-source tab` to generate the earlier Fn → Tab version.
- **Unchanged:** Tab uses its own color, and both variants preserve the brightness adjustment.
- **No new firmware versions supported:** the same stock application and bootloader hashes are required. See [technical details](docs/TECHNICAL.md) and [release notes](CHANGELOG.md).

## TL;DR — what this does and how to use it

**What it fixes:** On the GM610, **Fn** normally displays a battery-status color (often white), and **Tab** displays blue/red wireless status colors. This nine-byte patch makes **Tab use its normal RGB setting**, while **Fn copies Enter's color** (or Tab's if selected). Both follow brightness settings. The battery/connection LED colors are intentionally hidden; keyboard input still works on the tested unit.

**Quick start (Windows):**

1. **Know the risk:** This can permanently brick the keyboard. It has worked on **one** GM610, not every GM610. Keep another keyboard handy.
2. **Get ready:** Install Python 3.11+ and download [`hidapitester`](https://github.com/todbot/hidapitester/releases) and [`sinowisp`](https://github.com/karstx/sinowisp/releases). Connect the GM610 by USB.
3. **Enter firmware-update mode:** Follow [Step 2](#2-enter-isp-mode-active-device-command) to find the correct HID interface and send the tested entry command. **Confirm the USB ID changes from `12C9:6001` to `0603:1020`** before continuing.
4. **Save your original firmware:** Follow [Step 3](#3-back-up-your-own-original-firmware) to make a **private 65,536-byte backup** using `sinowisp`. A read is not completely non-invasive. Keep an extra copy somewhere safe.
5. **Make the patch:** Open PowerShell in the folder containing the script and your backup, then run:

   ```powershell
   py -3 .\patch_gm610.py inspect .\private\gm610_stock_full.bin
   py -3 .\patch_gm610.py patch .\private\gm610_stock_full.bin
   py -3 .\patch_gm610.py verify .\private\gm610_stock_full.bin .\local-output\gm610_rgb_enter_patched.bin
   ```

   **If the script says your firmware or bootloader doesn't match, STOP.** Do not bypass its checks.
6. **Flash and check:** Follow [Step 5](#5-flash-the-patched-application) to write **only** `local-output/gm610_rgb_enter_patched.bin` (the **61,440-byte application**, **not** the full backup). Reconnect the keyboard, check it types, and test **per-key colors or rainbow mode** to confirm Fn follows Enter.

To keep the older **Fn → Tab** behavior instead, use `--fn-source tab` with the `patch` and `verify` commands in [Step 4](#4-check-compatibility-and-generate-your-patch-offline).

If something goes wrong, see [Recovery and rollback](docs/RECOVERY.md). **There is no guaranteed way to recover a GM610 that no longer enters update mode.** For exact commands and safety checks, follow the [full step-by-step guide](#step-by-step); this summary is not a substitute for it.

## Compatibility: what was actually tested

| Item | Observation |
| --- | --- |
| Keyboard | Newmen GM610, wired USB mode |
| Main MCU marking | `BYK916` (SinoWealth SH68F90A family) |
| Separate wireless chip | Beken `BK3632` (not modified) |
| Normal USB ID | `12C9:6001` |
| ISP / bootloader USB ID | `0603:1020` |
| ISP bootloader MD5 | `2d169670eae0d36eae8188562c1f66e8` |
| Stock application SHA-256 | `8b5e410ca8c65897f23f560fc86688831f533c684a575e5f2e9c5da363006bca` |
| **v1.1 Fn → Enter SHA-256 (default)** | `314e2292fb083533b82cecd824f37d087e3a1d259f1fa39859a828b202bdf583` |
| v1.0 Fn → Tab SHA-256 (option) | `4f16f98a24f1f622f304298dd02697472bb58869c4682bc92f7960be10abd30b` |
| Flash layout | 61,440-byte application + 4,096-byte ISP bootloader |
| Confirmed result | Both Fn → Enter and Fn → Tab work on **one** physical keyboard; Tab uses its own RGB color |
| Not established | Hardware recovery when application firmware is corrupt; other revisions; all animation effects |

**Not** a generic GM610 custom firmware, a wireless-chip patch, a Newmen software mod, or a mod of the firmware embedded in the manufacturer's downloadable updater. The latter was found to be **different** from the firmware on the successfully modified keyboard. Firmware versions were not reliably labeled by the vendor; **hashes, not marketing names, determine compatibility**.

## What's in this repository

```text
patch_gm610.py              Offline patcher with Enter/Tab Fn reference choices
README.md                   Instructions, variants and risk warning
CHANGELOG.md                v1.1 changes and previous behavior
docs/TECHNICAL.md           Exact byte changes and reverse-engineering notes
docs/RECOVERY.md            Restoring stock firmware and limits of recovery
tests/test_patch_gm610.py   Offline structural tests
.github/workflows/tests.yml Automated tests that do NOT use firmware or hardware
.gitignore                  Prevents accidental committing of firmware dumps
LICENSE                     MIT license for this repository's scripts/docs only
```

**Firmware `.bin` files are deliberately NOT included.** Newmen/SinoWealth firmware is third-party proprietary material. This repository distributes the patch instructions and original tooling only; you must obtain a backup **from your own keyboard**. Never upload your full dump, bootloader, manufactured updater, or generated firmware to this repository or a GitHub issue.

## Requirements (Windows)

- A GM610 **matching the hashes above**. Do not assume yours matches.
- A spare keyboard, in case the GM610 stops working.
- A reliable wired USB connection; avoid hubs and power interruptions during flashing.
- Python 3.11+ (standard library only; no `pip install` needed).
- [`hidapitester`](https://github.com/todbot/hidapitester/releases) for selecting the application-mode HID collection.
- [`sinowisp`](https://github.com/karstx/sinowisp/releases) for backing up and writing SinoWealth firmware. The documented commands match sinowisp **v2.1.0**; check the CLI help when using other versions.

The two external tools are **not** included. Verify their downloads at their upstream project pages.

## Step-by-step

Open PowerShell in a folder with `sinowisp.exe`, `hidapitester.exe` and this repository's `patch_gm610.py`, or adjust the paths accordingly. **Do not execute any firmware command if you are unsure which keyboard is selected.**

### 1. Confirm normal USB mode

Connect the GM610 by USB in wired mode:

```powershell
Get-PnpDevice -PresentOnly | Where-Object {
    $_.InstanceId -match 'VID_12C9&PID_6001'
} | Select-Object FriendlyName, InstanceId
```

Seeing `12C9:6001` indicates normal firmware enumeration; it does **not** prove the firmware revision matches. If you have multiple keyboards plugged in, distinguish the GM610 by VID/PID.

### 2. Enter ISP mode (active device command)

Find the vendor-defined `Col03` interface **for `12C9:6001`**:

```powershell
.\hidapitester.exe --vidpid 12C9:6001 --usagePage FF00 --list-detail
```

On the successfully modified keyboard, `Col03` had report ID `0x05` and a **5-byte payload** (six bytes including report ID). Check its descriptor before sending anything:

```powershell
# Replace with the actual Col03 path from YOUR --list-detail output.
$path = '<PASTE_THE_EXACT_Col03_PATH_HERE>'
.\hidapitester.exe --open-path $path --get-report-descriptor
```

The expected feature-report descriptor includes `85 05 ... 95 05 B1`. **Stop if the path/report does not match.** Then send the entry report that worked on the test keyboard:

```powershell
.\hidapitester.exe --open-path $path --length 6 --send-feature 0x05,0x75,0,0,0,0
Start-Sleep -Seconds 2
Get-PnpDevice -PresentOnly | Where-Object {
    $_.InstanceId -match 'VID_0603&PID_1020'
} | Select-Object FriendlyName, InstanceId
```

**Do not continue unless `0603:1020` is present.** On the test keyboard, `hidapitester` returned Windows error `0x1F` because the device disconnected immediately while switching to ISP; the new USB ID confirmed success. Error `0x1F` **alone does not prove success**.

### 3. Back up your own original firmware

Make a private backup directory (ignored by Git):

```powershell
New-Item -ItemType Directory -Force .\private | Out-Null
```

With the GM610 confirmed in ISP mode, capture the full application + bootloader **sinowisp readout**:

```powershell
.\sinowisp.exe read --platform sh68f90 --vendor_id 0x12C9 --product_id 0x6001 --firmware_size 61440 --bootloader_size 4096 --page_size 2048 --isp_iface_num 1 --isp_report_id 5 --reboot false --section full .\private\gm610_stock_full.bin
```

> [!WARNING]
> `sinowisp read` is **not completely non-invasive**. Its upstream documentation states that a read can set the application-enable opcode at `firmware_size - 5`, and that reset-vector bytes are relocated in the ISP readout. It is *not* a raw physical-flash image. Keep this backup privately and **never write the complete 65,536-byte dump as an application**.

Before flashing, copy your backup somewhere safe. On the tested unit, USB power-cycling after reading returned to normal `12C9:6001` operation; that is useful to verify, but **does not guarantee recovery from a later failed flash**.

### 4. Check compatibility and generate your patch (offline)

```powershell
py -3 .\patch_gm610.py inspect .\private\gm610_stock_full.bin
py -3 .\patch_gm610.py patch .\private\gm610_stock_full.bin
py -3 .\patch_gm610.py verify .\private\gm610_stock_full.bin .\local-output\gm610_rgb_enter_patched.bin
```

The script aborts if the application or bootloader fingerprint differs. **Do not remove this guard or force it to patch another revision.**

By default, `patch` makes **Fn follow Enter**. For the original Fn → Tab variant, run the following commands instead (the existing private backup can be reused):

```powershell
py -3 .\patch_gm610.py patch .\private\gm610_stock_full.bin --fn-source tab
py -3 .\patch_gm610.py verify .\private\gm610_stock_full.bin .\local-output\gm610_rgb_tab_patched.bin --fn-source tab
```

Each command is **offline** and only reads local firmware files. An existing output is never overwritten silently. The script creates local-only files inside ignored `local-output/`:

| Local file | Meaning |
| --- | --- |
| `gm610_rgb_enter_patched.bin` | **61,440-byte Fn → Enter patch (v1.1 default)** |
| `gm610_rgb_tab_patched.bin` | **61,440-byte Fn → Tab patch (if selected)** |
| `gm610_stock_application.bin` | **61,440-byte unmodified application**, for attempted ISP rollback |

Expected SHA-256: **Enter** `314e2292fb083533b82cecd824f37d087e3a1d259f1fa39859a828b202bdf583`; **Tab** `4f16f98a24f1f622f304298dd02697472bb58869c4682bc92f7960be10abd30b`. Both were tested on the same physical keyboard, not independently across different units.

Optional local unit tests (no device needed):

```powershell
py -3 -m unittest discover -s tests -v
```

### 5. Flash the patched application

Reconnect/re-enter ISP mode using step 2 if necessary. Check that the device is showing `0603:1020` **immediately before writing**. Then:

```powershell
.\sinowisp.exe write --platform sh68f90 --vendor_id 0x12C9 --product_id 0x6001 --firmware_size 61440 --bootloader_size 4096 --page_size 2048 --isp_iface_num 1 --isp_report_id 5 --reboot false .\local-output\gm610_rgb_enter_patched.bin
```

**This writes flash.** Do not disconnect USB, do not flash the **65,536-byte** dump, and do not retry blindly after an error. Stop and read [RECOVERY.md](docs/RECOVERY.md) if anything fails.

### 6. Confirm behavior

After a completed write, power-cycle the GM610. Confirm it enumerates as `12C9:6001`, types normally, and has working Bluetooth/2.4 GHz as applicable. Check Fn, Tab, and the rest of the keys at multiple brightness levels. For Fn → Enter, also test **per-key colors or a multi-color effect**, because a uniform solid color cannot distinguish the chosen reference key. Normal Fn battery indication and Tab connection-status colors are intentionally hidden by the patch.

### Revert to stock

If the keyboard still enters ISP mode and you have its original matching backup, re-run the `sinowisp write` command above **with the final filename changed** to:

```text
.\local-output\gm610_stock_application.bin
```

See [RECOVERY.md](docs/RECOVERY.md) for the command and the limitations of this rollback.

## Known limitations

- Fn mirrors **Enter** (default) or **Tab** (optional), not its own independent RGB pixel. Both choices were tested on one keyboard; all animations and wireless states are not exhaustively validated.
- **Battery/connection indicator colors are suppressed visually.** Battery reporting and radio control were not intentionally removed.
- A shared brightness helper is patched; other callers could be affected, and not every effect or edge case has been tested.
- Another GM610 revision can have completely different offsets, even if the PCB looks similar. The program will refuse unknown hashes.
- This is **not QMK/VIA/Vial**, and there is no universal firmware installer or guaranteed unbricking procedure.

## Why this is source-only

The script modifies a locally supplied firmware readout using five in-place instruction edits (nine byte values total). It **does not contain or fetch** the vendor's firmware or call `sinowisp` itself. The code can be inspected or tested without owning the keyboard, but creating the flashable image requires a matching, privately obtained full readout.

## Credits and sources

- [`sinowisp`](https://github.com/karstx/sinowisp): essential open-source SinoWealth ISP read/write and documented bootloader behavior.
- [`hidapitester`](https://github.com/todbot/hidapitester): HID descriptor inspection and ISP-entry report transmission.
- SinoWealth 8051 / SH68F90A family information and bootloader fingerprints from `sinowisp` documentation.
- Patch research and test instructions were developed through **AI-assisted (vibe-coded)** reverse engineering, then **one user tested both Fn → Tab and Fn → Enter variants on a real Newmen GM610** and confirmed the desired behavior.

**Not affiliated with, sponsored by, or endorsed by Newmen, SinoWealth, Beken, or the external tool authors.** The MIT license covers this repository's original code and documentation, **not** vendor firmware or third-party applications.

