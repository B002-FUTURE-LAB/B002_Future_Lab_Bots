"""Drawer cell: cobot MoveIt 2 + RViz (reused from the cobot submodule) + example cabinet.

    ros2 launch drawer_picking drawer_cell.launch.py use_mock_bridge:=true   # simulation

On the real robot the bridge runs on the Jetson Nano (use_mock_bridge:=false).
"""
import math
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

# Example cabinet pose in mycobot_base_link (meters, radians). yaw = pi turns
# the open side of the bins toward the robot. If you move it, re-teach the
# poses (or update DEFAULT_POSES in drawer_picking/poses.py).
CABINET = {'x': 0.30, 'y': -0.06, 'z': -0.16, 'yaw': math.pi}


def generate_launch_description():
    rviz_config = os.path.join(get_package_share_directory('drawer_picking'), 'config', 'drawer_cell.rviz')
    moveit_launch = os.path.join(get_package_share_directory('mycobot_280_jn_moveit_config'),
                                 'galactic_demo.launch.py')
    return LaunchDescription([
        DeclareLaunchArgument('use_mock_bridge', default_value='false',
                              description='true = simulated robot (mock bridge on the PC)'),
        Node(package='mycobot_hw_interface', executable='mycobot_bridge', parameters=[{'mock': True}],
             output='screen', condition=IfCondition(LaunchConfiguration('use_mock_bridge'))),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(moveit_launch),
                                 launch_arguments={'rviz_config': rviz_config}.items()),
        Node(package='drawer_picking', executable='cabinet_marker', parameters=[CABINET]),
    ])
