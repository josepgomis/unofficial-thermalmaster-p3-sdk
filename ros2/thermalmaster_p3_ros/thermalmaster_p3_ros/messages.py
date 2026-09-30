import math

import numpy as np
import yaml
from sensor_msgs.msg import CameraInfo, Image


def image_message(array, encoding, header):
    msg = Image()
    msg.header = header
    msg.height, msg.width = array.shape
    msg.encoding = encoding
    msg.is_bigendian = False
    dtype = {'16UC1': '<u2', '32FC1': '<f4', 'mono8': 'u1'}[encoding]
    values = np.ascontiguousarray(array, dtype=dtype)
    msg.step = msg.width * values.dtype.itemsize
    msg.data = values.tobytes()
    return msg


def camera_info(filename):
    msg = CameraInfo()
    msg.width, msg.height = 256, 192
    if not filename:
        return msg
    with open(filename, encoding='utf-8') as stream:
        values = yaml.safe_load(stream)
    if values['image_width'] != 256 or values['image_height'] != 192:
        raise ValueError('Calibration must describe native 256x192 images')
    def matrix(key, size):
        data = [float(x) for x in values[key]['data']]
        if len(data) != size or not all(math.isfinite(x) for x in data):
            raise ValueError('Invalid calibration matrix: ' + key)
        return data
    msg.k = matrix('camera_matrix', 9)
    msg.r = matrix('rectification_matrix', 9)
    msg.p = matrix('projection_matrix', 12)
    msg.d = [float(x) for x in values['distortion_coefficients']['data']]
    if not all(math.isfinite(x) for x in msg.d) or msg.k[0] <= 0 or msg.k[4] <= 0:
        raise ValueError('Invalid calibration coefficients')
    msg.distortion_model = values['distortion_model']
    return msg
