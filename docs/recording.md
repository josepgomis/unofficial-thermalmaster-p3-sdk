# Radiometric sessions, format version 1

`SessionWriter(directory, configuration=None, block_size=100)` creates a new directory, refuses to overwrite existing sessions, and writes frames with `write(frame)`. Use a context manager to finalize the partial block after normal exit or an exception. Arrays are copied at write time.

`manifest.json` describes format `thermalmaster-p3`, version 1, dimensions, units, timestamp origin, JSON configuration, block filenames and committed frame count. Blocks contain arrays named `raw`, `ir`, `metadata`, `sequence`, `monotonic_ns`, `utc_ns`, `start_counters`, `end_counters`. The first dimension is the number of frames. Temperatures are computed from original raw values on replay.

`writer.event(name, values)` records host-timed control events in the manifest. The viewer uses it for gain and NUC commands during recording. Events indicate requested/acknowledged changes, not a verified exposure boundary.

NPZ files contain no Python objects. Replay always uses `allow_pickle=False`, validates dimensions and refuses filenames escaping the session directory. Each block and the manifest are replaced atomically. On a hard crash, uncommitted buffered frames can be lost and an orphan block can remain; only blocks referenced by the manifest are replayed. This is not a transactional database or a crash-proof recorder.

```python
from thermalmaster_p3.recording import SessionWriter, replay

# Inside an active camera context:
with SessionWriter('sessions/run-01', {'gain': camera.gain}) as writer:
    writer.write(camera.read_frame())

for frame in replay('sessions/run-01'):
    print(frame.utc_ns, frame.temperature_c.mean())
```

`p3 replay SESSION` validates and counts frames. Add `--viewer` for timed display. Playback waits use monotonic capture intervals, capped at 200 ms for responsiveness. It is a visualization replay, not real-time synchronization with other sensors. For ROS experiments, use rosbag2 to preserve ROS message timing and accompanying sensors.

## Actual P3 sample

Download `p3-real-sample.zip` from the [v1.0.0 release](https://github.com/josepgomis/unofficial-thermalmaster-p3-sdk/releases/tag/v1.0.0). Extract it using your archive tool; the resulting directory is `p3-real-sample/`.

```sh
p3 replay p3-real-sample
p3 replay p3-real-sample --viewer --rotate 180
p3 replay p3-real-sample --viewer --rotate 180 --range 15 35
```

The sample contains 30 physical P3 frames, original raw/IR/metadata arrays, reception timestamps and a configuration manifest with model/firmware/gain. Device serial identifiers are excluded from the manifest. The display rotation accounts for the camera mounting; arrays stay in native sensor orientation. It is a demonstration of acquisition and replay, not a temperature calibration reference.

```python
from thermalmaster_p3.recording import replay

for frame in replay("p3-real-sample"):
    print(frame.sequence, float(frame.temperature_c.mean()))
```

PNG gallery exports and their acquisition provenance live in `docs/images/`. No sample thermal images are synthesized. For regression tests only, `examples/synthetic_session.py` generates an explicitly labeled synthetic recording.
