"""Analyze a recorded physical P3 session; no USB camera is required."""
import argparse
import json

import numpy as np
from thermalmaster_p3.recording import replay


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('session', help='Extracted radiometric session directory')
    args = parser.parse_args()
    first, count = None, 0
    for frame in replay(args.session):
        if first is None:
            first = frame
        count += 1
    if first is None:
        parser.error('Session contains no frames')
    temperature = first.temperature_c
    y, x = np.unravel_index(np.argmax(temperature), temperature.shape)
    roi = temperature[80:112, 112:144]
    print(json.dumps({
        'frames': count, 'shape_yx': list(temperature.shape),
        'dtype': str(temperature.dtype),
        'hottest_pixel': {'x': int(x), 'y': int(y), 'celsius': float(temperature[y, x])},
        'frame_celsius': {'min': float(temperature.min()), 'max': float(temperature.max())},
        'roi_native_xy': [112, 80, 144, 112],
        'roi_celsius': {'min': float(roi.min()), 'mean': float(roi.mean()), 'max': float(roi.max())},
        'timestamp_source': 'host reception',
    }, indent=2))


if __name__ == '__main__':
    main()
