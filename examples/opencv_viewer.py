from thermalmaster_p3 import Camera
from thermalmaster_p3.viewer import run_viewer

with Camera() as camera:
    camera.start()
    camera.set_gain('high')
    run_viewer(camera=camera)
