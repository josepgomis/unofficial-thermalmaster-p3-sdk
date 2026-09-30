"""Capture a real P3 scene for docs and a small identifier-free release sample.

Run only after the scene has been cleared for public sharing. No synthetic fallback.
"""
import json
import argparse
import time
import zipfile
from pathlib import Path

import numpy as np

from thermalmaster_p3 import Camera
from thermalmaster_p3.recording import SessionWriter
from thermalmaster_p3.viewer import _ViewerState, _compose, _export_png


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', default='build/p3-real-sample')
    parser.add_argument('--rotate', type=int, choices=(0, 180), default=180)
    args = parser.parse_args()
    sample = Path(args.session)
    assets = Path('docs/images')
    assets.mkdir(parents=True, exist_ok=True)
    state = _ViewerState(rotation=args.rotate)
    with Camera() as camera:
        camera.start()
        camera.set_gain('high')
        config = {'source': 'physical Thermal Master P3', 'model': camera.info['model'],
                  'firmware': camera.info['firmware'], 'gain': camera.gain,
                  'public_sample': True, 'synthetic': False,
                  'scene': 'user-approved objects', 'timestamp_origin': 'host reception'}
        with SessionWriter(sample, config, block_size=30) as writer:
            for _ in range(30):
                frame = camera.read_frame(timeout=2)
                writer.write(frame)
                state.received(time.monotonic())
        live = _compose(frame, state, 'LIVE', 'STREAMING', camera.gain,
                        message='Real P3 acquisition | host reception timestamps')
        _export_png(live, assets / 'viewer-live.png')
        # Use the same real frame and Celsius scale for all palette comparisons.
        state.limits = state.displayed_limits
        live_fps = state.fps
        state.fps_times.clear()
        state.roi_start, state.roi_end = (80, 56), (176, 136)
        panels = []
        for palette in range(3):
            state.palette = palette
            panel = _compose(frame, state, 'REPLAY', 'READY', camera.gain,
                             message='Same real frame and fixed Celsius range | no synthetic data')
            panels.append(panel)
        _export_png(panels[0], assets / 'viewer-roi.png')
        _export_png(np.hstack(panels), assets / 'viewer-palettes.png')
        provenance = {'model': camera.info['model'], 'firmware': camera.info['firmware'],
                      'source': 'physical camera', 'frames': 30, 'gain': camera.gain,
                      'display_rotation_degrees': args.rotate,
                      'fps_recent': live_fps, 'utc_ns': frame.utc_ns,
                      'range_c': state.displayed_limits, 'radiometric_accuracy': 'not calibrated',
                      'images': {'viewer-live.png': 'direct live frame composition',
                                 'viewer-roi.png': 'same frame replay composition with ROI',
                                 'viewer-palettes.png': 'same frame replay composition, fixed range'}}
    (assets / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n', encoding='utf-8')
    output = Path('dist/p3-real-sample.zip')
    output.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(sample.iterdir()):
            archive.write(path, 'p3-real-sample/' + path.name)
    if output.stat().st_size >= 10_000_000:
        raise RuntimeError('Public sample must be below 10 MB')
    print(json.dumps({'sample_bytes': output.stat().st_size, 'frames': 30,
                      'firmware': provenance['firmware'], 'images': list(provenance['images'])}))


if __name__ == '__main__':
    main()
