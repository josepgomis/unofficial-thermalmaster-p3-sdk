# Validation status — 2026-09-30

Automated validation passed in [GitHub Actions run 36740280965](https://github.com/josepgomis/unofficial-thermalmaster-p3-sdk/actions/runs/36740280965), code commit `0ca5b1c`. All 11 jobs succeeded. ROS tests use a simulated camera; they do not certify USB access or physical accuracy.

| Area | Evidence | Status |
| --- | --- | --- |
| SDK unit tests | 39 tests including viewer extra, Windows, Python 3.12.14 / NumPy 2.3.5 | Passed locally; latest CI rerun pending |
| Parser | Fragmentation, concatenation, corruption, truncation, NUC recovery, bounded queue, counter wrap | Synthetic tests passed |
| Camera lifecycle | Mock transport, partial claims, timeout, unplug, resource release | Tests passed; not physical streaming |
| Recording | Full/partial blocks, replay, interruption, owned copies, version/path validation, control events | Passed locally |
| Wheel + sdist | `python -m build --no-isolation`, `twine check` | Passed locally |
| Clean install | Fresh Python 3.12 venv, wheel + NumPy 2.5.3 / PyUSB 1.3.1 / libusb-package 1.0.30.0 | Core import, conversion, recording/replay and CLI help passed |
| Optional dependencies | Base import without OpenCV or ROS in clean venv | Passed |
| Viewer | OpenCV 5.0.0.93, physical frame/ROI/palette exports and rotation mapping inspected | Render/export passed; keyboard/mouse states automated |
| Windows/Linux SDK | Python 3.8, 3.10, 3.12 and 3.13; unit tests, wheel/sdist, metadata and clean wheel smoke | All 8 CI jobs passed |
| Python 3.8 | SDK runtime tests and Foxy Python 3.8.10 environment | Passed in CI |
| Physical USB discovery | P3 `3474:45a2`, path `1:3` | Detected on Windows |
| Physical capture | Firmware 00.00.02.18, WinUSB on grouped MI_00 child; native raw/IR capture and 30-frame replay | Passed on Windows |
| Capture endurance | Last observed progress: 660.109 s, 16,448 frames, 24.917 average FPS | Stopped at user request; 30-minute acceptance not completed |
| Gain and NUC | High/low gain and NUC acknowledged; subsequent valid frames delivered | Physical Windows test exercised; not an accuracy certificate |
| Disconnect/reconnect | Separate short physical test | Pending |
| Linux x86_64 / ARM64 | No accessible Linux runtime in this session | Hardware tests pending |
| ROS Foxy/Humble/Jazzy | Ubuntu 20.04/22.04/24.04 containers; colcon build/test; encodings, Celsius payload, shared headers, gain/timeout validation, NUC service; rosbag2 record/play | All 3 CI jobs passed with simulated camera |
| Package name | PyPI JSON endpoint returned HTTP 404 on 2026-09-30 | Apparently unregistered; not reserved |

The owner explicitly stopped the endurance run before 30 minutes. [Observed hardware evidence](hardware/windows-p3-2026-09-30.json) preserves the last stdout progress interval, not an invented final duration. Final timeout/corruption/drop counters were unavailable after interruption; no zero-loss claim is made. The alpha release discloses this incomplete endurance check.

The gallery and release sample use actual acquisitions from a user-approved scene. [Provenance](images/provenance.json) records firmware, timing and display rotation; the configuration manifest omits device serial identifiers. Thermal arrays and original metadata are preserved.

## Physical acceptance procedure

1. Configure WinUSB for the identified P3 interfaces, then run `p3 info` and save model/firmware without posting a private serial number.
2. Run `p3 capture frame.npz`; inspect dimensions, native values and temperatures against a stable scene. Do not claim absolute calibration from plausible room temperature alone.
3. For a future complete endurance run, use `python tools/hardware_validate.py --duration 1800` or `p3 record sessions/acceptance --duration 1800` if saving all frames is required. The validation tool saves progress every minute without a large recording. Counter discontinuities are not an exact lost-frame count.
4. In a separate viewer run, change high/low gain and trigger NUC. Verify framing recovery and recording/replay of original data.
5. Unplug/replug: standalone operations must raise an actionable error and allow a fresh Camera; the ROS node must reconnect without publishing old frames.
6. Repeat on Linux and run the ROS tests in each supported distribution. Record observed architecture, firmware, driver, dependency versions and results before upgrading any support claim.
