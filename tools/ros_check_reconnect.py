"""Manual physical ROS unplug/replug acceptance; source the built workspace first."""
import json
import platform
import time
from pathlib import Path

import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image

from thermalmaster_p3 import list_devices
from thermalmaster_p3_ros.node import P3Node


def main():
    report = {'test': 'physical ROS unplug/replug', 'platform': platform.platform(),
              'result': 'pending'}
    rclpy.init()
    node = P3Node()
    observer = rclpy.create_node('p3_reconnect_observer')
    executor = SingleThreadedExecutor()
    executor.add_node(node)
    executor.add_node(observer)
    received = []
    subscription = observer.create_subscription(Image, 'thermal/raw',
        lambda message: received.append((time.monotonic(), message.header.stamp)),
        qos_profile_sensor_data)
    def spin_until(predicate, timeout):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            executor.spin_once(timeout_sec=.1)
            if predicate():
                return
        raise TimeoutError('Reconnect acceptance stage timed out')
    try:
        spin_until(lambda: bool(received), 15)
        original = node.camera
        print('READY: unplug P3; wait for the next message before reconnecting.', flush=True)
        spin_until(lambda: not list_devices(), 120)
        spin_until(lambda: node.camera is None, 15)
        report['disconnect_error'] = node.last_error
        assert node.last_error
        assert original._device is None
        # Drain old DDS samples before recording the return of the new stream.
        until = time.monotonic() + 2
        while time.monotonic() < until:
            executor.spin_once(timeout_sec=.1)
        received.clear()
        print('UNPLUG DETECTED: reconnect P3 now.', flush=True)
        spin_until(lambda: bool(list_devices()), 120)
        connected_stamp = node.get_clock().now().to_msg()
        connected_ns = connected_stamp.sec * 1000000000 + connected_stamp.nanosec
        spin_until(lambda: node.camera is not None and bool(received), 20)
        assert node.camera is not original
        assert all(stamp.sec * 1000000000 + stamp.nanosec >= connected_ns
                   for _, stamp in received), 'Old ROS samples appeared after reconnection'
        report.update(result='passed', received_after_reconnect=len(received),
                      firmware=node.camera.info.get('firmware'),
                      fresh_camera_instance=True, old_samples_after_reconnect=False)
    except BaseException as exc:
        report.update(result='failed', error=str(exc))
        raise
    finally:
        executor.shutdown()
        observer.destroy_node()
        node.destroy_node()
        rclpy.shutdown()
        output = Path('build/ros-reconnect-validation.json')
        output.parent.mkdir(exist_ok=True)
        output.write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
