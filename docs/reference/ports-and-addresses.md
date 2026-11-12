# Ports and Addresses

All network addresses and ports below are represented with placeholders; define your laboratory's actual values in your local `.env` (see [`future_lab_control_center/.env.example`](https://github.com/B002-FUTURE-LAB/B002_Future_Lab_Bots/blob/main/future_lab_control_center/.env.example) on GitHub) and ROS 2 Discovery configuration.

## Service Ports

| Placeholder | Where | Service |
|---|---|---|
| `<FRONTEND_PORT>` | Host PC | Dashboard (Next.js) |
| `<BACKEND_PORT>` | Host PC | Backend API (FastAPI) |
| `<HOST_AGENT_PORT>` | Host PC, loopback only | [Host agent](host-agent.md) |
| `<MISSION_SIGNAL_PORT>` | Host PC, loopback only | Mission signal agent |
| `<COBOT_DISCOVERY_PORT>` | Host PC | Cobot Fast DDS Discovery Server |
| `<TB4_DISCOVERY_PORT>` | Raspberry Pi (`<TURTLEBOT_IP>`) | TurtleBot Fast DDS Discovery Server |
| `<CAMERA_STREAM_PORT>` | Jetson Nano | Cobot camera MJPEG stream (`/stream.mjpg`) |
| `<NANO_BRIDGE_PORT>` | Jetson Nano | HTTP micro-bridge for the arm and pump |
| `<CREATE3_HTTP_PORT>` | Create 3 (`<CREATE3_BASE_IP>`) | Create 3 web interface |
| `<UDP_JOINT_PORT>` | Host PC (localhost UDP) | Cross-distro 3D RViz joint-state mirror |
| `<REMOTE_DESKTOP_PORT>` / `<SSH_PORT>` | Host PC | Optional remote desktop / SSH access |

## Device Address Placeholders

| Placeholder | Device |
|---|---|
| `<HOST_PC_IP>` | Host Control PC |
| `<TURTLEBOT_IP>` | Raspberry Pi 4 (TurtleBot 4) |
| `<CREATE3_BASE_IP>` | Create 3 base (reachable via `usb0` from the Raspberry Pi) |
| `<JETSON_NANO_IP>` (`<NANO_WIFI_IP>`, `<NANO_ETH_IP>`) | Jetson Nano (Wi-Fi or wired interface) |
| `<TAILSCALE_HOST_IP>` | Optional Tailscale VPN address of the Host PC |

All device addresses live on private local subnets configured in your lab router and `.env`.

## ROS Settings

| Setting | TurtleBot side | Cobot side |
|---|---|---|
| ROS distribution | Jazzy | Galactic |
| `ROS_DOMAIN_ID` | `0` | `42` |
| RMW | `rmw_fastrtps_cpp` | `rmw_cyclonedds_cpp` |
| Discovery | Discovery Server `<TURTLEBOT_IP>:<TB4_DISCOVERY_PORT>` | Discovery Server on the host, port `<COBOT_DISCOVERY_PORT>` |
