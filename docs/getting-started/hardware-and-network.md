# Hardware and network

## Devices

| Device | Address | Role |
|---|---|---|
| Host PC (hostname `future-lab-ESPRIMO-P757`) | `192.168.0.204` | Runs Docker (backend and frontend), the host agent, ROS 2 Jazzy processes (Nav2, localization, RViz) and the cobot Discovery Server. |
| Raspberry Pi 4 on the TurtleBot 4 | `192.168.0.129` | TurtleBot 4 bringup (`turtlebot4.service`), the TurtleBot Discovery Server and the OAK-D camera. SSH user `ubuntu`. |
| iRobot Create 3 base | `192.168.186.2` | The TurtleBot's mobile base. Reachable from the Raspberry Pi; has its own web interface. |
| Jetson Nano (MyCobot side) | `192.168.0.250` (or `192.168.0.62`) | Hardware bridge for the MyCobot 280, camera stream and pump control. SSH user `er`. |
| MyCobot 280 arm | connected to the Jetson Nano | The manipulator. |

!!! note "The Nano's address can change"
    The Nano can appear as `192.168.0.62` (Wi-Fi) or `192.168.0.250`. The
    backend probes both and uses whichever answers (`backend/config/settings.py`).
    If the arm stops responding after a Wi-Fi reconnect, check this first.

## Software stack

| Layer | Technology |
|---|---|
| TurtleBot side | ROS 2 **Jazzy**, Nav2, Fast DDS (`rmw_fastrtps_cpp`) |
| Cobot side | ROS 2 **Galactic** in the `mycobot_ros2` container, MoveIt 2, Cyclone DDS (`rmw_cyclonedds_cpp`), `ROS_DOMAIN_ID=42` |
| Backend | Python 3.12, FastAPI, `rclpy` |
| Frontend | Next.js 14, React 18 |
| Containers | Docker Compose: `future_lab_backend` and `future_lab_frontend`, both with `network_mode: host` |

## Discovery servers

The TurtleBot side does not use multicast discovery. It uses two **Fast DDS
Discovery Servers**:

| Server | Runs on | Port | Managed by |
|---|---|---|---|
| TurtleBot Discovery Server | Raspberry Pi 4 | `11811` | the TurtleBot image (`discovery.service`) |
| Cobot Discovery Server | Host PC | `11888` | the user service `future-lab-cobot-discovery` |

The backend connects to the TurtleBot server with
`ROS_DISCOVERY_SERVER=192.168.0.129:11811;` and `ROS_SUPER_CLIENT=True`, so it
can see the whole graph. See [Ports and addresses](../reference/ports-and-addresses.md)
for every port.

!!! warning "Not yet documented"
    This page does not explain how the cobot side (domain 42) and the
    TurtleBot side (domain 0) exchange the handshake topics. That mechanism was
    not verified for this version. Add it to
    [Mission handshake](../architecture/mission-handshake.md) once confirmed.
