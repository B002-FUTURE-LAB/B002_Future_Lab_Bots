# Hardware and Network

## Devices

| Device | Address | Role |
|---|---|---|
| **Host Control PC** (`future-lab-ESPRIMO-P757`) | `192.168.0.129` (or `.204` secondary; Tailscale `100.86.49.29`) | Runs the FastAPI backend (`:8000`), Next.js frontend (`:3000`), Host Agent (`:18080`), Mission Signal Agent (`:18081`), ROS 2 Jazzy Nav2/localization/RViz, FastDDS Discovery Server (`:11811`), and the `mycobot_ros2` Docker container. |
| **TurtleBot 4 Raspberry Pi 4** | `192.168.0.21` | Runs TurtleBot 4 bringup (`turtlebot4.service`), `create3_republisher`, RPLIDAR, and OAK-D Pro camera. SSH user `ubuntu`. |
| **iRobot Create 3 Base** | `192.168.186.2` (`usb0` on RPi4) | Mobile base connected to the Raspberry Pi 4 via internal USB-C RNDIS Ethernet. Hosts an internal web interface on `:80`. |
| **Jetson Nano (MyCobot 280)** | `192.168.0.62` (Wi-Fi) or `192.168.0.250` (Ethernet) | Runs `nano_micro_bridge.py` (`:8088`) for serial servo control (`/dev/ttyTHS1` @ `1000000` baud), GPIO suction pump (BCM pins `20` and `21`), and wrist-camera MJPEG server (`:8080/stream.mjpg`). SSH user `er`. |
| **MyCobot 280 Manipulator** | Serial `/dev/ttyTHS1` on Jetson Nano | 6-DOF manipulator arm with pneumatic vacuum suction gripper and wrist camera. |

!!! note "The Nano's address can change"
    The Nano can appear as `192.168.0.62` (Wi-Fi) or `192.168.0.250` (wired). The
    backend probes both and uses whichever answers (`backend/config/settings.py`).
    If the arm stops responding after a Wi-Fi reconnect, check this first.

## Software Stack

| Layer | Technology |
|---|---|
| **TurtleBot 4 & Host Navigation** | ROS 2 **Jazzy Jalisco** (Ubuntu 24.04), Nav2, FastDDS (`rmw_fastrtps_cpp`), `ROS_DOMAIN_ID=0` |
| **MyCobot MoveIt 2 Container** | ROS 2 **Galactic Geochelone** in `mycobot_ros2` container (Ubuntu 20.04), MoveIt 2 (`move_group`), `ROS_DOMAIN_ID=42` |
| **Control Center Backend** | Python 3.12, FastAPI (`:8000`), in-process `rclpy` (`TurtleBotNode` + `CobotNode`) |
| **Control Center Frontend** | Next.js 14, React 18 (`:3000`) |
| **Host Micro-Daemons** | `host_agent.py` (`127.0.0.1:18080`) and `mission_signal_agent.py` (`127.0.0.1:18081`) |

## Discovery Servers

Rather than relying on Wi-Fi multicast (which campus and lab access points drop), the cell uses **FastDDS Unicast Discovery Servers**:

| Server | Runs on | Port | Managed by |
|---|---|---|---|
| **Primary ROS 2 Jazzy Discovery Server** (`Domain 0`) | Host PC (`192.168.0.129`) | `11811` | `host_agent.py` / `turtlebot4_jazzy/start_discovery_server.sh` |
| **Cobot Discovery Server** (`Domain 42`) | Host PC (`192.168.0.129`) | `11888` | `future-lab-cobot-discovery` (`cobot/START_COBOT_DISCOVERY_HOST.sh`) |

The backend and CLI tools connect to the primary server with `ROS_DISCOVERY_SERVER="192.168.0.129:11811;"` and `ROS_SUPER_CLIENT=True`, giving full visibility of all nodes and topics. See [Ports and addresses](../reference/ports-and-addresses.md) for the complete port catalog.

## How Cross-Domain Communication Works (`Domain 42` ↔ `Domain 0`)

Because ROS 2 Galactic (`Domain 42`) and ROS 2 Jazzy (`Domain 0`) have incompatible DDS wire handshakes, they never share a `ROS_DOMAIN_ID`. Instead, the Host PC bridges them through three mechanisms:

1. **Direct HTTP Actuation (`:8088`)**: The backend's `CobotNode` commands the physical MyCobot arm and reads measured encoder angles directly over HTTP via `nano_micro_bridge.py` on the Jetson Nano (`192.168.0.62:8088`).
2. **Host Mission Signal Agent (`:18081`)**: Both `TurtleBotNode` and `CobotNode` run inside the host's ROS 2 Jazzy process (`ROS_DOMAIN_ID=0`), and critical handshake signals (`/product_class`, `/turtlebot_at_pickup`, `/item_released_on_tb4`, `/start_delivery`) are published and verified on `ROS_DOMAIN_ID=0` via `mission_signal_agent.py` (`127.0.0.1:18081`).
3. **Localhost UDP Joint Mirror (`:38527`)**: For unified 3D visualization in RViz2 (`integration_cobot_tb4`), `tools_mycobot_joint_udp_exporter.py` inside `mycobot_ros2` (Galactic, Domain 42) streams `/joint_states` over localhost UDP (`127.0.0.1:38527`) to `tools_mycobot_joint_udp_receiver.py` on the Host PC (Jazzy, Domain 0), which republishes `/mycobot/joint_states`.

See [Networking, DDS Domains & Cross-Domain Bridging](../architecture/networking-and-dds.md) and [Mission Handshake](../architecture/mission-handshake.md) for full architectural diagrams.
