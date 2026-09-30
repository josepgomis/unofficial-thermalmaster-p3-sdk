"""Optional lightweight OpenCV viewer; SDK imports never load cv2."""
import time
from datetime import datetime
from pathlib import Path

import numpy as np

from .errors import FrameTimeoutError
from .recording import SessionWriter


def _cv2():
    try:
        import cv2
    except ImportError as exc:
        raise ImportError('Install the viewer extra: pip install "unofficial-thermalmaster-p3[viewer]"') from exc
    return cv2


def render(frame, limits=None, palette=0):
    cv2 = _cv2()
    if limits is not None and (len(limits) != 2 or not np.isfinite(limits).all() or limits[0] >= limits[1]):
        raise ValueError('Fixed range requires finite MIN_C < MAX_C')
    temperatures = frame.temperature_c
    low, high = limits if limits is not None else np.percentile(temperatures, [1, 99])
    if high <= low:
        high = low + 1
    gray = np.clip((temperatures - low) * 255 / (high - low), 0, 255).astype(np.uint8)
    palettes = (cv2.COLORMAP_INFERNO, cv2.COLORMAP_JET, cv2.COLORMAP_BONE)
    return cv2.applyColorMap(gray, palettes[palette % len(palettes)]), float(low), float(high)


def run_viewer(camera=None, frames=None, limits=None, source_label='REPLAY'):
    cv2 = _cv2()
    if (camera is None) == (frames is None):
        raise ValueError('Supply exactly one camera or frame iterator')
    if limits is not None and (len(limits) != 2 or not np.isfinite(limits).all() or limits[0] >= limits[1]):
        raise ValueError('Fixed range requires finite MIN_C < MAX_C')
    title = 'Unofficial Thermal Master P3'
    cursor = [128, 96]
    drag = [None, None, False]
    scale = 3
    writer = None
    palette = 0
    iterator = iter(frames) if frames is not None else None
    cv2.namedWindow(title, cv2.WINDOW_AUTOSIZE)

    def mouse(event, x, y, flags, param):
        point = (min(255, max(0, x // scale)), min(191, max(0, y // scale)))
        cursor[:] = point
        if event == cv2.EVENT_LBUTTONDOWN:
            drag[:] = [point, point, True]
        elif event == cv2.EVENT_MOUSEMOVE and drag[2]:
            drag[1] = point
        elif event == cv2.EVENT_LBUTTONUP:
            drag[1], drag[2] = point, False

    cv2.setMouseCallback(title, mouse)
    started = time.monotonic()
    count = 0
    previous_time = None
    message = ''
    last_display = np.zeros((696, 768, 3), dtype=np.uint8)
    cv2.putText(last_display, 'Waiting for thermal frames...', (20, 620), cv2.FONT_HERSHEY_SIMPLEX,
                .6, (240, 240, 240), 1, cv2.LINE_AA)
    cv2.imshow(title, last_display)
    print('q quit | p palette | s snapshot | r record | n NUC | g gain | drag ROI')
    try:
        while True:
            try:
                frame = next(iterator) if iterator is not None else camera.read_frame(timeout=.5)
            except StopIteration:
                break
            except FrameTimeoutError:
                stale = last_display.copy()
                stale[576:] = 0
                cv2.putText(stale, 'No new frame: check USB connection. q quit', (10, 610),
                            cv2.FONT_HERSHEY_SIMPLEX, .6, (240, 240, 240), 1, cv2.LINE_AA)
                cv2.imshow(title, stale)
                if cv2.waitKey(1) & 255 == ord('q') or cv2.getWindowProperty(title, cv2.WND_PROP_VISIBLE) < 1:
                    break
                continue
            if iterator is not None and previous_time is not None:
                time.sleep(min(.2, max(0, (frame.monotonic_ns - previous_time) / 1e9)))
            previous_time = frame.monotonic_ns
            if writer:
                writer.write(frame)
            count += 1
            image, low, high = render(frame, limits, palette)
            image = cv2.resize(image, (768, 576), interpolation=cv2.INTER_NEAREST)
            temp = frame.temperature_c
            lines = ['{:.1f} to {:.1f} C | {:.1f} fps | {}'.format(low, high, count / max(.001, time.monotonic() - started),
                     ('REC | ' if writer else '') + (source_label if iterator else 'LIVE | gain ' + str(camera.gain))),
                     '({}, {}) {:.2f} C'.format(cursor[0], cursor[1], temp[cursor[1], cursor[0]])]
            if drag[0] is not None:
                x0, x1 = sorted((drag[0][0], drag[1][0]))
                y0, y1 = sorted((drag[0][1], drag[1][1]))
                roi = temp[y0:y1 + 1, x0:x1 + 1]
                cv2.rectangle(image, (x0 * scale, y0 * scale), (x1 * scale, y1 * scale), (255, 255, 255), 1)
                lines.append('ROI min {:.2f} mean {:.2f} max {:.2f} C'.format(roi.min(), roi.mean(), roi.max()))
            lines.extend(['q quit  p palette  s snapshot  r record  n NUC  g gain', message])
            panel = np.zeros((120, 768, 3), dtype=np.uint8)
            for i, line in enumerate(lines):
                cv2.putText(panel, line, (10, 20 + 23 * i), cv2.FONT_HERSHEY_SIMPLEX, .48, (240, 240, 240), 1, cv2.LINE_AA)
            last_display = np.vstack((image, panel))
            cv2.imshow(title, last_display)
            key = cv2.waitKey(1) & 255
            if key == ord('q') or cv2.getWindowProperty(title, cv2.WND_PROP_VISIBLE) < 1:
                break
            if key == ord('p'):
                palette += 1
            if key == ord('s'):
                from dataclasses import asdict
                directory = Path('sessions')
                directory.mkdir(exist_ok=True)
                output = directory / ('capture-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.npz')
                np.savez_compressed(output, **asdict(frame), temperature_c=frame.temperature_c)
                message = str(output)
            if key == ord('r'):
                if writer:
                    writer.close()
                    writer = None
                else:
                    Path('sessions').mkdir(exist_ok=True)
                    output = Path('sessions') / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
                    writer = SessionWriter(output, {'source': 'replay' if iterator else camera.info,
                                                   'gain': None if iterator else camera.gain})
                    message = str(output)
            if camera is not None and key == ord('n'):
                camera.trigger_nuc()
                if writer:
                    writer.event('nuc', {})
            if camera is not None and key == ord('g'):
                camera.set_gain('low' if camera.gain == 'high' else 'high')
                if writer:
                    writer.event('gain', {'gain': camera.gain})
    finally:
        if writer:
            writer.close()
        cv2.destroyWindow(title)
