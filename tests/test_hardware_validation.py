"""Acceptance must reject stalled streams even after a successful frame."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from thermalmaster_p3 import FrameTimeoutError
from thermalmaster_p3.frame import Frame


def load_tool():
    path = Path(__file__).resolve().parents[1] / 'tools' / 'hardware_validate.py'
    spec = importlib.util.spec_from_file_location('hardware_validate', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('stall', [False, True])
def test_physical_acceptance_checks_stream_progress(monkeypatch, tmp_path, stall):
    module = load_tool()
    clock = [0.]
    module.time = SimpleNamespace(monotonic=lambda: clock[0])
    class Camera:
        info = {'model': 'fake', 'firmware': 'fake'}
        timeouts = 0
        parser = SimpleNamespace(corrupt_candidates=0, queue_drops=0,
                                 counter_discontinuities=0, discarded_bytes=0)
        def open(self): pass
        def start(self): pass
        def set_gain(self, gain): pass
        def close(self): pass
        def read_frame(self, timeout):
            clock[0] += .1
            if stall and clock[0] > .1:
                self.timeouts += 1
                raise FrameTimeoutError('simulated stall')
            return Frame(np.full((192, 256), 19082, np.uint16),
                         np.zeros((192, 256), np.uint8), np.zeros((2, 256), np.uint16),
                         0, 0, 0, (0, 0, 0), (0, 0, 0))
    monkeypatch.setattr(module, 'Camera', Camera)
    report = tmp_path / 'report.json'
    monkeypatch.setattr('sys.argv', ['hardware_validate', '--duration', '1',
                                   '--max-stall', '.3', '--report', str(report)])
    if stall:
        with pytest.raises(RuntimeError, match='stalled'):
            module.main()
    else:
        module.main()
    saved = json.loads(report.read_text())
    assert saved['frames'] > 0
    assert saved['result'] == ('failed' if stall else 'passed')
