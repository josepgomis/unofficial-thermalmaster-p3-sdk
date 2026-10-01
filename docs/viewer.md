# OpenCV viewer

The viewer displays original 256 x 192 P3 measurements at 3x nearest-neighbor scale. It is a small inspection tool for acquisition and robotics development. The SDK core does not require OpenCV.

```sh
python -m pip install "unofficial-thermalmaster-p3[viewer] @ git+https://github.com/josepgomis/unofficial-thermalmaster-p3-sdk.git@v1.0.0"
p3 viewer
p3 viewer --range 15 60
p3 viewer --rotate 180
p3 replay p3-real-sample --viewer --range 15 60
```

From a local checkout: `python -m pip install ".[viewer]"`. Configure [USB access](usb.md) before starting live acquisition. OpenCV windows require an interactive desktop; use CLI capture/record on headless robots.

## Measurements and scale

The crosshair marks the native pixel coordinates shown in the panel. Drag within the image to select an inclusive rectangular ROI. The legend describes the **display** range in Celsius; it does not change `frame.raw` or the conversion to Celsius.

If the mounted camera appears upside down, use `--rotate 180` in live or replay mode. The display rotates while cursor/ROI measurements map back to the original sensor coordinates. Raw arrays and ROS images keep their native orientation. The gallery uses a 180-degree display rotation for this camera mounting.

- **AUTO:** 1st to 99th percentile of each frame. Values outside that range saturate in the palette. A changing color does not necessarily mean a changing temperature because the scale may move.
- **FIXED:** explicit `--range MIN MAX`, or the visible range frozen with `a`. Use the same fixed range when comparing frames or palettes. `a` restores the previous fixed range after returning to auto.
- **Recent FPS:** measured delivery/display cadence over the most recent approximately two seconds. Replay cadence includes playback waits and rendering; it is not a sensor exposure rate.

![Inferno, Jet and Bone applied to the same real P3 frame with identical fixed Celsius limits](images/viewer-palettes.png)

All three panels use the same actual frame, ROI and fixed range. They are replay exports from the shipped compositor, not separate physical measurements. [Provenance](images/provenance.json).

## Controls

| Input | Action |
| --- | --- |
| Mouse move | Read temperature and native `(x, y)` position |
| Left-button drag | Select ROI; panel/legend interactions are ignored |
| `c` | Clear ROI |
| `p` | Cycle Inferno, Jet and Bone |
| `a` | Toggle automatic/fixed scale |
| `i` | Export the complete displayed composition as PNG |
| `s` | Save a radiometric NPZ snapshot, including original arrays and temperatures |
| `r` | Start/stop a radiometric session recording |
| `n` | Request NUC, live mode only |
| `g` | Switch high/low gain, live mode only |
| `q` or window close | Finalize recording and release resources |

Exports use timestamped names under `sessions/`. A PNG contains rendered colors, legend, measurements and source state; it cannot replace the raw NPZ/session for numerical analysis. `s` snapshots can be loaded using `np.load(..., allow_pickle=False)`.

## States and recovery

`LIVE / STREAMING` means a valid live frame was received. `REPLAY / READY` means a saved frame is displayed. The replay remains open at `FINISHED` so you can inspect/export the last frame, then close with `q`.

During `TIMEOUT`, `DISCONNECTED` or `ERROR`, retained imagery is dimmed, cursor measurements are marked `STALE`, and FPS is unavailable. A retained picture is not a new observation. Timeouts can recover; disconnect/error requires closing and reopening after checking USB. Recording and camera resources are finalized on exit.

`NUC` reports acknowledgment and waiting for the next valid frame. Malformed transition frames are discarded. It does not claim an exposure boundary or absolute calibration. Temperature accuracy depends on the camera and measurement conditions; host timestamps are reception timestamps.
