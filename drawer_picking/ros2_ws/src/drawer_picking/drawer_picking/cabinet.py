"""cabinet_marker: show the example cabinet (STL) in RViz.

Visual only: the planner does not avoid it. Pose parameters (x, y, z, yaw)
are in mycobot_base_link and are set in launch/drawer_cell.launch.py.
"""
import math

import rclpy
from rclpy.qos import DurabilityPolicy, QoSProfile
from visualization_msgs.msg import Marker


def main():
    rclpy.init()
    node = rclpy.create_node('cabinet_marker')
    x, y, z, yaw = (node.declare_parameter(n, 0.0).value for n in ('x', 'y', 'z', 'yaw'))

    m = Marker(type=Marker.MESH_RESOURCE, action=Marker.ADD)
    m.header.frame_id = 'mycobot_base_link'
    m.mesh_resource = 'package://drawer_picking/meshes/kks5_wall_assembly.stl'   # meters
    m.pose.position.x, m.pose.position.y, m.pose.position.z = x, y, z
    m.pose.orientation.z, m.pose.orientation.w = math.sin(yaw / 2), math.cos(yaw / 2)
    m.scale.x = m.scale.y = m.scale.z = 1.0
    m.color.r, m.color.g, m.color.b, m.color.a = 0.85, 0.75, 0.55, 1.0

    # Transient local: RViz gets the marker even if it starts later.
    qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
    node.create_publisher(Marker, '/drawer_picking/cabinet', qos).publish(m)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    rclpy.try_shutdown()


if __name__ == '__main__':
    main()
