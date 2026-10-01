# USB setup and troubleshooting

P3 identifiers: VID `3474`, PID `45a2`. Control interface: 0. Streaming interface: 1, alternate setting 1, bulk IN endpoint `81`. Both interfaces must be accessible to libusb. The composite USB parent must remain a composite device when installing per-interface drivers.

## Windows

1. Install Python and the SDK. The SDK includes `libusb-package` on Windows to provide the user-space backend.
2. Run `p3 devices`. Detection alone does not mean the interfaces are usable.
3. Inspect the P3 in Device Manager, or run `pnputil /enum-devices /connected /bus USB`. Confirm `VID_3474&PID_45A2`; note its interface children and their drivers.
4. If interfaces have no compatible driver, use [Zadig](https://zadig.akeo.ie/) and **Options → List All Devices**. Identify the P3's control and streaming interfaces from their USB IDs/interface numbers, then install WinUSB for the required interfaces. Do not select unrelated devices or replace the composite parent accidentally.
5. Replug the P3 and run `p3 info`, then `p3 capture frame.npz`.

If Windows exposes only one child, inspect the full device tree before choosing a driver. Do not guess from a generic friendly name. Driver installation is a user-managed step and can require administrator privileges. A vendor application may require its original driver; restore it through Device Manager if needed.

`Entity not found`, `Access denied`, `Not supported`, or `Resource busy` generally mean a missing/incompatible interface driver or another program owning the camera. Close the vendor app and check both interfaces. `libusb backend not available` means the user-space libusb library is missing; reinstall the package in the Python environment being used.

On the validated Windows PC, the P3's `MI_00` initially had problem code 28 (no driver). Manually installing WinUSB on that child resolved register access and streaming through both SDK interfaces; the composite parent retained its original driver. This camera exposes a grouped child: do not assume that you must create or replace a second Windows child. USB paths are machine-specific and can change.

## Linux

The Python installation supplies `libusb-package>=1.0.26.4` on Linux and Windows. The SDK selects that bundled userspace runtime; it does not replace system drivers. The system libusb runtime can also be installed through your distribution (Ubuntu: `sudo apt install libusb-1.0-0`). Create `/etc/udev/rules.d/99-thermalmaster-p3.rules` containing:

```udev
SUBSYSTEM=="usb", ATTR{idVendor}=="3474", ATTR{idProduct}=="45a2", MODE="0660", GROUP="plugdev", TAG+="uaccess"
```

Ensure the user belongs to `plugdev` for headless robot access. Apply with `sudo udevadm control --reload-rules` and `sudo udevadm trigger`, then unplug/replug. Re-login after changing group membership. Do not routinely run your project as root.

The SDK detaches kernel drivers only from interfaces 0 and 1 of the selected P3 and attempts to reattach them on close.

## Common checks

- Use a data-capable cable and a stable USB port; close any other process using the camera.
- With multiple P3 cameras, select `--path` or `--serial`. A USB serial descriptor may be unavailable; the vendor serial can be read by `p3 info` after interfaces are accessible.
- Normal start includes documented startup waits totaling about three seconds.
- NUC may interrupt frames. The parser drops malformed transition frames and resynchronizes instead of emitting suspect temperature arrays.
- After unplugging, reopen the standalone SDK or restart the CLI. The ROS node reconnects automatically.
- WSL is not native Linux USB access. USB passthrough must be configured separately; it has not been validated here.

### Ubuntu 22.04 libusb 1.0.25 disconnect failure

Physical testing found an abort in `libusb_close` after unplugging with Ubuntu's libusb 1.0.25. Its [`libusb_set_interface_alt_setting` error path](https://github.com/libusb/libusb/blob/v1.0.25/libusb/core.c) unlocks a mutex before taking the lock when the device is disconnected. The SDK now stops by releasing the streaming interface, reclaims it on restart, and closes by releasing interfaces without a redundant altsetting reset. libusb documents that interface release resets the alternate setting. The bundled runtime also avoids the affected startup path if unplugging occurs during initialization.
