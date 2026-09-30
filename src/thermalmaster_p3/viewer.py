"""Optional OpenCV viewer. Display processing never changes radiometric arrays."""
import time
from collections import deque
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

import numpy as np

from .errors import P3Error, FrameTimeoutError
from .recording import SessionWriter

WIDTH, HEIGHT, SCALE = 768, 576, 3
LEGEND_HEIGHT, PANEL_HEIGHT = 60, 170
PALETTES = ('Inferno', 'Jet', 'Bone')
TITLE = 'Unofficial Thermal Master P3'


def _cv2():
    try:
        import cv2
    except ImportError as exc:
        raise ImportError('Install OpenCV with: pip install "unofficial-thermalmaster-p3[viewer] @ '
                          'git+https://github.com/josepgomis/unofficial-thermalmaster-p3-sdk.git@main"') from exc
    return cv2


def _validate_limits(limits):
    if limits is not None and (len(limits) != 2 or not np.isfinite(limits).all() or limits[0] >= limits[1]):
        raise ValueError('Fixed range requires finite MIN_C < MAX_C')


def _colormap(palette):
    cv2 = _cv2()
    return (cv2.COLORMAP_INFERNO, cv2.COLORMAP_JET, cv2.COLORMAP_BONE)[palette % 3]


def render(frame, limits=None, palette=0):
    """Return native-size color image and actual displayed Celsius limits."""
    _validate_limits(limits)
    temperatures = frame.temperature_c
    low, high = limits if limits is not None else np.percentile(temperatures, [1, 99])
    if high <= low:
        high = low + 1
    gray = np.clip((temperatures - low) * 255 / (high - low), 0, 255).astype(np.uint8)
    return _cv2().applyColorMap(gray, _colormap(palette)), float(low), float(high)


