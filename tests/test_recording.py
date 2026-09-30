import json

import numpy as np
import pytest

from thermalmaster_p3.protocol import FrameParser
from thermalmaster_p3.recording import SessionWriter, replay
from test_protocol import wire


def sample():
    parser = FrameParser()
    parser.feed(wire())
    return parser.pop()


def test_roundtrip_full_and_partial_blocks(tmp_path):
    frame = sample()
    target = tmp_path / 'session'
    with SessionWriter(target, {'gain': 'high'}, block_size=2) as writer:
        for _ in range(3):
            writer.write(frame)
    manifest = json.loads((target / 'manifest.json').read_text())
    assert manifest['frames'] == 3 and len(manifest['blocks']) == 2
    restored = list(replay(target))
    assert len(restored) == 3
    for item in restored:
        for key in ('raw', 'ir', 'metadata', 'temperature_c'):
            np.testing.assert_array_equal(getattr(frame, key), getattr(item, key))
        assert item.utc_ns == frame.utc_ns
        assert item.start_counters == frame.start_counters


def test_snapshot_and_error_finalization(tmp_path):
    frame = sample()
    target = tmp_path / 'session'
    with pytest.raises(RuntimeError):
        with SessionWriter(target) as writer:
            writer.write(frame)
            frame.raw[:] = 0
            raise RuntimeError('interrupted')
    assert np.all(next(replay(target)).raw == 19082)
    with pytest.raises(FileExistsError):
        SessionWriter(target)
    with pytest.raises(ValueError):
        writer.write(frame)


def test_version_and_path_validation(tmp_path):
    target = tmp_path / 'session'
    with SessionWriter(target):
        pass
    filename = target / 'manifest.json'
    values = json.loads(filename.read_text())
    values['version'] = 99
    filename.write_text(json.dumps(values))
    with pytest.raises(ValueError):
        list(replay(target))
    values['version'] = 1
    values['blocks'] = ['../outside.npz']
    filename.write_text(json.dumps(values))
    with pytest.raises(ValueError):
        list(replay(target))


def test_control_events_are_preserved(tmp_path):
    target = tmp_path / 'events'
    with SessionWriter(target) as writer:
        writer.write(sample())
        writer.event('gain', {'gain': 'low'})
    values = json.loads((target / 'manifest.json').read_text())
    assert values['events'][0]['after_frames'] == 1
    assert values['events'][0]['values'] == {'gain': 'low'}
