# Thermal Master P3 camera topics and visualization in ROS 2

Publish native radiometric matrices to ROS 2 and inspect a real thermal stream. The physical reference environment is Ubuntu 22.04 x86_64 with ROS 2 Humble. Foxy and Jazzy have automated adapter coverage; physical acceptance on those distributions remains pending.

## Build with the ROS-compatible Python

Clone the repository, configure [USB permissions](usb.md), and run from its root. Use the system Python matching ROS rather than a Conda interpreter.

```sh
source /opt/ros/humble/setup.bash
sudo apt install python3-venv python3-pip python3-colcon-common-extensions libusb-1.0-0 ros-humble-sensor-msgs ros-humble-diagnostic-msgs ros-humble-std-srvs ros-humble-rosbag2 ros-humble-rqt-image-view
/usr/bin/python3 -m venv --system-site-packages .ros-venv
. .ros-venv/bin/activate
python -m pip install --upgrade 'pip>=23' 'setuptools>=61,<72' 'packaging>=24' 'importlib-metadata>=4' wheel
python -m pip install --no-build-isolation "git+https://github.com/josepgomis/unofficial-thermalmaster-p3-sdk.git@v1.0.0"
P3_SDK_SITE=$(python -c "import sysconfig; print(sysconfig.get_paths()['purelib'])")
export PYTHONPATH="$P3_SDK_SITE:$PYTHONPATH"
colcon build --base-paths ros2
. install/setup.bash
export PYTHONPATH="$P3_SDK_SITE:$PYTHONPATH"
export ROS_DOMAIN_ID=42
ros2 launch thermalmaster_p3_ros p3.launch.py
```

Use a normally installed SDK: colcon's system Python may not process an editable installation's `.pth` file when the venv site directory is provided through PYTHONPATH. Startup includes the camera initialization sequence and can take several seconds. Close other camera applications first.

## Inspect topics from a second terminal

Run from the same checkout. Both terminals must use the same ROS distribution and domain:

```sh
source /opt/ros/humble/setup.bash
. install/setup.bash
export ROS_DOMAIN_ID=42
ros2 topic list -t
ros2 topic info /thermal/ir --verbose
ros2 topic hz /thermal/ir
ros2 topic echo /thermal/camera_info --once --qos-reliability best_effort
ros2 run rqt_image_view rqt_image_view /thermal/ir
```

`/thermal/ir` is a grayscale preview. `/thermal/raw` is 16UC1 in 1/64 K; `/thermal/temperature` is 32FC1 Celsius. All three images and CameraInfo share each frame's header. Diagnostics have their own timestamps. Native dimensions are 256 × 192. Topic names assume the default namespace/remapping.

Images and CameraInfo use sensor-data QoS (best effort, volatile). In RViz2, add an Image display for `/thermal/ir` and select **Best Effort** reliability. A reliable-only subscriber may not match these publishers. `ros2 topic hz` reports the subscriber's observed delivery rate, not a guaranteed sensor rate.

![Physical ROS 2 Humble camera topics and observed IR rate near 25 FPS, without host identifiers](images/ros2-humble-topics.jpg)

Actual command output from a physical P3 session is reformatted for presentation. [Original identifier-free output](images/ros2-humble-output.json).

## Change controls and inspect state

```sh
ros2 param set /p3 gain low
ros2 param set /p3 gain high
ros2 service call /thermal/trigger_nuc std_srvs/srv/Trigger '{}'
ros2 topic echo /diagnostics --once
```

NUC service success means acknowledgment, not a calibrated measurement or exposure boundary. Device selection and calibration changes require restarting the node; gain, timeout and frame_id can change while it runs.

The node closes/reopens after disconnect or a persistent stalled stream, with exponential retries capped at five seconds. Recovery uses a new Camera and parser. The default optical frame is `p3_optical_frame`; supply the mounting transform yourself. Headers use the host ROS clock after SDK reception, not hardware exposure timestamps.

## Record and replay ROS messages

```sh
ros2 bag record -o p3-run /thermal/raw /thermal/temperature /thermal/ir /thermal/camera_info /diagnostics
```

Stop recording cleanly, then stop the live node before playback so two publishers do not share the same topics:

```sh
ros2 bag info p3-run
ros2 bag play p3-run
```

If recording QoS does not match, supply best-effort/volatile overrides for the four sensor topics. CameraInfo is explicitly uncalibrated unless a valid native-grid calibration YAML is supplied; the adapter does not estimate extrinsics or rectify images. See [parameters, calibration and validation](ros2.md).
