"""Unofficial Thermal Master P3 SDK."""
from .camera import Camera, DeviceInfo, list_devices
from .frame import Frame, raw_to_celsius
from .errors import (P3Error, DeviceNotFoundError, DevicePermissionError,
                     DeviceDisconnectedError, FrameTimeoutError, ProtocolError,
                     CameraStateError)

__version__ = '0.1.0'
__all__ = ['Camera', 'DeviceInfo', 'list_devices', 'Frame', 'raw_to_celsius',
           'P3Error', 'DeviceNotFoundError', 'DevicePermissionError',
           'DeviceDisconnectedError', 'FrameTimeoutError', 'ProtocolError', 'CameraStateError']
