# Troubleshooting

Find your symptom in the table below, then follow the diagnosis and recovery steps. Every entry documents a real failure mode encountered and solved in Lab B002.

---

## Symptom Quick-Reference Matrix

| Symptom | Likely Cause | Fix |
|---|---|---|
| `telemetry_ok: false`, battery `null`, `/scan` works but `/odom` and `/dock_status` are dead | Create 3 application crashed or `create3_republisher` stopped on the RPi4 | [Recover TurtleBot telemetry](guides/recover-turtlebot-telemetry.md) |
| Create 3 base (`<CREATE3_BASE_IP>`) answers `ping`, web UI says `"Oops, something went wrong"` | Internal Create 3 firmware application hung | [Restart the Create 3 application](guides/restart-the-create3-app.md) |
| Create 3 base does not answer `ping <CREATE3_BASE_IP>` and ring light is completely off | Create 3 entered **Deep Sleep** off the dock or battery is depleted | [Wake Create 3 from Deep Sleep](#1-create-3-in-deep-sleep-usb0-down-ring-light-off) |
| `ros2 node list` is empty or `undock` / Nav2 goals hang indefinitely | FastDDS Discovery Server overloaded by duplicate Nav2 stacks or stale root `_ros2_daemon` | [Recover the Discovery Server](guides/recover-discovery-server.md) & [Root Daemon Fix](#2-stale-root-_ros2_daemon-hiding-topics-on-the-host-pc) |
| Dashboard shows telemetry lost right after `START_LAB.sh --reset` | `--reset` restarted `turtlebot4.service`; Create 3 takes ~60 s to re-establish DDS | Wait 60 seconds; avoid repeated `--reset` calls ([Start and stop the lab](guides/start-and-stop-the-lab.md)) |
| MyCobot does not respond after Wi-Fi reconnect (`HTTP 503` on `:<NANO_BRIDGE_PORT>`) | Jetson Nano switched between `<NANO_WIFI_IP>` and `<NANO_ETH_IP>`, or `nano_micro_bridge.py` exited | [Recover Jetson Nano Bridge](#3-mycobot-jetson-nano-http-bridge-nano_bridge_port-unreachable) |
| MoveIt 2 logs `RRTConnect: Unable to sample any valid states for goal tree` or `Motion plan was found but it seems to be too costly` | Requested Cartesian pose is outside the 280 mm reach envelope or start state has joint limit violation | [Fix MoveIt Planning Failures](#4-moveit-2-rrtconnect-planning-failures) |
| `nav_readiness` stays `false` with `amcl_pose_stale` while robot is stationary on the dock | AMCL has not received an initial pose yet, or TF `map -> odom` is missing | Click **Set Docked Pose** (`POST /api/v1/turtlebot/dock_pose`) ([Set Initial Pose](guides/set-initial-pose-and-dock-pose.md)) |
| Host PC cannot receive DDS traffic from `<TURTLEBOT_IP>` even though `<TB4_DISCOVERY_PORT>` is listening | Linux `ufw` firewall blocking unicast UDP response ports on `wlan0` / `eth0` | [Check Host Firewall Rules](#5-host-firewall-ufw-blocking-fastdds-unicast-traffic) |
| OAK-D camera preview is black or `restart_camera_stream` times out | USB bus reset needed on RPi4 or MyCobot USB webcam `/dev/video0` busy | [Recover Camera Streams](#6-camera-stream-black-or-unavailable-oak-d-or-mycobot-wrist-camera) |
| Stop mission answers `partial` | Nav2 action server did not confirm cancellation within timeout | Press physical Create 3 button ([Emergency stop](guides/emergency-stop.md)) |

---

## Detailed Recovery Procedures

### 1. Create 3 in Deep Sleep (`usb0` Down, Ring Light Off)

If the TurtleBot 4 was left undocked with power on for an extended period, the iRobot Create 3 base powers down its internal `usb0` interface (`<CREATE3_BASE_IP>`) to protect the battery. Software reboots on the Raspberry Pi **cannot** wake it:

1. **Physical Action Required**: Pick up the TurtleBot 4 and place it firmly onto the powered charging dock so the metal charging contacts engage.
2. Wait **45–60 seconds** for the Create 3 ring light to spin white and chime.
3. Verify from the Raspberry Pi (`ssh <TB4_USER>@<TURTLEBOT_IP>`) that `ping -c 3 <CREATE3_BASE_IP>` responds.
4. Trigger **Restart Telemetry** (`POST /api/v1/turtlebot/restart_telemetry`) so `create3_republisher` reconnects cleanly.

---

### 2. Stale Root `_ros2_daemon` Hiding Topics on the Host PC

If someone ran `sudo ros2 ...` on the Host Control PC, a root-owned `_ros2_daemon` process starts without the `ROS_DISCOVERY_SERVER` environment variables, poisoning `ros2 node list` and `ros2 topic list`:

```bash
sudo pkill -f _ros2_daemon || true
pkill -f _ros2_daemon || true
source /opt/ros/jazzy/setup.bash
source ~/B002_Future_Lab_Bots/turtlebot4_jazzy/setup.bash
export ROS_DOMAIN_ID=0
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_SUPER_CLIENT=True
export ROS_DISCOVERY_SERVER="<TURTLEBOT_IP>:<TB4_DISCOVERY_PORT>;"
ros2 daemon start
ros2 node list
```

---

### 3. MyCobot Jetson Nano HTTP Bridge (`:<NANO_BRIDGE_PORT>`) Unreachable

If `/api/v1/cobot/status` reports `connected: false` or `HTTP 503`:

1. Probe both Nano IP addresses from the Host PC:

```bash
curl -s --max-time 2 http://<NANO_WIFI_IP>:<NANO_BRIDGE_PORT>/status || curl -s --max-time 2 http://<NANO_ETH_IP>:<NANO_BRIDGE_PORT>/status
```

2. If the Nano responds to `ping` (`<JETSON_NANO_IP>`) but port `<NANO_BRIDGE_PORT>` is closed, restart the bridge via the Control Center recovery endpoint:

```bash
curl -s -X POST http://localhost:<BACKEND_PORT>/api/v1/health/recover/cobot_bridge | jq
```

Or manually over SSH:

```bash
cd ~/B002_Future_Lab_Bots/cobot/mycobot_docker
./START_NANO_BRIDGE.sh
```

---

### 4. MoveIt 2 `RRTConnect` Planning Failures

The MyCobot 280 has a compact `280 mm` working radius. Cartesian goals outside this sphere fail with `RRTConnect: Unable to sample any valid states for goal tree`:

- **Why Joint-Space Poses Are Preferred**: All 6 operational poses (`home`, `scan`, `pick_approach`, `pick`, `place_approach`, `place`) are stored and executed in **joint space** (`cobot_poses.yaml` via `goto_pose_verified`), avoiding IK singularities entirely.
- **If MoveIt Rejects the Start State**: Ensure the physical arm is not twisted past $\pm 165^\circ$ ($\pm 2.88\text{ rad}$) on any joint. Use **Teach Mode** (`Release Servos` → move near `home` → `Lock Servos`) to bring all joints back inside nominal bounds.

---

### 5. Host Firewall (`ufw`) Blocking FastDDS Unicast Traffic

FastDDS Discovery Server uses UDP port `<TB4_DISCOVERY_PORT>` for registration, plus ephemeral unicast UDP ports for peer-to-peer user data between `<TURTLEBOT_IP>` and `<HOST_PC_IP>`. If `ufw` is active on the Host PC, allow all traffic from the local lab subnet:

```bash
sudo ufw allow from <LAB_SUBNET_CIDR>
sudo ufw allow from <CREATE3_SUBNET_CIDR>
```

---

### 6. Camera Stream Black or Unavailable (OAK-D or MyCobot Wrist Camera)

- **MyCobot Wrist Camera (`http://<JETSON_NANO_IP>:<CAMERA_STREAM_PORT>/stream.mjpg`)**:
  - If `yolo_test_vision.py` is running in non-headless mode on the Nano, it may lock `/dev/video0`. Restart the MJPEG stream server via:

```bash
curl -s -X POST http://localhost:<BACKEND_PORT>/api/v1/health/recover/camera | jq
```

- **TurtleBot 4 OAK-D Pro Camera (`/oakd/rgb/preview/image_raw`)**:
  - Verify whether the topic is publishing on the RPi4: `ros2 topic hz /oakd/rgb/preview/image_raw`.
  - If silent, restart the TurtleBot 4 bringup service via `POST /api/v1/turtlebot/restart_telemetry`.