@dataclass
class _ViewerState:
    limits: Optional[Tuple[float, float]] = None
    rotation: int = 0
    palette: int = 0
    cursor: Tuple[int, int] = (128, 96)
    roi_start: Optional[Tuple[int, int]] = None
    roi_end: Optional[Tuple[int, int]] = None
    dragging: bool = False
    fixed_limits: Optional[Tuple[float, float]] = None
    displayed_limits: Tuple[float, float] = (0., 1.)
    fps_times: deque = field(default_factory=lambda: deque(maxlen=100))

    def __post_init__(self):
        _validate_limits(self.limits)
        if self.rotation not in (0, 180):
            raise ValueError('Display rotation must be 0 or 180 degrees')
        self.fixed_limits = self.limits

    def toggle_scale(self):
        if self.limits is None:
            self.limits = self.fixed_limits or self.displayed_limits
            self.fixed_limits = self.limits
        else:
            self.fixed_limits, self.limits = self.limits, None

    def mouse(self, event, x, y, flags=0, param=None):
        cv2 = _cv2()
        if not (0 <= x < WIDTH and 0 <= y < HEIGHT):
            if event == cv2.EVENT_LBUTTONUP:
                self.dragging = False
            return
        point = (x // SCALE, y // SCALE)
        if self.rotation == 180:
            point = (255 - point[0], 191 - point[1])
        self.cursor = point
        if event == cv2.EVENT_LBUTTONDOWN:
            self.roi_start, self.roi_end, self.dragging = point, point, True
        elif event == cv2.EVENT_MOUSEMOVE and self.dragging:
            self.roi_end = point
        elif event == cv2.EVENT_LBUTTONUP and self.dragging:
            self.roi_end, self.dragging = point, False

    def clear_roi(self):
        self.roi_start, self.roi_end, self.dragging = None, None, False

    def received(self, now):
        self.fps_times.append(now)
        while len(self.fps_times) > 2 and now - self.fps_times[0] > 2:
            self.fps_times.popleft()

    @property
    def fps(self):
        if len(self.fps_times) < 2:
            return None
        return (len(self.fps_times) - 1) / max(.001, self.fps_times[-1] - self.fps_times[0])


def _roi_stats(frame, state):
    if state.roi_start is None or state.roi_end is None:
        return None
    x0, x1 = sorted((state.roi_start[0], state.roi_end[0]))
    y0, y1 = sorted((state.roi_start[1], state.roi_end[1]))
    values = frame.temperature_c[y0:y1 + 1, x0:x1 + 1]
    return (x0, y0, x1, y1), (float(values.min()), float(values.mean()), float(values.max()))


def _compose(frame, state, source='REPLAY', status='READY', gain=None, recording=False, message=''):
    """Shipped composition, also used for reproducible real-session exports."""
    cv2 = _cv2()
    canvas = np.full((HEIGHT + LEGEND_HEIGHT + PANEL_HEIGHT, WIDTH, 3), 24, np.uint8)
    white, muted, accent = (244, 244, 244), (190, 190, 190), (110, 210, 255)

    def text(value, x, y, size=.52, color=white):
        cv2.putText(canvas, value, (x, y), cv2.FONT_HERSHEY_SIMPLEX, size, color, 1, cv2.LINE_AA)

    stale = status in ('TIMEOUT', 'DISCONNECTED', 'ERROR')
    if frame is not None:
        native, low, high = render(frame, state.limits, state.palette)
        state.displayed_limits = low, high
        if state.rotation == 180:
            native = cv2.rotate(native, cv2.ROTATE_180)
        thermal = cv2.resize(native, (WIDTH, HEIGHT), interpolation=cv2.INTER_NEAREST)
        canvas[:HEIGHT] = (thermal.astype(np.float32) * .3).astype(np.uint8) if stale else thermal
        cx, cy = state.cursor
        if state.rotation == 180:
            cx, cy = 255 - cx, 191 - cy
        x, y = cx * SCALE + 1, cy * SCALE + 1
        for color, thickness in (((0, 0, 0), 3), (white, 1)):
            cv2.line(canvas, (max(0, x - 9), y), (min(WIDTH - 1, x + 9), y), color, thickness)
            cv2.line(canvas, (x, max(0, y - 9)), (x, min(HEIGHT - 1, y + 9)), color, thickness)
        stats = _roi_stats(frame, state)
        if stats:
            (x0, y0, x1, y1), _ = stats
            if state.rotation == 180:
                x0, y0, x1, y1 = 255 - x1, 191 - y1, 255 - x0, 191 - y0
            for color, thickness in (((0, 0, 0), 3), (white, 1)):
                cv2.rectangle(canvas, (x0 * SCALE, y0 * SCALE),
                              (x1 * SCALE + 2, y1 * SCALE + 2), color, thickness)
        ramp = np.tile(np.linspace(0, 255, 480, dtype=np.uint8), (16, 1))
        canvas[HEIGHT + 12:HEIGHT + 28, 18:498] = cv2.applyColorMap(ramp, _colormap(state.palette))
        text('{:.1f} C'.format(low), 18, HEIGHT + 49, .48)
        text('{:.1f} C'.format(high), 410, HEIGHT + 49, .48)
        text(PALETTES[state.palette % 3], 530, HEIGHT + 25, .58)
        text(('AUTO (1-99%)' if state.limits is None else 'FIXED') +
             (' / 180' if state.rotation else ''), 530, HEIGHT + 49, .48, muted)
    else:
        canvas[:HEIGHT] = 0
        text('Waiting for P3 frames', 220, 280, .85)
        text('USB startup normally takes about 3 seconds', 170, 313, .55, muted)
    base = HEIGHT + LEGEND_HEIGHT
    text(source + '  |  ' + status + ('  |  REC' if recording else ''), 18, base + 25, .61,
         accent if stale or recording else white)
    rate = '--' if state.fps is None or stale else '{:.1f}'.format(state.fps)
    text('Recent FPS ' + rate + '  |  gain ' + (gain or '--'), 440, base + 25, .48, muted)
    if frame is not None:
        x, y = state.cursor
        text('Cursor ({}, {})  {:.2f} C{}'.format(x, y, frame.temperature_c[y, x],
             ' [STALE]' if stale else ''), 18, base + 53, .6)
        stats = _roi_stats(frame, state)
        roi = ('ROI  min {:.2f}  mean {:.2f}  max {:.2f} C'.format(*stats[1]) if stats
               else 'Drag on the image to measure a ROI')
        text(roi, 18, base + 79, .52, muted)
    text('p palette   a auto/fixed   c clear ROI   i PNG   s raw snapshot', 18, base + 108, .47, muted)
    text('r record   n NUC (live)   g gain (live)   q quit', 18, base + 130, .47, muted)
    if len(message) > 93:
        message = message[:44] + ' ... ' + message[-44:]
    text(message, 18, base + 155, .44, accent)
    return canvas


def _export_png(image, output):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if not _cv2().imwrite(str(output), image):
        raise OSError('Could not write PNG: ' + str(output))
    return output


def _output_path(suffix, prefix='capture'):
    return Path('sessions') / (prefix + '-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f') + suffix)


