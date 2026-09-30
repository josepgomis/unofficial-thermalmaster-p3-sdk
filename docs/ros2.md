# ROS 2 integration

Targets: Foxy/Ubuntu 20.04, Humble/22.04 and Jazzy/24.04. Foxy is a legacy target; its CI image and dependencies may require maintenance. These combinations have not been run locally. Linux hardware support, including ARM64, remains unverified.

Use a venv with `--system-site-packages` and the same system Python as ROS. This retains ROS modules, avoids modifying externally managed Python, and supplies a packaging backend that understands the SDK's pyproject metadata:

```sh
# Run from this repository after sourcing your ROS installation.
sudo apt install libusb-1.0-0 python3-venv python3-pip python3-numpy python3-usb python3-yaml python3-colcon-common-extensions python3-setuptools python3-wheel
python3 -m venv --system-site-packages .ros-venv
. .ros-venv/bin/activate
python -m pip install --upgrade 'pip>=23' 'setuptools>=61,<77' wheel
python -m pip install --no-build-isolation .
P3_SDK_SITE=$(python -c "import sysconfig; print(sysconfig.get_paths()['purelib'])")
export PYTHONPATH="$P3_SDK_SITE:$PYTHONPATH"
colcon build --base-paths ros2
. install/setup.bash
export PYTHONPATH="$P3_SDK_SITE:$PYTHONPATH"
ros2 launch thermalmaster_p3_ros p3.launch.py
```

Install the `ros-$ROS_DISTRO-sensor-msgs`, `diagnostic-msgs`, `std-srvs`, and `rosbag2` packages if they are absent from your ROS installation. Configure [USB permissions](usb.md) first. The launch file accepts `serial`, `path`, `frame_id`, and `camera_info_file` arguments.

## Topics and controls

| Topic | Type / encoding | Meaning |
| --- | --- | --- |
| `thermal/raw` | sensor_msgs/Image, 16UC1 | Original 1/64 K values |
| `thermal/temperature` | sensor_msgs/Image, 32FC1 | Celsius, not a display-normalized image |
| `thermal/ir` | sensor_msgs/Image, mono8 | Infrared brightness |
| `thermal/camera_info` | sensor_msgs/CameraInfo | Native-grid calibration, or uncalibrated K[0]=0 |
| `diagnostics` | diagnostic_msgs/DiagnosticArray | Connection, FPS, framing errors and timeouts |

Image topics use the sensor-data QoS profile. Messages from one frame share a header stamped with the ROS clock after SDK reception. The default optical frame is `p3_optical_frame`; the user supplies the mounting transform. No TF extrinsics or hardware synchronization are fabricated. A paused simulated clock cannot describe live exposure timing.

```sh
ros2 param set /p3 gain low
ros2 param set /p3 timeout 0.1
ros2 service call /thermal/trigger_nuc std_srvs/srv/Trigger '{}'
```

`gain` (high/low), `timeout` (positive seconds) and `frame_id` can change during use. Restart to change device selection or calibration file. The node reconnects with exponential waits up to five seconds and discards buffered data by opening a new stream. A stream stalled for five seconds is reopened. Startup takes about three seconds, so callbacks can be delayed during reconnect.

## Calibration

`camera_info_file` reads a standard ROS camera-calibration YAML with `image_width`, `image_height`, `camera_matrix`, `distortion_coefficients`, `rectification_matrix`, `projection_matrix`, and `distortion_model`. Matrices must describe 256x192 images. Missing calibration publishes an explicitly uncalibrated CameraInfo; malformed supplied calibration fails startup. The SDK does not calculate calibration or rectify radiometric images.

## rosbag2

```sh
ros2 bag record -o p3-run /thermal/raw /thermal/temperature /thermal/ir /thermal/camera_info /diagnostics
ros2 bag info p3-run
ros2 bag play p3-run
```

If your recorder uses incompatible QoS, supply a QoS override with `best_effort` reliability and `volatile` durability for the four sensor topics. Do not run the live publisher on the same topics while inspecting playback.
