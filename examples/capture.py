"""Run after USB setup: python examples/capture.py"""
from thermalmaster_p3 import Camera

with Camera() as camera:
    camera.start()
    frame = camera.read_frame()
    print('Shape:', frame.raw.shape)
    print('Center temperature (C):', frame.temperature_c[96, 128])
