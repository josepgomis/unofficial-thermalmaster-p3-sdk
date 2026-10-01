# Validation status — 2026-10-01

Version 1.0.0 acceptance covers Ubuntu 22.04.5 x86_64 and ROS 2 Humble with a physical P3, firmware 00.00.02.18. The agreed stability duration is **15 minutes for the SDK and a separate 15 minutes for ROS**, not 30 minutes. Absolute measurement accuracy is not certified.

The corrected transport and Linux runtime dependency passed all 11 jobs in [GitHub Actions run 36886067233](https://github.com/josepgomis/unofficial-thermalmaster-p3-sdk/actions/runs/36886067233), commit `aa1f84a`: eight Windows/Linux SDK jobs with Python 3.8, 3.10, 3.12 and 3.13, plus Foxy/Humble/Jazzy builds, tests and simulated-camera rosbag2 record/play. The release notes link the final packaging commit's complete CI run. Simulated-camera tests certify adapter behavior, not physical USB access.

| Area | Evidence | Status |
| --- | --- | --- |
| SDK unit tests | 44 tests, including stalled-acceptance rejection, stop/start and unplug cleanup regressions | Passed locally and in corrected-transport CI |
| Wheel + sdist | Build, metadata check and installation in a clean environment | Passed locally for 1.0.0; repeated in final release CI |
| Linux environment | Ubuntu 22.04.5 x86_64; Python 3.10.12; NumPy 2.2.6; PyUSB 1.3.1; libusb-package 1.0.30.0; OpenCV 4.14.0.94 | Physically exercised |
| Physical SDK stability | 900.001 seconds; 22,445 frames; 24.939 average FPS; maximum valid-frame gap 1.477 seconds | Passed; [raw report](hardware/linux-sdk-2026-10-01.json) |
| SDK counters | 3 read-deadline timeouts; 2 corrupt candidates; 0 queue drops; 724 marker discontinuities | Recorded; not a zero-loss claim |
| Gain and NUC | Low/high gain and NUC acknowledged; valid radiometric frames resumed | Passed physically |
| Physical capture and viewer | Native 192×256 uint16 raw, float32 Celsius, uint8 IR; CLI capture, record/replay, native OpenCV window, palettes and ROI; 180° display for this mounting | [Feature report](hardware/linux-features-2026-10-01.json); raw arrays remain native |
| SDK disconnect/reconnect | DeviceDisconnectedError on unplug, fresh Camera after replug; corrected stop/start also receives native frames | [Passed with system libusb 1.0.25](hardware/linux-reconnect-system-libusb-2026-10-01.json) |
| Physical ROS stability | 900.037 seconds; 22,351 published frames; 22,350 complete same-header groups checked; maximum observed gap 0.749 seconds | Passed; [raw report](hardware/linux-ros-2026-10-01.json) |
| ROS contracts | 16UC1 raw, 32FC1 Celsius, mono8 IR; shared headers; native dimensions; sensor-data QoS; uncalibrated CameraInfo; gain/NUC; diagnostics | Physical run and adapter tests passed |
| ROS rosbag2 | First 15 seconds recorded on all five topics; live stream observed for the full acceptance duration; 248 raw images replayed | Physical playback passed; [all-topic payload check](hardware/linux-rosbag-playback-2026-10-01.json) validated 247 complete groups |
| ROS disconnect/reconnect | Automatic fresh Camera, old handle closed, no pre-reconnect ROS samples observed after replug | [Passed physically](hardware/linux-ros_reconnect-2026-10-01.json) |
| ROS adapter unit tests | Topic encodings, Celsius payload, headers, gain/timeout validation, NUC service, disconnect and stalled-stream recovery | 3 tests passed locally and in corrected-transport CI |
| Windows physical history | WinUSB capture, gain/NUC and reconnect, firmware 00.00.02.18; historical endurance progress 660.109 s / 16,448 frames | Previously exercised; no new Windows endurance claim |
| ARM64 and physical Foxy/Jazzy | No physical acceptance on these targets | Pending |
| Absolute thermal accuracy | No calibrated thermal reference used | Unverified |

## Initial failure and correction

The initial Linux unplug test aborted in system libusb 1.0.25 while closing a disconnected camera. [Failure evidence](hardware/linux-libusb-failure-2026-10-01.json) preserves the actual failure. The SDK now releases interfaces instead of redundantly resetting altsetting on stop/close, and reclaims streaming on restart. The same system runtime passed the corrected physical reconnect check. Linux and Windows installations also supply a corrected bundled libusb runtime, protecting initialization. The standalone 15-minute acceptance was repeated with the bundled runtime before accepting v1.

The earlier [Linux system-runtime capture](hardware/linux-sdk-system-runtime-2026-10-01.json) is retained separately; the initial capture passed, but its subsequent unplug cleanup did not. Historical [Windows evidence](hardware/windows-p3-2026-09-30.json) remains unchanged: that owner-stopped run did not complete its original 30-minute request and has no final loss counters.

Counter discontinuities describe undocumented USB marker transitions, **not an exact lost-frame count**. The SDK report's `seconds` and `fps` are final metrics; `elapsed_seconds` and `average_fps` retain its last periodic progress snapshot. Review the interval deltas to detect sustained degradation. Corrupt transitions and read timeouts are disclosed rather than reported as zero. No hardware-synchronized exposure timestamps, extrinsics, environmental correction or thermal calibration are fabricated.

The gallery and existing 30-frame release sample are actual Windows acquisitions with [provenance](images/provenance.json). No new private Linux image or device serial is published by this validation. Local display rotation of 180° does not rotate raw matrices, recordings or ROS images; mounting transforms are supplied by the integrator.

## Repeat physical acceptance

1. Install the package, configure [USB permissions](usb.md), then check model/firmware without publishing serial identifiers.
2. Capture a native frame and inspect shape, dtypes and `raw / 64 - 273.15`. Plausible room temperatures are not calibration evidence.
3. Run `python tools/hardware_validate.py --duration 900 --report build/sdk-acceptance.json`. Examine minute-by-minute throughput, maximum gap and all parser counters, not just `result`.
4. Check capture, record/replay and native viewer behavior separately; use `--rotate 180` only when required by the mounting.
5. Run `python tools/check_reconnect.py`; follow its manual unplug/replug prompt. Also verify stop/start and clean device release.
6. Follow [ROS setup](ros2.md), build/test the adapter, then run `python tools/ros_check_reconnect.py` and `python tools/ros_hardware_validate.py --duration 900 --bag build/new-physical-bag --report build/ros-acceptance.json`. Use a fresh bag path; do not mix simulation or an unrelated publisher with the acceptance topics.
7. Save system, architecture, firmware, dependency/runtime versions, source commit, duration and observed results before changing support claims. Run the full SDK and ROS CI matrix on the final packaging commit.
