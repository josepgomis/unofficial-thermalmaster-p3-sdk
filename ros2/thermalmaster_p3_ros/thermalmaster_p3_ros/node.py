import time
import math

import rclpy
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
from rcl_interfaces.msg import SetParametersResult
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CameraInfo, Image
from std_msgs.msg import Header
from std_srvs.srv import Trigger

from thermalmaster_p3 import Camera, P3Error, FrameTimeoutError
from .messages import camera_info, image_message


class P3Node(Node):
    def __init__(self):
        super().__init__('p3')
        for name, default in [('serial', ''), ('path', ''), ('frame_id', 'p3_optical_frame'),
                              ('gain', 'high'), ('timeout', .1), ('camera_info_file', '')]:
            self.declare_parameter(name, default)
        if self.value('gain') not in ('high', 'low') or not math.isfinite(self.value('timeout')) or self.value('timeout') <= 0:
            raise ValueError('gain must be high/low and timeout must be positive')
        self.calibration = camera_info(self.value('camera_info_file'))
        self.camera = None
        self.connected_at = time.monotonic()
        self.frames = 0
        self.last_frame_at = None
        self.last_error = 'Waiting for P3'
        self.retry_at = 0.0
        self.backoff = .5
        self.publishers_by_kind = {name: self.create_publisher(Image, 'thermal/' + name,
                                                              qos_profile_sensor_data)
                                   for name in ('raw', 'temperature', 'ir')}
        self.info_publisher = self.create_publisher(CameraInfo, 'thermal/camera_info', qos_profile_sensor_data)
        self.diagnostics = self.create_publisher(DiagnosticArray, 'diagnostics', 10)
        self.nuc_service = self.create_service(Trigger, 'thermal/trigger_nuc', self.nuc)
        self.add_on_set_parameters_callback(self.parameters_changed)
        self.capture_timer = self.create_timer(.001, self.capture)
        self.diagnostic_timer = self.create_timer(1.0, self.publish_diagnostics)

    def value(self, name):
        return self.get_parameter(name).value

    def parameters_changed(self, parameters):
        for parameter in parameters:
            if parameter.name in ('serial', 'path', 'camera_info_file'):
                return SetParametersResult(successful=False, reason='Restart node to change ' + parameter.name)
            if parameter.name == 'gain' and parameter.value not in ('high', 'low'):
                return SetParametersResult(successful=False, reason='gain must be high/low')
            if parameter.name == 'timeout' and (not isinstance(parameter.value, (float, int)) or not math.isfinite(parameter.value) or parameter.value <= 0):
                return SetParametersResult(successful=False, reason='timeout must be positive')
            if parameter.name == 'frame_id' and not parameter.value:
                return SetParametersResult(successful=False, reason='frame_id cannot be empty')
        try:
            for parameter in parameters:
                if parameter.name == 'gain' and self.camera:
                    self.camera.set_gain(parameter.value)
        except P3Error as exc:
            return SetParametersResult(successful=False, reason=str(exc))
        return SetParametersResult(successful=True)

    def disconnect(self, error):
        if self.camera:
            self.camera.close()
            self.camera = None
        self.last_error = str(error)
        self.get_logger().warning(self.last_error)
        self.retry_at = time.monotonic() + self.backoff
        self.backoff = min(5., self.backoff * 2)

    def capture(self):
        if self.camera is None:
            if time.monotonic() < self.retry_at:
                return
            candidate = Camera(serial=self.value('serial') or None, path=self.value('path') or None)
            try:
                candidate.open()
                candidate.start()
                candidate.set_gain(self.value('gain'))
                self.camera = candidate
                self.connected_at = time.monotonic()
                self.frames = 0
                self.last_frame_at = None
            except P3Error as exc:
                candidate.close()
                self.disconnect(exc)
                return
        try:
            frame = self.camera.read_frame(timeout=float(self.value('timeout')))
        except FrameTimeoutError as exc:
            self.last_error = str(exc)
            # Recover a stream that stays stalled, not just an unplugged device.
            if time.monotonic() - (self.last_frame_at or self.connected_at) > 5:
                self.disconnect(exc)
            return
        except P3Error as exc:
            self.disconnect(exc)
            return
        header = Header()
        header.stamp = self.get_clock().now().to_msg()
        header.frame_id = self.value('frame_id')
        for name, data, encoding in [('raw', frame.raw, '16UC1'),
                                     ('temperature', frame.temperature_c, '32FC1'),
                                     ('ir', frame.ir, 'mono8')]:
            self.publishers_by_kind[name].publish(image_message(data, encoding, header))
        self.calibration.header = header
        self.info_publisher.publish(self.calibration)
        self.frames += 1
        self.last_frame_at = time.monotonic()
        self.last_error = ''
        self.backoff = .5

    def nuc(self, request, response):
        if not self.camera:
            response.success, response.message = False, 'P3 is disconnected'
            return response
        try:
            self.camera.trigger_nuc()
            response.success, response.message = True, 'NUC command acknowledged; malformed transition frames are discarded'
        except P3Error as exc:
            response.success, response.message = False, str(exc)
        return response

    def publish_diagnostics(self):
        status = DiagnosticStatus()
        status.name = self.get_name() + '/capture'
        status.hardware_id = '3474:45a2'
        status.level = DiagnosticStatus.ERROR if self.camera is None else (DiagnosticStatus.WARN if self.last_error else DiagnosticStatus.OK)
        status.message = self.last_error or 'Streaming (host reception timestamps)'
        values = {'frames': self.frames, 'fps': self.frames / max(.001, time.monotonic() - self.connected_at)}
        if self.camera:
            values.update(corrupt_candidates=self.camera.parser.corrupt_candidates,
                          counter_discontinuities=self.camera.parser.counter_discontinuities,
                          queue_drops=self.camera.parser.queue_drops, timeouts=self.camera.timeouts)
        status.values = [KeyValue(key=key, value=str(value)) for key, value in values.items()]
        message = DiagnosticArray()
        message.header.stamp = self.get_clock().now().to_msg()
        message.status = [status]
        self.diagnostics.publish(message)

    def destroy_node(self):
        if self.camera:
            self.camera.close()
        return super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = P3Node()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
