import subprocess
import sys

import numpy as np
import pytest

from thermalmaster_p3.protocol import FrameParser
from test_protocol import wire


def test_import_is_optional_in_separate_process():
    subprocess.run([sys.executable, '-c', "import sys; import thermalmaster_p3; assert 'cv2' not in sys.modules"], check=True)


def test_render_never_changes_raw():
    pytest.importorskip('cv2')
    from thermalmaster_p3.viewer import render
    parser = FrameParser()
    parser.feed(wire())
    frame = parser.pop()
    original = frame.raw.copy()
    image, low, high = render(frame, limits=(15, 60))
    assert image.shape == (192, 256, 3) and image.dtype == np.uint8
    assert low == 15 and high == 60
    np.testing.assert_array_equal(frame.raw, original)
