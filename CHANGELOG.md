# Changelog

## Unreleased

- Fix intermittent ROS Foxy rosbag recording failures by supplying explicit sensor QoS overrides in CI, physical validation and the documented recording command. Install the override with the ROS package and include it in source archives.
- Require nonzero recorded message counts for every sensor topic in the rosbag smoke test before playback.

## 1.0.0 — 2026-10-01

- Linux x86_64 SDK and ROS 2 Humble passed physical stability and functional validation, including gain/NUC, record/replay and unplug/replug checks.
- Stabilize the documented SDK API, CLI, recording format and ROS topic/encoding contracts for the 1.x series. Absolute accuracy, ARM64 and physical Foxy/Jazzy validation remain outside this acceptance.

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
