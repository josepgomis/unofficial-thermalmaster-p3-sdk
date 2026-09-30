import numpy as np
from thermalmaster_p3 import Camera

with Camera() as camera:
    camera.start()
    temperatures = camera.read_frame().temperature_c
    y, x = np.unravel_index(np.argmax(temperatures), temperatures.shape)
    print('Hottest pixel (x, y, C):', x, y, temperatures[y, x])
    print('Center ROI average (C):', temperatures[80:112, 112:144].mean())
