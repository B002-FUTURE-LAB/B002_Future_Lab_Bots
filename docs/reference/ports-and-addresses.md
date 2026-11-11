# Ports and addresses

## Ports

| Port | Where | Service |
|---|---|---|
| `3000` | Host PC | Dashboard (Next.js) |
| `8000` | Host PC | Backend API (FastAPI) |
| `8100` | Host PC, loopback only | [Host agent](host-agent.md) |
| `8101` | Host PC, loopback only | Mission signal agent |
| `11888` | Host PC | Cobot Fast DDS Discovery Server |
| `11811` | Raspberry Pi `192.168.0.129` | TurtleBot Fast DDS Discovery Server |
| `8080` | Jetson Nano | Cobot camera MJPEG stream (`/stream.mjpg`) |
| `8088` | Jetson Nano | HTTP micro-bridge for the arm and pump |
| `80` | Create 3 `192.168.186.2` | Create 3 web interface |

## Addresses

| Address | Device |
|---|---|
| `192.168.0.204` | Host PC |
| `192.168.0.129` | Raspberry Pi 4 (TurtleBot 4) |
| `192.168.186.2` | Create 3 base (seen from the Raspberry Pi) |
| `192.168.0.250`, `192.168.0.62` | Jetson Nano (it may take either) |

All addresses are private (LAN) addresses on the lab network.

## ROS settings

| Setting | TurtleBot side | Cobot side |
|---|---|---|
| ROS distribution | Jazzy | Galactic |
| `ROS_DOMAIN_ID` | `0` | `42` |
| RMW | `rmw_fastrtps_cpp` | `rmw_cyclonedds_cpp` |
| Discovery | Discovery Server `192.168.0.129:11811` | Discovery Server on the host, port `11888` |
