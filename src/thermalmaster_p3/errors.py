"""Public SDK errors."""


class P3Error(Exception):
    """Base SDK error."""


class DeviceNotFoundError(P3Error):
    pass


class DevicePermissionError(P3Error):
    pass


class DeviceDisconnectedError(P3Error):
    pass


class FrameTimeoutError(P3Error):
    pass


class ProtocolError(P3Error):
    pass


class CameraStateError(P3Error):
    pass
