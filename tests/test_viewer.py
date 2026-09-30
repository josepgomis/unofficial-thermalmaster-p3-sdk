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


@pytest.fixture
def viewer_frame():
    pytest.importorskip('cv2')
    parser = FrameParser()
    parser.feed(wire())
    return parser.pop()


@pytest.mark.parametrize('limits', [(20, 20), (30, 10), (0, float('inf')), (float('nan'), 10)])
def test_invalid_range(viewer_frame, limits):
    from thermalmaster_p3.viewer import render
    with pytest.raises(ValueError):
        render(viewer_frame, limits)


def test_freeze_and_restore_range(viewer_frame):
    from thermalmaster_p3.viewer import _ViewerState, _compose
    state = _ViewerState()
    _compose(viewer_frame, state)
    actual = state.displayed_limits
    state.toggle_scale()
    assert state.limits == actual
    state.toggle_scale()
    assert state.limits is None
    state.toggle_scale()
    assert state.limits == actual
    fixed = _ViewerState(limits=(15, 60))
    fixed.toggle_scale()
    fixed.toggle_scale()
    assert fixed.limits == (15, 60)


def test_roi_coordinates_and_panel_ignored(viewer_frame):
    import cv2
    from thermalmaster_p3.viewer import _ViewerState, _roi_stats
    state = _ViewerState()
    state.mouse(cv2.EVENT_LBUTTONDOWN, 30, 60)
    state.mouse(cv2.EVENT_LBUTTONUP, 60, 90)
    assert _roi_stats(viewer_frame, state)[0] == (10, 20, 20, 30)
    before = state.cursor, state.roi_start, state.roi_end
    state.mouse(cv2.EVENT_LBUTTONDOWN, 300, 650)
    assert (state.cursor, state.roi_start, state.roi_end) == before
    state.clear_roi()
    assert _roi_stats(viewer_frame, state) is None


def test_export_legend_and_stale_frame(viewer_frame, tmp_path):
    import cv2
    from thermalmaster_p3.viewer import _ViewerState, _compose, _export_png
    state = _ViewerState(limits=(15, 60))
    original = viewer_frame.raw.copy()
    live = _compose(viewer_frame, state, 'LIVE', 'STREAMING', 'high')
    stale = _compose(viewer_frame, state, 'LIVE', 'TIMEOUT', 'high')
    assert live.shape == (806, 768, 3)
    # The legend goes cold to hot while retained imagery is visibly dimmed.
    assert not np.array_equal(live[590, 20], live[590, 495])
    assert stale[:550].mean() < live[:550].mean()
    output = _export_png(live, tmp_path / 'viewer.png')
    np.testing.assert_array_equal(cv2.imread(str(output)), live)
    np.testing.assert_array_equal(viewer_frame.raw, original)


def test_export_failure(viewer_frame, tmp_path, monkeypatch):
    import cv2
    from thermalmaster_p3.viewer import _export_png, render
    monkeypatch.setattr(cv2, 'imwrite', lambda *args: False)
    with pytest.raises(OSError):
        _export_png(render(viewer_frame)[0], tmp_path / 'fail.png')


def test_recent_fps(viewer_frame):
    from thermalmaster_p3.viewer import _ViewerState
    state = _ViewerState()
    assert state.fps is None
    for i in range(70):
        state.received(i / 25)
    assert state.fps == pytest.approx(25)
    assert len(state.fps_times) <= 52


def test_rotation_maps_mouse_to_original_pixels(viewer_frame):
    import cv2
    from thermalmaster_p3.viewer import _ViewerState, _compose, _roi_stats
    state = _ViewerState(rotation=180)
    state.mouse(cv2.EVENT_LBUTTONDOWN, 0, 0)
    state.mouse(cv2.EVENT_LBUTTONUP, 6, 9)
    assert state.cursor == (253, 188)
    assert _roi_stats(viewer_frame, state)[0] == (253, 188, 255, 191)
    original = viewer_frame.raw.copy()
    _compose(viewer_frame, state)
    np.testing.assert_array_equal(viewer_frame.raw, original)
    with pytest.raises(ValueError):
        _ViewerState(rotation=90)


@pytest.mark.parametrize('ending', ['finished', 'disconnected'])
def test_viewer_final_states_and_cleanup(viewer_frame, monkeypatch, ending):
    import cv2
    from thermalmaster_p3.viewer import run_viewer
    from thermalmaster_p3 import DeviceDisconnectedError
    from unittest.mock import MagicMock
    displays = []
    keys = iter([-1, -1, ord('q')])
    monkeypatch.setattr(cv2, 'namedWindow', lambda *args: None)
    monkeypatch.setattr(cv2, 'setMouseCallback', lambda *args: None)
    monkeypatch.setattr(cv2, 'imshow', lambda title, image: displays.append(image.copy()))
    monkeypatch.setattr(cv2, 'waitKey', lambda *args: next(keys, ord('q')))
    monkeypatch.setattr(cv2, 'getWindowProperty', lambda *args: 1)
    destroy = MagicMock()
    monkeypatch.setattr(cv2, 'destroyWindow', destroy)
    if ending == 'finished':
        run_viewer(frames=iter([viewer_frame]))
    else:
        camera = MagicMock(gain='high')
        camera.read_frame.side_effect = [viewer_frame, DeviceDisconnectedError('unplug')]
        run_viewer(camera=camera)
        assert camera.close.called
    assert len(displays) >= 3
    assert not np.array_equal(displays[1], displays[-1])
    destroy.assert_called_once()
