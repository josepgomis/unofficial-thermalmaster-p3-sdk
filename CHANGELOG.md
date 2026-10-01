# Changelog

## Unreleased

- Fix Linux unplug cleanup abort with libusb 1.0.25: release streaming interfaces on stop, reclaim on restart, and avoid redundant altsetting resets on close.
- Supply an updated bundled libusb runtime on Linux as well as Windows, retaining Python 3.8 compatibility.

- Hardware acceptance rejects stalled streams even if an earlier frame succeeded, checks radiometric payloads, and records environment and maximum frame gaps.
- Added a ROS physical acceptance tool with gain/NUC controls and rosbag2 playback; simulation is explicitly identified.
- Clarified ROS Python selection and why colcon requires a normal SDK installation.

## 0.1.0 — 2026-09-30 (alpha)

- Original Python P3 USB transport, validated framing and owned radiometric arrays.
- Device discovery, gain and NUC commands, typed API and structured errors.
- CLI, optional OpenCV viewer, versioned NPZ recording and replay.
- ROS 2 adapter and CI configurations targeting Foxy, Humble and Jazzy.
- English documentation and Spanish quick start.
- Real P3 image gallery, identifier-free sample session and reproducible capture tools.
- Viewer Celsius legend, recent FPS, scale toggle, crosshair/ROI, PNG export and stale-frame states.
- Optional 180-degree display rotation with native coordinate mapping; raw/ROS arrays unchanged.
- Firmware 00.00.02.18 write-only command acknowledgment compatibility.
- WinUSB unplug I/O errors become DeviceDisconnectedError only after USB absence confirmation.

Alpha: public interfaces may change before 1.0. Windows physical capture works; SDK and simulated-camera ROS runtime tests have passed. Linux hardware and absolute temperature accuracy remain unverified; see [validation](docs/validation.md).