def run_viewer(camera=None, frames=None, limits=None, source_label='REPLAY', rotation=0):
    """Display live or replay frames; close recording, window and camera on exit."""
    cv2 = _cv2()
    if (camera is None) == (frames is None):
        raise ValueError('Supply exactly one camera or frame iterator')
    state = _ViewerState(limits=tuple(limits) if limits is not None else None, rotation=rotation)
    iterator = iter(frames) if frames is not None else None
    source = source_label if iterator is not None else 'LIVE'
    writer, frame, previous_time = None, None, None
    status, message, ended, opened = 'WAITING', '', False, False
    try:
        cv2.namedWindow(TITLE, cv2.WINDOW_AUTOSIZE)
        opened = True
        cv2.setMouseCallback(TITLE, state.mouse)
        cv2.imshow(TITLE, _compose(None, state, source, status))
        print('q quit | p palette | a auto/fixed | c clear ROI | i PNG | s raw | r record | n NUC | g gain')
        while True:
            if not ended:
                try:
                    candidate = next(iterator) if iterator is not None else camera.read_frame(timeout=.1)
                    if iterator is not None and previous_time is not None:
                        time.sleep(min(.2, max(0, (candidate.monotonic_ns - previous_time) / 1e9)))
                    frame, previous_time = candidate, candidate.monotonic_ns
                    state.received(time.monotonic())
                    if status in ('TIMEOUT', 'NUC'):
                        message = 'Valid frames resumed' if status == 'TIMEOUT' else 'Valid frame received after NUC'
                    status = 'READY' if iterator is not None else 'STREAMING'
                    if writer:
                        writer.write(frame)
                except StopIteration:
                    status, message, ended = 'FINISHED', 'Replay finished. i export PNG, q close.', True
                    if writer:
                        writer.close()
                        writer = None
                except FrameTimeoutError:
                    status, message = 'TIMEOUT', 'No new frame; retained measurements are stale. Check USB.'
                except P3Error as exc:
                    status, message, ended = 'DISCONNECTED', str(exc), True
                    if camera:
                        camera.close()
                    if writer:
                        writer.close()
                        writer = None
            display = _compose(frame, state, source, status, getattr(camera, 'gain', None), bool(writer), message)
            cv2.imshow(TITLE, display)
            key = cv2.waitKey(30 if ended else 1) & 255
            if key == ord('q') or cv2.getWindowProperty(TITLE, cv2.WND_PROP_VISIBLE) < 1:
                break
            try:
                if key == ord('p'):
                    state.palette = (state.palette + 1) % 3
                elif key == ord('a') and frame is not None:
                    state.toggle_scale()
                elif key == ord('c'):
                    state.clear_roi()
                elif key == ord('i') and frame is not None:
                    message = 'PNG: ' + str(_export_png(display, _output_path('.png', 'viewer')))
                elif key == ord('s') and frame is not None:
                    output = _output_path('.npz')
                    output.parent.mkdir(exist_ok=True)
                    np.savez_compressed(output, **asdict(frame), temperature_c=frame.temperature_c)
                    message = 'Radiometric snapshot: ' + str(output)
                elif key == ord('r') and not ended:
                    if writer:
                        writer.close()
                        writer = None
                        message = 'Recording finalized'
                    else:
                        output = _output_path('', 'recording')
                        output.parent.mkdir(exist_ok=True)
                        writer = SessionWriter(output, {'source': source, 'synthetic': 'SYNTHETIC' in source,
                                               'gain': getattr(camera, 'gain', None)})
                        message = 'Recording: ' + str(output)
                elif camera is not None and not ended and key in (ord('n'), ord('g')):
                    if key == ord('n'):
                        camera.trigger_nuc()
                        status, message = 'NUC', 'NUC acknowledged; waiting for the next valid frame.'
                        if writer:
                            writer.event('nuc', {})
                    else:
                        camera.set_gain('low' if camera.gain == 'high' else 'high')
                        message = 'Gain acknowledged: ' + camera.gain
                        if writer:
                            writer.event('gain', {'gain': camera.gain})
            except (P3Error, OSError) as exc:
                message = str(exc)
                if isinstance(exc, P3Error):
                    status, ended = 'ERROR', True
                    camera.close()
            if key in (ord('n'), ord('g')):
                cv2.imshow(TITLE, _compose(frame, state, source, status,
                           getattr(camera, 'gain', None), bool(writer), message))
                cv2.waitKey(1)
    finally:
        try:
            if writer:
                writer.close()
        finally:
            try:
                if camera is not None:
                    camera.close()
            finally:
                if opened:
                    cv2.destroyWindow(TITLE)
