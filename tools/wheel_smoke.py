"""Run with the installed wheel in a clean Python environment."""
import sys
import tempfile
from pathlib import Path

import numpy as np
from thermalmaster_p3 import Camera, Frame, raw_to_celsius, __version__
from thermalmaster_p3.recording import SessionWriter, replay

assert 'cv2' not in sys.modules and 'rclpy' not in sys.modules
assert __version__ == '1.0.0'
np.testing.assert_allclose(raw_to_celsius(np.array([19082], np.uint16)), [25.00625], atol=.0001)
frame = Frame(np.full((192, 256), 19082, np.uint16), np.zeros((192, 256), np.uint8),
              np.zeros((2, 256), np.uint16), 0, 123, 456, (1, 0, 0), (1, 0, 40))
with tempfile.TemporaryDirectory() as directory:
    target = Path(directory) / 'session'
    with SessionWriter(target) as writer:
        writer.write(frame)
    restored = next(replay(target))
    np.testing.assert_array_equal(restored.raw, frame.raw)
    assert restored.utc_ns == 456
print('Clean installed wheel: core import, conversion, recording and replay passed')
