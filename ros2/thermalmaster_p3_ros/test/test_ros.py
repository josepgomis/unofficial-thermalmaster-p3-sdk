import time

import numpy as np
import pytest
import rclpy
from sensor_msgs.msg import Image
from std_msgs.msg import Header
from std_srvs.srv import Trigger
from rclpy.qos import qos_profile_sensor_data

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
        def open(self): pass
        def start(self): pass
        def set_gain(self, gain): pass
        def close(self): pass
        def trigger_nuc(self): pass
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
        # The zero-latency fake has no USB pacing. Stop it before testing the
        # service so legacy executors cannot starve service discovery with images.
        node.capture_timer.cancel()
        client = observer.create_client(Trigger, 'thermal/trigger_nuc')
        assert client.wait_for_service(timeout_sec=3)
        future = client.call_async(Trigger.Request())
        deadline = time.monotonic() + 10
        while not future.done() and time.monotonic() < deadline:
            executor.spin_once(timeout_sec=.1)
        assert future.done(), 'NUC service did not respond'
        assert future.result().success
    finally:
        executor.shutdown()
        observer.destroy_node()
        node.destroy_node()
        rclpy.shutdown()
