# Validation status — 2026-09-30

Automated validation passed in [GitHub Actions run 36740280965](https://github.com/josepgomis/unofficial-thermalmaster-p3-sdk/actions/runs/36740280965), code commit `0ca5b1c`. All 11 jobs succeeded. ROS tests use a simulated camera; they do not certify USB access or physical accuracy.

| Area | Evidence | Status |
| --- | --- | --- |
| SDK unit tests | 25 tests, Windows, Python 3.12.14 / NumPy 2.3.5 | Passed locally |
| Parser | Fragmentation, concatenation, corruption, truncation, NUC recovery, bounded queue, counter wrap | Synthetic tests passed |
| Camera lifecycle | Mock transport, partial claims, timeout, unplug, resource release | Tests passed; not physical streaming |
| Recording | Full/partial blocks, replay, interruption, owned copies, version/path validation, control events | Passed locally |
| Wheel + sdist | `python -m build --no-isolation`, `twine check` | Passed locally |
| Clean install | Fresh Python 3.12 venv, wheel + NumPy 2.5.3 / PyUSB 1.3.1 / libusb-package 1.0.30.0 | Core import, conversion, recording/replay and CLI help passed |
| Optional dependencies | Base import without OpenCV or ROS in clean venv | Passed |
| Viewer | OpenCV 5.0.0.93 render, synthetic ROI/panel composition inspected | Rendering passed; interactive window/controls need real usage |
| Windows/Linux SDK | Python 3.8, 3.10, 3.12 and 3.13; unit tests, wheel/sdist, metadata and clean wheel smoke | All 8 CI jobs passed |
| Python 3.8 | SDK runtime tests and Foxy Python 3.8.10 environment | Passed in CI |
| Physical USB discovery | P3 `3474:45a2`, path `1:3` | Detected on Windows |
| Physical capture | `p3 info` cannot claim usable interfaces; MI_00 has code 28 | Blocked by Windows driver setup |
| 30-minute camera run | FPS, marker gaps, gain, NUC, unplug/replug | Pending USB access |
| Linux x86_64 / ARM64 | No accessible Linux runtime in this session | Hardware tests pending |
| ROS Foxy/Humble/Jazzy | Ubuntu 20.04/22.04/24.04 containers; colcon build/test; encodings, Celsius payload, shared headers, gain/timeout validation, NUC service; rosbag2 record/play | All 3 CI jobs passed with simulated camera |
| Package name | PyPI JSON endpoint returned HTTP 404 on 2026-09-30 | Apparently unregistered; not reserved |

## Physical acceptance procedure

1. Configure WinUSB for the identified P3 interfaces, then run `p3 info` and save model/firmware without posting a private serial number.
2. Run `p3 capture frame.npz`; inspect dimensions, native values and temperatures against a stable scene. Do not claim absolute calibration from plausible room temperature alone.
3. Run `p3 record sessions/acceptance --duration 1800`. Save elapsed time, average FPS, timeouts, corrupt candidates, queue drops and counter discontinuities. Counter discontinuities are not an exact lost-frame count.
4. In a separate viewer run, change high/low gain and trigger NUC. Verify framing recovery and recording/replay of original data.
5. Unplug/replug: standalone operations must raise an actionable error and allow a fresh Camera; the ROS node must reconnect without publishing old frames.
6. Repeat on Linux and run the ROS tests in each supported distribution. Record observed architecture, firmware, driver, dependency versions and results before upgrading any support claim.
