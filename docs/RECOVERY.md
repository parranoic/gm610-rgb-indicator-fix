# Recovery and rollback

## If the keyboard still works

Power-cycle it and verify normal USB VID:PID `12C9:6001`. If you want to undo the lighting patch, enter ISP using the method in the main README and restore **the 61,440-byte stock application that your own patcher generated from your original backup**:

```powershell
.\sinowisp.exe write --platform sh68f90 --vendor_id 0x12C9 --product_id 0x6001 --firmware_size 61440 --bootloader_size 4096 --page_size 2048 --isp_iface_num 1 --isp_report_id 5 --reboot false .\local-output\gm610_stock_application.bin
```

Wait for the utility to finish, then disconnect/reconnect USB. Re-check `12C9:6001` and keyboard functionality.

## If the device is already in ISP mode

If Windows detects **`0603:1020`**, stop and investigate the previous error first. The bootloader is accessible, but that **does not** guarantee the application is safely writable or your backup is correct. If appropriate, try restoring the original 61,440-byte application via the supported `sinowisp write` command above. Do not use the complete full dump as the write input.

## If normal mode and ISP mode both disappear

There is **no verified software-only recovery procedure for this GM610** in that situation. The previously observed HID report `05 75 00 00 00 00` was sent **by a running application**; it cannot be assumed to work after application corruption. A supported independent bootloader-entry method, factory pad access or external MCU programmer might be necessary, and the relevant pinout / recovery sequence has **not been established** for this board.

## Safety limits

- `sinowisp read` may change an application-enable opcode even when you are only attempting a backup; review its upstream documentation.
- The readout relocates certain reset-vector bytes, so it is **not a raw JTAG/external-flash image**.
- **Never write the 65,536-byte full readout** as the application. For this layout the intended application file is **61,440 bytes**.
- A bootloader included in a readout is valuable evidence, **not proof** that it can be reinstalled or that recovery is guaranteed.
- Do not experiment with unrelated images, force a hash mismatch, or blindly retry erase/write operations.
- Keep a spare keyboard connected and a separate copy of your backup before proceeding.

External documentation: https://github.com/karstx/sinowisp
