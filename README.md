# B002 Future Lab Bots

Aggregator repository that keeps the three B002 laboratory robotics projects together:
**TurtleBot 4**, **MyCobot 280**, and the **3D Integration / Visualization Overlay**, along with the **Future Lab Control Center** web dashboard. Each robot subsystem folder is a Git submodule so this repository pins the exact versions that work together.

## Structure

```text
B002_Future_Lab_Bots/
  turtlebot4_jazzy/          # TurtleBot 4 (ROS 2 Jazzy), B002 map, Nav2 & mission routines
  cobot/                     # MyCobot 280, Docker, MoveIt 2 & Jetson Nano hardware bridge
  integration_cobot_tb4/     # 3D visualization, static TF overlay & UDP joint-state bridge
  future_lab_control_center/ # Unified Web Control Center (Next.js frontend + FastAPI/ROS 2 backend)
  docs/                      # Technical & operational documentation (MkDocs)
```

## Official References

Each robot subsystem builds upon the official platform documentation:

### TurtleBot 4

- [TurtleBot 4 Basic Setup](https://turtlebot.github.io/turtlebot4-user-manual/setup/basic.html)
- [TurtleBot 4 Navigation Tutorial](https://turtlebot.github.io/turtlebot4-user-manual/tutorials/navigation.html)
- Observed issues & hardware notes: [turtlebot4_jazzy/KNOWN_ISSUES.md](turtlebot4_jazzy/KNOWN_ISSUES.md)

### MyCobot 280

- [Elephant Robotics GitBook](https://docs.elephantrobotics.com/docs/gitbook-en/)
- [MyCobot 280 Pi SSH / Software Notes](https://docs.elephantrobotics.com/docs/mycobot_280_pi_en/3-FunctionsAndApplications/5.BasicFunction/5.2-Softwarelnstructions/3.5.2-SW-detail-description.html#ssh)
- [MyCobot 280 MoveIt Documentation](https://docs.elephantrobotics.com/docs/mycobot-m5-en/12-ApplicationBaseROS/12.1-ROS1/12.1.5-Moveit/myCobot-280.html)
- [MyCobot 280 Arduino ROS/MoveIt Documentation](https://docs.elephantrobotics.com/docs/mycobot-280-Arduino-en/3-FunctionsAndApplications/6.developmentGuide/ROS/12.1-ROS1/12.1.5-Moveit/)
- [MoveIt 2 Galactic README](https://github.com/moveit/moveit2/tree/galactic?tab=readme-ov-file)
- [MoveIt Galactic Announcement](https://moveit.ai/ros/moveit/galactic/2021/07/08/moveit-galactic.html)
- [Install MoveIt 2 from Source](https://moveit.ai/install-moveit2/source/)
- [Elephant Robotics MyCobot 280 Jetson Nano Support](https://www.elephantrobotics.com/en/support-280-jetson-nano-en/)

### Network & Factory References

- Router / lab network: TP-Link AX5400.

## Cloning the Repository

```bash
git clone --recurse-submodules https://github.com/B002-FUTURE-LAB/B002_Future_Lab_Bots.git
cd B002_Future_Lab_Bots
```

If already cloned without submodules:

```bash
git submodule update --init --recursive
```

To update the repository and submodules:

```bash
git pull
git submodule update --init --recursive
```

## Running the Three Systems Manually

To operate the cell manually from terminals, open three windows (e.g., in Terminator) for MyCobot, TurtleBot 4, and the 3D Integration View.

Before starting, clean up any stale RViz / Nav2 / Mission Manager processes from previous sessions:

```bash
pkill -f "mission_manager.py" || true
pkill -f "turtlebot4_navigation localization.launch.py" || true
pkill -f "turtlebot4_navigation nav2.launch.py" || true
pkill -f "turtlebot4_viz view_navigation.launch.py" || true
pkill -f "rviz2" || true
ros2 daemon stop
ros2 daemon start
```

### Window 1 — MyCobot 280

```bash
cd ~/B002_Future_Lab_Bots/cobot/mycobot_docker
xhost +local:root
docker compose up -d mycobot_ros2
```

Then launch MoveIt 2 planning on the host PC:

```bash
cd ~/B002_Future_Lab_Bots/cobot
./mycobot_docker/RUN_PLANNING_PC.sh
```

This starts the container, prepares the MyCobot bridge on the Jetson Nano, and opens MoveIt 2 + RViz to plan and execute arm motions.

### Window 2 — Physical TurtleBot 4 on Map B002

Enter the TurtleBot 4 workspace:

```bash
cd ~/B002_Future_Lab_Bots/turtlebot4_jazzy
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=0
export ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_SUPER_CLIENT=True
export ROS_DISCOVERY_SERVER="192.168.0.129:11811;"
```

If the robot is docked, undock first:

```bash
ros2 action send_goal /undock irobot_create_msgs/action/Undock "{}"
```

Launch localization with the B002 map:

```bash
ros2 launch turtlebot4_navigation localization.launch.py \
  map:=$HOME/B002_Future_Lab_Bots/turtlebot4_jazzy/maps/B002_map.yaml
```

Once the map appears in RViz, set the robot's initial pose using **2D Pose Estimate**, then launch Nav2 with the custom project parameters:

```bash
ros2 launch turtlebot4_navigation nav2.launch.py \
  params_file:=$HOME/B002_Future_Lab_Bots/turtlebot4_jazzy/config/nav2_custom.yaml
```

To open the navigation RViz view:

```bash
ros2 launch turtlebot4_viz view_navigation.launch.py
```

### Window 3 — Integrated 3D Visualization

```bash
cd ~/B002_Future_Lab_Bots/integration_cobot_tb4
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=0
export ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_SUPER_CLIENT=True
export ROS_DISCOVERY_SERVER="192.168.0.129:11811;"
./scripts/run_3d_view.sh
```

### Passwordless SSH Key Setup (PC ↔ Robot)

So `mission_manager.py` and the Control Center can manage the OAK-D camera and services on the robot over SSH without password prompts:

1. Generate an SSH key on the PC (if you don't already have one):
   ```bash
   ssh-keygen -t ed25519 -N "" -f ~/.ssh/id_ed25519
   ```
2. Copy the key to the TurtleBot 4 Raspberry Pi:
   ```bash
   ssh-copy-id ubuntu@192.168.0.129
   ```

### Mission Manager

Once localization, Nav2, and sensors are active:

```bash
cd ~/B002_Future_Lab_Bots/turtlebot4_jazzy
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=0
export ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_SUPER_CLIENT=True
export ROS_DISCOVERY_SERVER="192.168.0.129:11811;"
python3 scripts/mission_manager.py --ros-args --params-file params/waypoints.yaml
```

Trigger a delivery mission:

```bash
ros2 service call /start_delivery std_srvs/srv/Trigger {}
```

## Simulation

To test TurtleBot 4 in Gazebo Harmonic using the project Docker environment:

```bash
cd ~/B002_Future_Lab_Bots/turtlebot4_jazzy
./sim/run_lab_world.sh false false 0.0 0.0 0.0
```

Simulation is useful for development, though physical hardware behavior in B002 (dock/undock, RPLidar, OAK-D, Wi-Fi, and post-undock sensor recovery) should always be validated on the real robot.

## Integration Notes

- **TurtleBot 4**: ROS 2 Jazzy, FastDDS, `ROS_DOMAIN_ID=0`.
- **MyCobot 280**: ROS 2 Galactic, MoveIt 2, CycloneDDS (`ROS_DOMAIN_ID=42`) for the arm bridge.
- **3D Integration**: Visualizes both robots in the shared `map` frame without mixing ROS distributions.
- **Navigation Map**: `turtlebot4_jazzy/maps/B002_map.yaml`.
- **Mission Waypoints**: `turtlebot4_jazzy/params/waypoints.yaml`.
- **TurtleBot 4 RPi Backup Configs**: `turtlebot4_jazzy/config/rpi_turtlebot4/`.

---

## 🎛️ Future Lab Control Center (Web Dashboard & Robotic Cell)

The `future_lab_control_center/` directory contains the full web interface for supervising, controlling, and calibrating the robotic cell.

### Communication Architecture & Ports

```text
  [ Next.js Frontend (Port 3000) ]
                 │ (HTTP REST / Polling)
                 ▼
  [ FastAPI Backend (Port 8000) ] ── (ROS 2 DDS / Docker) ──► [ MoveIt Planning (mycobot_ros2) ]
                 │ (SSH ControlMaster / HTTP Micro-Bridge)
                 ▼
  [ Jetson Nano (192.168.0.62) ]
     ├── HTTP Micro-Bridge (Port 8088) -> Suction Pump, Release/Lock Servos, Direct Joints (<30ms)
     └── MJPEG Camera Server (Port 8080) -> Live computer vision stream
```

---

### 🚨 Panic Mode & Hardware Safety Notes

The **`🚨 PANIC`** button on the Dashboard executes a master safety shutdown of the robotic cell:

1. **Immediate Servo Lock (`< 5ms`)**: Sends a priority HTTP request to `http://<JETSON_NANO_IP>:8088/panic`, halting serial joint commands and locking torque on all 6 joints.
2. **Peripheral Shutdown**: Turns off the suction pump and stops any running YOLO vision test.
3. **Camera Shutdown**: Terminates `nano_camera_server.py` on the Jetson Nano.
4. **MoveIt Planner Termination**: Runs `pkill -9` on `move_group` and `rviz` inside the `mycobot_ros2` Docker container on the PC.
5. **Nano Bridge Termination**: Stops `mycobot_bridge` on the Jetson Nano while keeping servos locked.
6. **Panic Lockout**: Locks the Dashboard in a safety state until the operator explicitly triggers a full system restart.

> [!WARNING]
> **1. Serial Port Contention (`/dev/ttyTHS1`) on Jetson Nano**:
> When `mycobot_bridge` is killed abruptly with `pkill -9`, the Linux kernel serial driver may take **1–2 seconds** to release `/dev/ttyTHS1`. Restarting before release completes can cause `device reports readiness to read but returned no data` or `Address already in use` on port `8088`.

> [!WARNING]
> **2. Internal Firmware Buffer Inertia (MyCobot 280)**:
> If Panic is triggered while the arm is moving at high speed, the HTTP panic command arrives in `< 5ms`, but the arm may still travel 1–3 cm due to packets already buffered in the microcontroller firmware before the torque lock takes effect.

> [!IMPORTANT]
> **3. Full-Screen Reboot Lockout Modal (`RebootOverlayModal`)**:
> Because hardware stabilization takes ~5–8 seconds (releasing the serial port, starting the video server, and warming up MoveIt ROS 2 actions), the web UI displays a full-screen blocking modal with a progress bar and 5-step health checklist.

---

### 🔄 Starting the Control Center

```bash
cd ~/B002_Future_Lab_Bots/future_lab_control_center
docker compose down && docker compose up --build -d
```

Open in your browser: **`http://localhost:3000`** (Frontend) or **`http://localhost:8000/docs`** (Swagger REST API).

---

## Never Override FastDDS Built-in Transports

Do **not** set `FASTDDS_BUILTIN_TRANSPORTS` (in environment variables, Docker Compose, or CLI) and do **not** use `<useBuiltinTransports>false</useBuiltinTransports>` in any RMW XML profile — neither on the host, nor in containers, nor in the Create 3 RMW Profile Override.

Overriding the built-in transport list breaks registration with the FastDDS Discovery Server (`192.168.0.129:11811`). Symptom: the robot responds to ping, but `/dock_status`, `/battery_state`, and `/odom` stop arriving, and `/dock` and `/undock` lose their action servers.
