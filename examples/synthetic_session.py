"""Generate an explicitly synthetic session to try the viewer without hardware."""
import argparse
import time

import numpy as np
from thermalmaster_p3.frame import Frame
from thermalmaster_p3.recording import SessionWriter

parser = argparse.ArgumentParser()
parser.add_argument('output')
args = parser.parse_args()
y, x = np.mgrid[:192, :256]
utc, mono = time.time_ns(), time.monotonic_ns()
with SessionWriter(args.output, {'synthetic': True}) as writer:
    for i in range(100):
        temperature = 20 + 35 * np.exp(-((x - 90 - i / 2) ** 2 + (y - 96) ** 2) / 800)
        raw = np.rint((temperature + 273.15) * 64).astype(np.uint16)
        ir = np.clip((temperature - 20) * 7, 0, 255).astype(np.uint8)
        writer.write(Frame(raw, ir, np.zeros((2, 256), np.uint16), i,
                           mono + i * 40000000, utc + i * 40000000,
                           (i, 0, (i * 40) % 2048), (i, 0, ((i + 1) * 40) % 2048)))
