import time

import numpy as np
import pytest
import rclpy
from sensor_msgs.msg import Image
from std_msgs.msg import Header
from std_srvs.srv import Trigger
from rclpy.qos import qos_profile_sensor_data
from rclpy.parameter import Parameter

import thermalmaster_p3_ros.node as module
from thermalmaster_p3.frame import Frame
from thermalmaster_p3.protocol import FrameParser
from thermalmaster_p3_ros.messages import camera_info, image_message


def test_message_types_and_uncalibrated_info():
    header = Header(frame_id='thermal')
    msg = image_message(np.zeros((192, 256), dtype=np.uint16), '16UC1', header)
    assert msg.height == 192 and msg.step == 512 and len(msg.data) == 98304
    assert msg.header.frame_id == 'thermal'
    assert not msg.is_bigendian
    assert camera_info('').k[0] == 0


def test_fake_camera_topics_and_nuc(monkeypatch):
    class FakeCamera:
        def __init__(self, **kwargs):
            self.parser, self.timeouts = FrameParser(), 0
            self.gain, self.nuc_calls = None, 0
        def open(self): pass
        def start(self): pass
        def set_gain(self, gain): self.gain = gain
        def close(self): pass
        def trigger_nuc(self): self.nuc_calls += 1
        def read_frame(self, timeout):
            return Frame(np.full((192, 256), 19082, np.uint16),
                         np.zeros((192, 256), np.uint8), np.zeros((2, 256), np.uint16),
                         0, time.monotonic_ns(), time.time_ns(), (1, 2, 3), (1, 2, 43))
    monkeypatch.setattr(module, 'Camera', FakeCamera)
    rclpy.init()
    node = module.P3Node()
    observer = rclpy.create_node('p3_test_observer')
    executor = rclpy.executors.SingleThreadedExecutor()
    executor.add_node(node)
    executor.add_node(observer)
    received = {}
    subscriptions = [observer.create_subscription(Image, 'thermal/' + name,
                     lambda msg, key=name: received.setdefault(key, msg), qos_profile_sensor_data)
                     for name in ('raw', 'temperature', 'ir')]
    try:
        deadline = time.monotonic() + 10
        while len(received) < 3 and time.monotonic() < deadline:
            executor.spin_once(timeout_sec=.1)
        assert len(received) == 3
        assert {received[k].encoding for k in received} == {'16UC1', '32FC1', 'mono8'}
        headers = [received[k].header for k in received]
        assert all(header == headers[0] for header in headers)
        temperatures = np.frombuffer(received['temperature'].data, dtype='<f4')
        assert np.allclose(temperatures, 19082 / 64 - 273.15, atol=.001)
        # The zero-latency fake has no USB pacing. Stop it before testing the
        # service so legacy executors cannot starve service discovery with images.
        node.capture_timer.cancel()
        assert node.set_parameters([Parameter('gain', value='low')])[0].successful
        assert node.camera.gain == 'low'
        assert node.set_parameters([Parameter('timeout', value=.2)])[0].successful
        assert not node.set_parameters([Parameter('timeout', value=-1.)])[0].successful
        assert not node.set_parameters([Parameter('gain', value='invalid')])[0].successful
        assert not node.set_parameters([Parameter('path', value='1:2')])[0].successful
        client = observer.create_client(Trigger, 'thermal/trigger_nuc')
        assert client.wait_for_service(timeout_sec=3)
        future = client.call_async(Trigger.Request())
        deadline = time.monotonic() + 10
        while not future.done() and time.monotonic() < deadline:
            executor.spin_once(timeout_sec=.1)
        assert future.done(), 'NUC service did not respond'
        assert future.result().success
        assert node.camera.nuc_calls == 1
    finally:
        executor.shutdown()
        observer.destroy_node()
        node.destroy_node()
        rclpy.shutdown()


def test_reconnect_reopens_camera_and_resets_stream(monkeypatch):
    from thermalmaster_p3 import DeviceDisconnectedError, FrameTimeoutError
    instances = []
    class FakeCamera:
        def __init__(self, **kwargs):
            self.parser, self.timeouts = FrameParser(), 0
            self.closed = False
            self.failure = None
            instances.append(self)
        def open(self): pass
        def start(self): pass
        def set_gain(self, gain): pass
        def close(self): self.closed = True
        def read_frame(self, timeout):
            if self.failure:
                raise self.failure
            return Frame(np.full((192, 256), 19082, np.uint16),
                         np.zeros((192, 256), np.uint8), np.zeros((2, 256), np.uint16),
                         0, time.monotonic_ns(), time.time_ns(), (0, 0, 0), (0, 0, 0))
    monkeypatch.setattr(module, 'Camera', FakeCamera)
    rclpy.init()
    node = module.P3Node()
    try:
        node.capture()
        first = node.camera
        assert node.frames == 1
        first.failure = DeviceDisconnectedError('unplugged')
        node.capture()
        assert first.closed and node.camera is None
        assert node.retry_at > time.monotonic()
        node.retry_at = 0
        node.capture()
        assert node.camera is not first and node.frames == 1
        assert len(instances) == 2
        # A persistently stalled stream must also close and reopen.
        second = node.camera
        second.failure = FrameTimeoutError('stalled')
        node.last_frame_at = time.monotonic() - 6
        node.capture()
        assert second.closed and node.camera is None
    finally:
        node.destroy_node()
        rclpy.shutdown()
