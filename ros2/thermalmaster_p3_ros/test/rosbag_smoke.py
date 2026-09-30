"""Linux CI: simulated camera record/play smoke test, no USB required."""
import os
import signal
import subprocess
import tempfile
import time
import numpy as np
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
import thermalmaster_p3_ros.node as module
from thermalmaster_p3.frame import Frame
from thermalmaster_p3.protocol import FrameParser


class FakeCamera:
    def __init__(self, **kwargs):
        self.parser, self.timeouts, self.sequence = FrameParser(), 0, 0
    def open(self): pass
    def start(self): pass
    def set_gain(self, gain): pass
    def trigger_nuc(self): pass
    def close(self): pass
    def read_frame(self, timeout):
        time.sleep(.04)
        self.sequence += 1
        return Frame(np.full((192, 256), 19082, np.uint16), np.zeros((192, 256), np.uint8),
                     np.zeros((2, 256), np.uint16), self.sequence, time.monotonic_ns(),
                     time.time_ns(), (1, 0, 0), (1, 0, 40))


def stop(process):
    if process.poll() is None:
        os.killpg(process.pid, signal.SIGINT)
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=5)


def main():
    module.Camera = FakeCamera
    rclpy.init()
    node = module.P3Node()
    observer = rclpy.create_node('p3_bag_observer')
    executor = SingleThreadedExecutor()
    executor.add_node(node)
    executor.add_node(observer)
    frames = []
    subscription = observer.create_subscription(Image, 'thermal/raw', frames.append, qos_profile_sensor_data)
    processes = []
    try:
        with tempfile.TemporaryDirectory() as directory:
            bag = os.path.join(directory, 'bag')
            record = subprocess.Popen(['ros2', 'bag', 'record', '-o', bag, '/thermal/raw',
                                       '/thermal/temperature', '/thermal/ir', '/thermal/camera_info',
                                       '/diagnostics'], start_new_session=True)
            processes.append(record)
            deadline = time.monotonic() + 8
            while time.monotonic() < deadline:
                executor.spin_once(timeout_sec=.1)
            stop(record)
            # Older ros2 CLI wrappers propagate SIGINT instead of returning 0.
            # Validate the finalized bag and actual playback below as well.
            # Foxy's ros2cli.cli.main explicitly returns signal.SIGINT (2) on
            # KeyboardInterrupt: github.com/ros2/ros2cli/blob/foxy/ros2cli/ros2cli/cli.py
            accepted = (0, -signal.SIGINT, 128 + signal.SIGINT)
            if os.environ.get('ROS_DISTRO') == 'foxy':
                accepted += (signal.SIGINT,)
            assert record.returncode in accepted, (
                'Recorder failed with exit code ' + str(record.returncode))
            executor.remove_node(node)
            node.destroy_node()
            node = None
            for _ in range(20):
                executor.spin_once(timeout_sec=.02)
            frames.clear()
            info = subprocess.check_output(['ros2', 'bag', 'info', bag], text=True)
            assert '/thermal/raw' in info and '/thermal/temperature' in info, info
            play = subprocess.Popen(['ros2', 'bag', 'play', bag], start_new_session=True)
            processes.append(play)
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline and (play.poll() is None or not frames):
                executor.spin_once(timeout_sec=.1)
            stop(play)
            assert frames and frames[0].encoding == '16UC1', 'No raw image replayed'
            print('Simulated P3 rosbag2 record/play passed')
    finally:
        for process in processes:
            stop(process)
        executor.shutdown()
        observer.destroy_node()
        if node:
            node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
