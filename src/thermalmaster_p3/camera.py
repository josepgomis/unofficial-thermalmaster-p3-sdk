import threading
import time
import math
from dataclasses import dataclass
from functools import lru_cache
from typing import List, Optional

from .errors import (CameraStateError, DeviceDisconnectedError, DeviceNotFoundError,
                     DevicePermissionError, FrameTimeoutError, ProtocolError)
from .frame import Frame
from .protocol import VID, PID, WIRE_SIZE, FrameParser, command

USB_HELP = ('USB setup: https://github.com/josepgomis/unofficial-thermalmaster-p3-sdk/blob/main/docs/usb.md '
            'Windows requires libusb and WinUSB on the P3 interfaces; '
            'Linux requires the P3 udev rule. Close other camera applications.')


@lru_cache(maxsize=1)
def _usb():
    try:
        import usb.core
        import usb.util
        import usb.backend.libusb1
    except ImportError as exc:
        raise DevicePermissionError('Install pyusb. ' + USB_HELP) from exc
    backend = None
    try:
        import libusb_package
        backend = usb.backend.libusb1.get_backend(find_library=libusb_package.find_library)
    except ImportError:
        backend = usb.backend.libusb1.get_backend()
    if backend is None:
        raise DevicePermissionError('libusb backend not available. ' + USB_HELP)
    return usb.core, usb.util, backend


def _translate(exc: Exception):
    if getattr(exc, 'errno', None) in (19,) or getattr(exc, 'backend_error_code', None) == -4:
        return DeviceDisconnectedError('P3 disconnected; reconnect and reopen it.')
    if getattr(exc, 'errno', None) in (2, 13, 16) or getattr(exc, 'backend_error_code', None) in (-3, -5, -6, -12):
        return DevicePermissionError(str(exc) + '. ' + USB_HELP)
    return ProtocolError(str(exc) + '. ' + USB_HELP)


@dataclass(frozen=True)
class DeviceInfo:
    bus: Optional[int]
    address: Optional[int]
    path: str
    serial: Optional[str]


def _path(device) -> str:
    ports = getattr(device, 'port_numbers', None)
    return '{}:{}'.format(device.bus, '.'.join(map(str, ports)) if ports else device.address)


def list_devices() -> List[DeviceInfo]:
    core, util, backend = _usb()
    devices = []
    try:
        for dev in core.find(find_all=True, idVendor=VID, idProduct=PID, backend=backend):
            serial = None
            try:
                serial = dev.serial_number
            except (core.USBError, ValueError):
                pass
            finally:
                util.dispose_resources(dev)
            devices.append(DeviceInfo(dev.bus, dev.address, _path(dev), serial))
    except core.USBError as exc:
        raise _translate(exc) from exc
    return devices


