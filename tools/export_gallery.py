"""Reproduce the gallery from a real session; no fabricated acquisition rate."""
import argparse
import json
from pathlib import Path

import numpy as np

from thermalmaster_p3.recording import replay
from thermalmaster_p3.viewer import _ViewerState, _compose, _export_png


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('session')
    parser.add_argument('--output', default='docs/images')
    parser.add_argument('--rotate', type=int, choices=(0, 180), default=180)
    args = parser.parse_args()
    manifest = json.loads((Path(args.session) / 'manifest.json').read_text(encoding='utf-8'))
    configuration = manifest['configuration']
    if configuration.get('synthetic') or configuration.get('source') != 'physical Thermal Master P3':
        raise ValueError('Gallery requires a provenance-marked physical P3 recording')
    frame = None
    for frame in replay(args.session):
        pass
    if frame is None:
        raise ValueError('Recording has no frames')
    output = Path(args.output)
    state = _ViewerState(rotation=args.rotate)
    _export_png(_compose(frame, state, 'REPLAY', 'READY', configuration.get('gain'),
                message='Actual P3 recording | display rotation 180 degrees'), output / 'viewer-live.png')
    state.limits = state.displayed_limits
    state.roi_start, state.roi_end = (80, 56), (176, 136)
    panels = []
    for palette in range(3):
        state.palette = palette
        panels.append(_compose(frame, state, 'REPLAY', 'READY', configuration.get('gain'),
                      message='Same real frame and fixed Celsius range | no synthetic data'))
    _export_png(panels[0], output / 'viewer-roi.png')
    _export_png(np.hstack(panels), output / 'viewer-palettes.png')
    provenance = {'model': configuration.get('model'), 'firmware': configuration.get('firmware'),
                  'source': 'physical camera recording', 'frames': manifest['frames'],
                  'display_rotation_degrees': args.rotate, 'utc_ns': frame.utc_ns,
                  'range_c': state.displayed_limits,
                  'images': {name: 'real session replay export' for name in
                             ('viewer-live.png', 'viewer-roi.png', 'viewer-palettes.png')}}
    (output / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
