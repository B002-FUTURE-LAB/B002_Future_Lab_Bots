# ADR-0009: Lightweight UDP Joint Mirroring Instead of `ros1_bridge` / Cross-Distro DDS

- **Status**: Accepted
- **Date**: 2026-08
- **Related**: [ADR-0007](0007-ipc-host-backend.md), [Networking and DDS](../networking-and-dds.md)

---

## Context

To provide a unified 3D Digital Twin of Lab B002 in a single RViz2 window (`integration_cobot_tb4`), the Host Control PC (running **ROS 2 Jazzy** on `ROS_DOMAIN_ID=0`) needs live 6-DOF joint angles from the MyCobot 280 manipulator, whose MoveIt 2 stack runs inside the `mycobot_ros2` container (**ROS 2 Galactic** on `ROS_DOMAIN_ID=42`).

Attempting to connect ROS 2 Galactic and ROS 2 Jazzy on the same `ROS_DOMAIN_ID` caused FastDDS RTPS participant crashes (`see ADR-0001`), and building a custom multi-distro C++ bridge was overly complex for forwarding a single 6-float `sensor_msgs/msg/JointState` array.

## Decision

Bridge the manipulator's joint states from ROS 2 Galactic (`Domain 42`) to ROS 2 Jazzy (`Domain 0`) using a dependency-free **localhost UDP JSON relay** (`integration_cobot_tb4/tools/`):

1. `tools_mycobot_joint_udp_exporter.py` runs inside `mycobot_ros2` (Galactic, Domain 42), subscribes to `/joint_states`, and sends compact JSON datagrams (`{"names": [...], "positions": [...]}`) to `127.0.0.1:<UDP_JOINT_PORT>` at up to `30 Hz`.
2. `tools_mycobot_joint_udp_receiver.py` runs on the Host PC (Jazzy, Domain 0), listens on UDP `127.0.0.1:<UDP_JOINT_PORT>`, stamps a native ROS 2 Jazzy `sensor_msgs/msg/JointState` message with the host clock, and publishes `/mycobot/joint_states` consumed by a namespaced `robot_state_publisher` (`frame_prefix: mycobot_`).

## Consequences

- **Positive**:
  - Zero DDS cross-version coupling between Galactic (`Domain 42`) and Jazzy (`Domain 0`).
  - Sub-millisecond localhost UDP overhead and automatic timestamp synchronization with the host's Jazzy TF tree (`map -> mycobot_base_link -> ...`).
- **Negative / Trade-offs**:
  - One-way telemetry mirroring (for visualization and rosbag recording on Domain 0); actuation commands still flow through the backend's HTTP `:<NANO_BRIDGE_PORT>` / `docker exec` pipeline.
