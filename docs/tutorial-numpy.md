# Thermal Master P3 radiometric analysis with Python and NumPy

Analyze original thermal-camera measurements, rather than colors from a screenshot. This tutorial works without hardware using the release's real P3 sample.

## Install and obtain the real sample

```sh
git clone https://github.com/josepgomis/unofficial-thermalmaster-p3-sdk.git
cd unofficial-thermalmaster-p3-sdk
python -m pip install "git+https://github.com/josepgomis/unofficial-thermalmaster-p3-sdk.git@v1.0.0"
```

Download `p3-real-sample.zip` from [v1.0.0](https://github.com/josepgomis/unofficial-thermalmaster-p3-sdk/releases/tag/v1.0.0) and extract it into this checkout. The `p3-real-sample/` directory contains 30 physical P3 frames. A camera is not needed for the following command:

```sh
python examples/offline_numpy_analysis.py p3-real-sample
```

It prints frame count, hottest-pixel coordinates, whole-frame extrema and central-ROI min/mean/max for the first frame. Values depend on the recorded scene; they are not calibration references.

## Understand the arrays

The image is 256 pixels wide and 192 high; arrays are indexed `[y, x]`. `raw` is `(192, 256)` uint16 in 1/64 K; `temperature_c` computes float32 Celsius as `raw / 64 - 273.15`. Metadata is retained separately and is not interpreted as temperature pixels.

```python
import numpy as np
from thermalmaster_p3.recording import replay

frame = next(replay("p3-real-sample"))
temperature = frame.temperature_c
assert temperature.shape == (192, 256)
assert temperature.dtype == np.float32

y, x = np.unravel_index(np.argmax(temperature), temperature.shape)
roi = temperature[80:112, 112:144]
print("Hottest pixel (x, y, °C):", int(x), int(y), float(temperature[y, x]))
print("ROI min/mean/max (°C):", float(roi.min()), float(roi.mean()), float(roi.max()))
```

The ROI above is 32 × 32 pixels. Slicing uses native sensor coordinates. Viewer rotation and palettes do not alter these arrays. Copies owned by each Frame remain valid after later reads or camera closure; their NumPy contents can still be modified by callers.

## Inspect an actual temperature matrix

![Celsius matrix displayed at 180 degrees and central ROI distribution computed from one physical Linux P3 acquisition](images/linux-temperature-matrix.png)

This plot is calculated from one captured radiometric NPZ, without interpolating temperatures or modifying stored arrays. The display is rotated 180° for this mounting; axes retain the original sensor coordinates. The color bar expresses Celsius; the histogram is a distribution of pixels from that single ROI, not measurement uncertainty. [Gallery and provenance](gallery.md).

## Capture and load your own NPZ

Configure [USB access](usb.md), then run:

```sh
p3 capture frame.npz
```

```python
import numpy as np

with np.load("frame.npz", allow_pickle=False) as saved:
    raw = saved["raw"]
    temperature = saved["temperature_c"]
    np.testing.assert_allclose(temperature, raw.astype(np.float32) / 64 - 273.15)
    print("Frame range (°C):", float(temperature.min()), float(temperature.max()))
```

Use [Camera](api.md) directly for live processing and [SessionWriter](recording.md) for repeated acquisition. The SDK is synchronous; run application acquisition and inference in a deliberate scheduling strategy if inference is slower than the camera. The parser's completed-frame queue is bounded and may discard old queued frames. No zero-copy or loss-free guarantee is made.

## Measurement limits

The 1/64 K numerical step is not accuracy. No host-side emissivity, atmospheric or reflected-temperature corrections are applied. Pixel maxima can include noise or unwanted scene objects; do not equate a maximum with a calibrated target temperature. Reception timestamps are sampled on the host and are not exposure synchronization.
