# Unofficial Thermal Master P3 SDK

Independent Python SDK for native radiometric P3 data, with an optional OpenCV viewer and ROS 2 integration. Not affiliated with or endorsed by Thermal Master.

**0.1.0 is an alpha.** The protocol implementation and packaging have automated tests. Real-camera streaming is not yet validated: the development PC detects a P3, but its USB interfaces lack a usable Windows driver. Do not treat the current support targets as hardware certification.

## Install and capture

From this checkout (Python 3.8 or newer):

```sh
python -m pip install .
p3 devices
p3 info
p3 capture frame.npz
```

First configure USB access using the [Windows/Linux guide](docs/usb.md). The SDK never installs or replaces system drivers.

```python
from thermalmaster_p3 import Camera

with Camera() as camera:
    camera.start()
    frame = camera.read_frame(timeout=2.0)
    temperatures = frame.temperature_c  # float32 Celsius, shape (192, 256)
    print(temperatures[96, 128])
```

`frame.raw` retains the original `uint16` radiometric values. `frame.ir` is the camera's gain-mapped infrared brightness image, **not a visible-light camera**. Display processing never modifies radiometric data.

The package is prepared for PyPI but is **not published yet**. After publication:

```sh
python -m pip install unofficial-thermalmaster-p3
```

The chosen repository is `josepgomis/unofficial-thermalmaster-p3-sdk`. After it is uploaded and tagged, installation directly from GitHub will also be available:

```sh
# Available after the repository and v0.1.0 tag have been published.
python -m pip install "git+https://github.com/josepgomis/unofficial-thermalmaster-p3-sdk.git@v0.1.0"
```

## Viewer and recording

```sh
python -m pip install ".[viewer]"
p3 viewer
p3 viewer --range 15 60
p3 record sessions/experiment --duration 60
p3 replay sessions/experiment
p3 replay sessions/experiment --viewer
```

Viewer controls: `q` quit, `p` palette, `s` radiometric snapshot, `r` recording, `n` NUC, `g` gain. Drag a rectangle for ROI statistics. Snapshots and sessions go into `sessions/`. Replay is bounded to one block in memory.

Try a clearly labeled synthetic recording without a camera:

```sh
python examples/synthetic_session.py sessions/synthetic
p3 replay sessions/synthetic --viewer
```

## ROS 2 and documentation

- [ROS 2 setup, topics, calibration and rosbag2](docs/ros2.md)
- [Public API and error behavior](docs/api.md)
- [Recording format](docs/recording.md)
- [Protocol basis and limitations](docs/protocol.md)
- [Compatibility and validation status](docs/validation.md)
- [Guía rápida en español](docs/quickstart-es.md)
- [Contributing](CONTRIBUTING.md) and [release checklist](docs/releasing.md)

Examples cover [capture](examples/capture.py), [NumPy analysis](examples/numpy_analysis.py), [OpenCV](examples/opencv_viewer.py), and [record/replay](examples/record_replay.py).

## Development

```sh
python -m pip install -e ".[dev]"
python -m pytest -q
python -m build
python -m twine check dist/*
```

CI is configured for Windows/Linux and Python 3.8, 3.10, 3.12 and 3.13. Separate ROS jobs build and run simulated-camera tests on Foxy, Humble and Jazzy. A configured workflow is not evidence that it has run; see the validation report.

## Attribution and license

Original SDK implementation informed by the public [P3 protocol research by jvdillon and contributors](https://github.com/jvdillon/p3-ir-camera/blob/main/P3_PROTOCOL.md). We did not copy the upstream Python driver. Protocol field values and documented command packets are interoperability facts. See [NOTICE](NOTICE).

Apache-2.0. Product names and trademarks belong to their respective owners. Pre-1.0 API changes will be documented in [CHANGELOG.md](CHANGELOG.md).
