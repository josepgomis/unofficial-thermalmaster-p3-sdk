"""Render the actual viewer composition with synthetic input, without a window."""
import cv2
from thermalmaster_p3.recording import replay
from thermalmaster_p3.viewer import run_viewer

cv2.namedWindow = lambda *args: None
cv2.destroyWindow = lambda *args: None
cv2.getWindowProperty = lambda *args: 1
cv2.waitKey = lambda *args: ord('q')
cv2.imshow = lambda title, image: cv2.imwrite('build/viewer-preview.png', image)

def set_mouse(title, callback):
    callback(cv2.EVENT_LBUTTONDOWN, 210, 240, 0, None)
    callback(cv2.EVENT_LBUTTONUP, 390, 345, 0, None)

cv2.setMouseCallback = set_mouse
run_viewer(frames=replay('sessions/synthetic'), source_label='SYNTHETIC REPLAY')
