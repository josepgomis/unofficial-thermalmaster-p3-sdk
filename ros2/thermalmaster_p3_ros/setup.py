from setuptools import setup

setup(
    name='thermalmaster_p3_ros', version='0.1.0',
    packages=['thermalmaster_p3_ros'],
    data_files=[('share/ament_index/resource_index/packages', ['resource/thermalmaster_p3_ros']),
                ('share/thermalmaster_p3_ros', ['package.xml']),
                ('share/thermalmaster_p3_ros/launch', ['launch/p3.launch.py'])],
    install_requires=['setuptools', 'unofficial-thermalmaster-p3>=0.1.0,<0.2'],
    zip_safe=True, license='Apache-2.0',
    description='Independent Thermal Master P3 ROS 2 driver',
    maintainer='Unofficial P3 SDK contributors', maintainer_email='maintainers@example.invalid',
    entry_points={'console_scripts': ['p3_node = thermalmaster_p3_ros.node:main']},
)
