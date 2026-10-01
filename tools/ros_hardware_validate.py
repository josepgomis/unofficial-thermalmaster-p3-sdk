"""Validate ROS publication and rosbag playback with real P3 data.

Source ROS and the built workspace first. --simulate only validates the harness.
"""
import argparse
import importlib.util
import json
import math
import os
import platform
import signal
import subprocess
import time
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.parameter import Parameter
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CameraInfo, Image
from diagnostic_msgs.msg import DiagnosticArray
from std_srvs.srv import Trigger
import thermalmaster_p3_ros.node as module


def stop(process):
    if process and process.poll() is None:
        os.killpg(process.pid, signal.SIGINT)
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--duration', type=float, default=900.)
    parser.add_argument('--report', default='build/ros-hardware-validation.json')
    parser.add_argument('--bag', required=True, help='New rosbag directory; records first 15 seconds')
    parser.add_argument('--simulate', action='store_true')
    args = parser.parse_args()
    if not math.isfinite(args.duration) or args.duration < 25:
        parser.error('duration must be finite and at least 25 seconds to exercise all controls')
    if Path(args.bag).exists():
        parser.error('bag output already exists')
    if args.simulate:
        source = Path(__file__).resolve().parents[1] / 'ros2/thermalmaster_p3_ros/test/rosbag_smoke.py'
        spec = importlib.util.spec_from_file_location('smoke', source)
        smoke = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(smoke)
        module.Camera = smoke.FakeCamera
    output = Path(args.report)
    output.parent.mkdir(parents=True, exist_ok=True)
    Path(args.bag).parent.mkdir(parents=True, exist_ok=True)
    report = {'result': 'in_progress', 'physical': not args.simulate,
              'platform': platform.platform(), 'python': platform.python_version(),
              'ros_distro': os.environ.get('ROS_DISTRO'), 'numpy': np.__version__,
              'started_utc': datetime.now(timezone.utc).isoformat(),
              'requested_seconds': args.duration, 'frames': 0, 'intervals': [], 'controls': [],
              'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'],
                  cwd=Path(__file__).resolve().parent, text=True).strip()}
    rclpy.init()
    node = module.P3Node()
    observer = rclpy.create_node('p3_acceptance_observer')
    executor = SingleThreadedExecutor()
    executor.add_node(node)
    executor.add_node(observer)
    pending = OrderedDict()
    last_frame = [None]
    max_gap = [0.]
    replay_frames = []
    phase = ['live']
    def receive(kind, message):
        if phase[0] == 'replay':
            if kind == 'raw':
                assert message.encoding == '16UC1'
                replay_frames.append(message.header.stamp.sec)
            return
        stamp = message.header.stamp
        key = (stamp.sec, stamp.nanosec)
        group = pending.setdefault(key, {})
        group[kind] = message
        while len(pending) > 32:
            pending.popitem(last=False)
        if len(group) != 4:
            return
        assert len({m.header.frame_id for m in group.values()}) == 1
        arrays = {}
        for name, dtype, encoding in [('raw', 'u2', '16UC1'),
                                      ('temperature', 'f4', '32FC1'), ('ir', 'u1', 'mono8')]:
            m = group[name]
            assert (m.height, m.width, m.encoding) == (192, 256, encoding)
            dt = np.dtype(('>' if m.is_bigendian else '<') + dtype)
            assert m.step == 256 * dt.itemsize
            arrays[name] = np.frombuffer(bytes(m.data), dtype=dt).reshape(192, 256)
        np.testing.assert_allclose(arrays['temperature'], arrays['raw'].astype(np.float32) / 64 - 273.15)
        info = group['camera_info']
        assert (info.height, info.width) == (192, 256)
        assert info.k[0] == 0  # This acceptance run has no supplied calibration.
        now = time.monotonic()
        if last_frame[0] is not None:
            max_gap[0] = max(max_gap[0], now - last_frame[0])
        last_frame[0] = now
        report['frames'] += 1
        pending.pop(key)
    subscriptions = []
    for kind in ('raw', 'temperature', 'ir', 'camera_info'):
        subscriptions.append(observer.create_subscription(
            CameraInfo if kind == 'camera_info' else Image, 'thermal/' + kind,
            lambda message, kind=kind: receive(kind, message), qos_profile_sensor_data))
    nuc = observer.create_client(Trigger, 'thermal/trigger_nuc')
    def diagnostics(message):
        report['diagnostic_messages'] = report.get('diagnostic_messages', 0) + 1
        report['last_diagnostics'] = [{'level': s.level, 'message': s.message}
                                    for s in message.status]
    subscriptions.append(observer.create_subscription(
        DiagnosticArray, 'diagnostics', diagnostics, 10))
    processes = []
    started = time.monotonic()
    recorder = None
    future = None
    schedule = [(5., 'gain_low'), (10., 'gain_high'), (20., 'nuc')]
    last_log = 0.
    try:
        recorder = subprocess.Popen(['ros2', 'bag', 'record', '-o', args.bag,
            '/thermal/raw', '/thermal/temperature', '/thermal/ir',
            '/thermal/camera_info', '/diagnostics'], start_new_session=True)
        processes.append(recorder)
        while time.monotonic() - started < args.duration:
            executor.spin_once(timeout_sec=.1)
            elapsed = time.monotonic() - started
            if last_frame[0] is None:
                if elapsed > 10:
                    raise RuntimeError('No complete ROS frame received during startup')
            elif time.monotonic() - last_frame[0] > 5:
                raise RuntimeError('ROS frame stream stalled for five seconds')
            if schedule and elapsed >= schedule[0][0]:
                _, action = schedule.pop(0)
                if action == 'nuc':
                    if not nuc.service_is_ready():
                        raise RuntimeError('NUC service unavailable')
                    future = nuc.call_async(Trigger.Request())
                else:
                    result = node.set_parameters([Parameter('gain', value=action.split('_')[1])])[0]
                    assert result.successful, result.reason
                    report['controls'].append({'action': action, 'result': 'acknowledged'})
            if future and future.done():
                assert future.result().success, future.result().message
                report['controls'].append({'action': 'nuc', 'result': 'acknowledged'})
                future = None
            if recorder and elapsed >= 15:
                stop(recorder)
                assert recorder.returncode in (0, -signal.SIGINT, 128 + signal.SIGINT)
                recorder = None
            if elapsed - last_log >= 60:
                report['intervals'].append({'seconds': elapsed, 'frames': report['frames']})
                report['max_frame_gap_seconds'] = max_gap[0]
                if node.camera:
                    report['camera'] = {k:v for k,v in getattr(node.camera, 'info', {}).items()
                                        if k in ('model', 'firmware')}
                    report['counters'] = {k:getattr(node.camera.parser, k) for k in
                        ('corrupt_candidates', 'counter_discontinuities', 'queue_drops')}
                    report['counters']['timeouts'] = node.camera.timeouts
                output.write_text(json.dumps(report, indent=2) + '\n')
                print(json.dumps(report['intervals'][-1]), flush=True)
                last_log = elapsed
        assert len(report['controls']) == 3
        assert report.get('diagnostic_messages', 0) > 0
        report.update(seconds=time.monotonic() - started,
                      max_frame_gap_seconds=max_gap[0],
                      fps=report['frames'] / (time.monotonic() - started))
        assert report['frames'] > 0 and max_gap[0] <= 5
        if node.camera:
            camera = node.camera
            report['camera'] = {k:v for k,v in camera.info.items() if k in ('model', 'firmware')} if hasattr(camera, 'info') else {}
            report['counters'] = {k:getattr(camera.parser, k) for k in
                ('corrupt_candidates', 'counter_discontinuities', 'queue_drops')}
            report['counters']['timeouts'] = camera.timeouts
        executor.remove_node(node)
        node.destroy_node()
        node = None
        phase[0] = 'replay'
        for _ in range(20):
            executor.spin_once(timeout_sec=.02)
        replay_frames.clear()
        info = subprocess.check_output(['ros2', 'bag', 'info', args.bag], text=True)
        for topic in ('raw', 'temperature', 'ir', 'camera_info'):
            assert '/thermal/' + topic in info
        play = subprocess.Popen(['ros2', 'bag', 'play', args.bag], start_new_session=True)
        processes.append(play)
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline and (play.poll() is None or not replay_frames):
            executor.spin_once(timeout_sec=.1)
        stop(play)
        assert replay_frames, 'No recorded physical frame replayed'
        report.update(result='passed', rosbag_replayed_frames=len(replay_frames))
    except BaseException as exc:
        report.update(result='failed', error=str(exc))
        raise
    finally:
        for process in processes:
            stop(process)
        executor.shutdown()
        observer.destroy_node()
        if node:
            node.destroy_node()
        rclpy.shutdown()
        output.write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
