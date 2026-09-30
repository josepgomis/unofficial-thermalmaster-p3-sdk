from unittest.mock import MagicMock

import pytest
import usb.core

import thermalmaster_p3.camera as module
from thermalmaster_p3 import (Camera, CameraStateError, DeviceDisconnectedError,
                             DevicePermissionError, FrameTimeoutError, DeviceNotFoundError)
from test_protocol import wire


@pytest.fixture
def transport(monkeypatch):
    dev = MagicMock()
    dev.bus, dev.address, dev.port_numbers, dev.serial_number = 1, 2, (3,), 'abc'
    dev.is_kernel_driver_active.return_value = True
    endpoint = MagicMock()
    endpoint.bEndpointAddress, endpoint.bmAttributes = 0x81, 2
    dev.get_active_configuration.return_value.__getitem__.return_value = [endpoint]
    core = MagicMock()
    core.USBError, core.USBTimeoutError = usb.core.USBError, usb.core.USBTimeoutError
    core.find.return_value = [dev]
    util = MagicMock()
    def ctrl(request_type, request, value, index, payload, timeout):
        if request == 0x22:
            return b'\x02' if dev._last_request == 0x20 else b'\x03'
        dev._last_request = request
        if request == 0x21:
            return b'\x01' if payload == 1 else b'P3' + bytes(payload - 2)
        return 0
    dev.ctrl_transfer.side_effect = ctrl
    dev.read.return_value = wire()
    monkeypatch.setattr(module, '_usb', lambda: (core, util, None))
    monkeypatch.setattr(module.time, 'sleep', lambda _: None)
    return dev, core, util


def test_lifecycle_and_cleanup(transport):
    dev, _, util = transport
    camera = Camera(path='1:3')
    with camera:
        camera.start()
        camera.set_gain('low')
        camera.trigger_nuc()
        assert camera.read_frame().raw.shape == (192, 256)
        camera.stop()
        with pytest.raises(CameraStateError):
            camera.read_frame()
    assert camera._device is None
    assert util.release_interface.call_count == 2
    assert dev.attach_kernel_driver.call_count == 2
    camera.close()


def test_missing_and_multiple_devices(transport):
    dev, core, _ = transport
    core.find.return_value = []
    with pytest.raises(DeviceNotFoundError):
        Camera().open()
    core.find.return_value = [dev, dev]
    with pytest.raises(CameraStateError):
        Camera().open()


def test_timeout_and_unplug(transport):
    dev, _, _ = transport
    with Camera() as camera:
        camera.start()
        dev.read.side_effect = usb.core.USBTimeoutError('timeout')
        with pytest.raises(FrameTimeoutError):
            camera.read_frame(.01)
        assert camera.timeouts == 1
        dev.read.side_effect = usb.core.USBError('unplug', error_code=-4)
        with pytest.raises(DeviceDisconnectedError):
            camera.read_frame()


def test_partial_claim_cleanup(transport):
    dev, _, util = transport
    util.claim_interface.side_effect = [None, usb.core.USBError('denied', error_code=-3)]
    camera = Camera()
    with pytest.raises(DevicePermissionError):
        camera.open()
    assert camera._device is None
    util.release_interface.assert_called_once_with(dev, 0)
    assert dev.attach_kernel_driver.call_count == 2


def test_state_and_invalid_gain():
    camera = Camera()
    with pytest.raises(ValueError):
        camera.set_gain('auto')
    with pytest.raises(CameraStateError):
        camera.start()
    with pytest.raises(ValueError):
        camera.read_frame(0)
