from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    arguments = [DeclareLaunchArgument('serial', default_value=''),
                 DeclareLaunchArgument('path', default_value=''),
                 DeclareLaunchArgument('frame_id', default_value='p3_optical_frame'),
                 DeclareLaunchArgument('camera_info_file', default_value='')]
    node = Node(package='thermalmaster_p3_ros', executable='p3_node', name='p3',
                output='screen', parameters=[{name: ParameterValue(LaunchConfiguration(name), value_type=str) for name in
                                             ('serial', 'path', 'frame_id', 'camera_info_file')}])
    return LaunchDescription(arguments + [node])
