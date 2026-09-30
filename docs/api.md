# Python API

```python
from thermalmaster_p3 import Camera, list_devices
devices = list_devices()  # DeviceInfo(bus, address, path, serial)
camera = Camera(path=devices[0].path)
camera.open()
try:
    print(camera.info)  # model, firmware, vendor serial
    camera.start()
    camera.set_gain("high")  # high or low, no automatic mode in v1
    frame = camera.read_frame(timeout=2.0)
    camera.trigger_nuc()
    camera.stop()
finally:
    camera.close()
```

Prefer `with Camera() as camera:` to release resources on exceptions. `open()` returns the camera; the context manager opens it but does not start streaming. `start()` and `open()` are idempotent; `stop()` and `close()` may be called on a closed camera. Operations on an unopened camera or reads before `start()` raise `CameraStateError`.

USB reads and control commands share a lock. Reads can hold the lock for the requested timeout; use a short timeout when another thread needs responsive control. There is no background worker and no unbounded capture queue. The parser retains at most two completed frames. Standalone callers explicitly reopen after disconnect; ROS reconnects automatically.

## Frame

| Field | Meaning |
| --- | --- |
| `raw` | Owned `(192,256)` uint16 array, documented 1/64 kelvin units |
| `temperature_c` | Newly computed float32 Celsius array, no display normalization |
| `ir` | Owned `(192,256)` uint8 infrared brightness array |
| `metadata` | Owned `(2,256)` uint16 array; uninterpreted original metadata |
| `sequence` | Local valid-frame number, starts at zero for each stream |
| `monotonic_ns`, `utc_ns` | Host times when the complete frame is parsed |
| `start_counters`, `end_counters` | Original three USB marker counters |

Arrays survive subsequent reads and closing the camera. Frame attributes are frozen but NumPy arrays remain mutable. `raw_to_celsius(array)` is available independently. Neither timestamps nor marker counters are verified exposure times. Celsius uses `raw / 64 - 273.15`; the numerical step is not an accuracy guarantee. Environmental corrections are not implemented.

## Errors and counters

Catch `P3Error` for SDK failures, or its specific subclasses: `DeviceNotFoundError`, `DevicePermissionError`, `DeviceDisconnectedError`, `FrameTimeoutError`, `ProtocolError`, `CameraStateError`. Invalid arguments raise `ValueError`.

`camera.timeouts` counts failed `read_frame` deadlines. `camera.parser` exposes `corrupt_candidates`, `discarded_bytes`, `queue_drops`, and `counter_discontinuities`. Discontinuities report marker gaps, **not an exact lost-frame count**; undocumented counter semantics prevent that claim. Parser metrics reset on each stream start. Metadata and these counters are diagnostic, not a stable extensible hardware-control API.
