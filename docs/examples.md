# Examples and recipes

Start with [USB setup](usb.md) and `p3 info`. If multiple cameras are attached, choose `--path` in the CLI or `Camera(path=...)` in Python.

To run repository examples:

```sh
git clone https://github.com/josepgomis/unofficial-thermalmaster-p3-sdk.git
cd unofficial-thermalmaster-p3-sdk
python -m pip install .
```

## Capture a temperature matrix

```sh
python examples/capture.py
p3 capture frame.npz
```

[capture.py](../examples/capture.py) opens and closes the camera automatically. A frame contains original `uint16` radiometry, `float32` Celsius, `uint8` IR brightness, original metadata and host reception timestamps. See the [API](api.md).

## Analyze with NumPy

For recorded physical data without a camera, follow the [NumPy tutorial](tutorial-numpy.md) and run `python examples/offline_numpy_analysis.py p3-real-sample`.

### Live acquisition

```sh
python examples/numpy_analysis.py
```

[numpy_analysis.py](../examples/numpy_analysis.py) finds the hottest pixel and calculates a central ROI average. Array indexing is `[y, x]`, shape `(192, 256)`. Display palettes do not affect these values.

For saved snapshots:

```python
import numpy as np

with np.load("frame.npz", allow_pickle=False) as frame:
    temperature = frame["temperature_c"]
    print("Central ROI average:", temperature[80:112, 112:144].mean())
```

## Inspect, record and replay

```sh
python -m pip install ".[viewer]"
python examples/opencv_viewer.py
p3 record sessions/run-01 --duration 60
p3 replay sessions/run-01 --viewer --range 15 60
```

[record_replay.py](../examples/record_replay.py) demonstrates the writer API. Choose a new output directory for each session; existing sessions are never overwritten. See the [viewer guide](viewer.md) and [session format](recording.md).

You can also replay the release's actual P3 sample without hardware. The synthetic generator remains available as a development fixture and labels its recordings explicitly; repository gallery images all use the physical P3.

## ROS 2

Follow the [ROS visualization tutorial](tutorial-ros2.md) and [full parameter/calibration reference](ros2.md) for Foxy, Humble or Jazzy. The adapter publishes raw `16UC1`, Celsius `32FC1`, IR `mono8` and `CameraInfo` with sensor QoS, plus diagnostics and a NUC service. The guide includes parameter changes and rosbag2 commands.

For physical endurance checks from a checkout:

```sh
python tools/hardware_validate.py --duration 1800 --report build/hardware-validation.json
```

This reads frames without saving a large recording, exercises gain and NUC, and writes identifier-free metrics. Keep the P3 connected throughout; run unplug/replug as a separate test. Counters are diagnostics, not an exact lost-frame estimate.