class Camera:
    def __init__(self, serial: Optional[str] = None, path: Optional[str] = None) -> None:
        self.serial, self.path = serial, path
        self._lock = threading.RLock()
        self._device = None
        self._claimed = []
        self._detached = []
        self._streaming = False
        self.parser = FrameParser()
        self.info = {}
        self.gain = None
        self.timeouts = 0

    def _require_open(self):
        if self._device is None:
            raise CameraStateError('Camera is closed; call open() first.')

    def _exchange(self, payload: bytes, length: int = 0) -> bytes:
        dev = self._device
        dev.ctrl_transfer(0x41, 0x20, 0, 0, payload, timeout=1000)
        status = bytes(dev.ctrl_transfer(0xC1, 0x22, 0, 0, 1, timeout=1000))
        # Firmware 00.00.02.18 returns 0x03 for write-only gain/NUC commands.
        # Reads still require the documented write-then-read status sequence.
        if status not in ((b'\x02', b'\x03') if not length else (b'\x02',)):
            raise ProtocolError('Unexpected command acknowledgment: {!r}'.format(status))
        if not length:
            return b''
        data = bytes(dev.ctrl_transfer(0xC1, 0x21, 0, 0, length, timeout=1000))
        status = bytes(dev.ctrl_transfer(0xC1, 0x22, 0, 0, 1, timeout=1000))
        if status != b'\x03' or len(data) != length:
            raise ProtocolError('Invalid register response or acknowledgment')
        return data

    def open(self) -> 'Camera':
        with self._lock:
            if self._device is not None:
                return self
            core, util, backend = _usb()
            enumerated = []
            try:
                enumerated = list(core.find(find_all=True, idVendor=VID, idProduct=PID, backend=backend))
                candidates = enumerated
                if self.path:
                    candidates = [d for d in candidates if _path(d) == self.path]
                if self.serial:
                    candidates = [d for d in candidates if d.serial_number == self.serial]
                if not candidates:
                    raise DeviceNotFoundError('No matching P3 (3474:45a2). Check cable and run p3 devices.')
                if len(candidates) > 1:
                    raise CameraStateError('Multiple P3 cameras; specify serial or path.')
                self._device = candidates[0]
                dev = self._device
                for interface in (0, 1):
                    try:
                        if dev.is_kernel_driver_active(interface):
                            dev.detach_kernel_driver(interface)
                            self._detached.append(interface)
                    except NotImplementedError:
                        pass
                try:
                    dev.get_active_configuration()
                except core.USBError:
                    dev.set_configuration()
                for interface in (0, 1):
                    util.claim_interface(dev, interface)
                    self._claimed.append(interface)
                cfg = dev.get_active_configuration()
                endpoints = [e for e in cfg[(1, 1)] if e.bEndpointAddress == 0x81 and (e.bmAttributes & 3) == 2]
                if not endpoints:
                    raise ProtocolError('P3 requires bulk IN 0x81 on interface 1 alt 1.')
                for name, register, length in [('model', 1, 30), ('firmware', 2, 12), ('serial', 7, 64)]:
                    value = self._exchange(command(0x0101, 0x81, register, length), length)
                    self.info[name] = value.split(b'\0')[0].decode('utf-8', errors='replace')
                return self
            except Exception as exc:
                self.close()
                if isinstance(exc, core.USBError):
                    raise _translate(exc) from exc
                raise
            finally:
                for device in enumerated:
                    if device is not self._device:
                        util.dispose_resources(device)

    def start(self) -> None:
        with self._lock:
            self._require_open()
            if self._streaming:
                return
            core, _, _ = _usb()
            try:
                self._start_command()
                time.sleep(1)
                self._device.set_interface_altsetting(interface=1, alternate_setting=1)
                self._device.ctrl_transfer(0x40, 0xEE, 0, 1, None, timeout=1000)
                time.sleep(2)
                try:
                    self._device.read(0x81, WIRE_SIZE + 16384, timeout=100)
                except core.USBTimeoutError:
                    pass
                self._start_command()
                self.parser = FrameParser()
                self._streaming = True
            except core.USBError as exc:
                self.close()
                raise _translate(exc) from exc
            except Exception:
                self.close()
                raise

    def _start_command(self):
        response = self._exchange(command(0x012f, 0x81, length=1), 1)
        if response not in (b'\x01', b'\x35'):
            raise ProtocolError('Unexpected stream response: {!r}'.format(response))

    def read_frame(self, timeout: float = 2.0) -> Frame:
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError('timeout must be positive and finite')
        with self._lock:
            self._require_open()
            if not self._streaming:
                raise CameraStateError('Call start() before read_frame().')
            core, _, _ = _usb()
            deadline = time.monotonic() + timeout
            while True:
                frame = self.parser.pop()
                if frame is not None:
                    return frame
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    self.timeouts += 1
                    raise FrameTimeoutError('No complete valid P3 frame within timeout.')
                try:
                    # Oversized reads accommodate the documented 204800-byte NUC transfer.
                    chunk = self._device.read(0x81, WIRE_SIZE + 16384,
                                              timeout=max(1, int(min(remaining, .25) * 1000)))
                    self.parser.feed(bytes(chunk))
                except core.USBTimeoutError:
                    continue
                except core.USBError as exc:
                    # WinUSB can report generic I/O when a claimed device is
                    # unplugged. Classify it as disconnect only after checking
                    # that the selected USB bus/address is no longer present.
                    if getattr(exc, 'errno', None) == 5 or getattr(exc, 'backend_error_code', None) == -1:
                        try:
                            _, _, backend = _usb()
                            present = any(d.bus == self._device.bus and d.address == self._device.address
                                          for d in core.find(find_all=True, idVendor=VID, idProduct=PID, backend=backend))
                        except core.USBError:
                            present = True
                        if not present:
                            raise DeviceDisconnectedError('P3 disconnected; reconnect and reopen it.') from exc
                    raise _translate(exc) from exc

    def set_gain(self, gain: str) -> None:
        if gain not in ('high', 'low'):
            raise ValueError('gain must be high or low')
        with self._lock:
            self._require_open()
            core, _, _ = _usb()
            try:
                self._exchange(command(0x012f, 0x41, int(gain == 'high')))
                self.gain = gain
            except core.USBError as exc:
                raise _translate(exc) from exc

    def trigger_nuc(self) -> None:
        with self._lock:
            self._require_open()
            core, _, _ = _usb()
            try:
                self._exchange(command(0x0136, 0x43))
                self.parser.buffer.clear()
                self.parser.ready.clear()
            except core.USBError as exc:
                raise _translate(exc) from exc

    def stop(self) -> None:
        with self._lock:
            if self._device is None:
                return
            core, _, _ = _usb()
            try:
                self._device.set_interface_altsetting(interface=1, alternate_setting=0)
            except core.USBError as exc:
                raise _translate(exc) from exc
            finally:
                self._streaming = False
                self.parser.buffer.clear()
                self.parser.ready.clear()

    def close(self) -> None:
        with self._lock:
            if self._device is None:
                return
            _, util, _ = _usb()
            dev = self._device
            try:
                dev.set_interface_altsetting(interface=1, alternate_setting=0)
            except Exception:
                pass
            for interface in reversed(self._claimed):
                try:
                    util.release_interface(dev, interface)
                except Exception:
                    pass
            for interface in self._detached:
                try:
                    dev.attach_kernel_driver(interface)
                except Exception:
                    pass
            try:
                util.dispose_resources(dev)
            except Exception:
                pass
            finally:
                self._device = None
                self._claimed.clear()
                self._detached.clear()
                self._streaming = False
                self.parser.buffer.clear()
                self.parser.ready.clear()

    def __enter__(self) -> 'Camera':
        return self.open()

    def __exit__(self, *args) -> None:
        self.close()
