# Run Gazebo Simulation & Interactive Simulation Mode

The project provides two complementary simulation modes for developing and testing without moving the physical robots:

1. **Gazebo Harmonic 3D Physics Simulation (`turtlebot4_jazzy/sim/`)**: Runs a full simulated TurtleBot 4 with Lidar, SLAM, and Nav2 inside a procedural SDF replica of Lab B002 (`my_lab.sdf`).
2. **Control Center Interactive Simulation Mode**: Runs inside the web dashboard (`http://localhost:3000`) to test the state machine, manual step approvals, and synthetic YOLO classification (`blue` / `red` / `defect`).

---

## Mode 1: Gazebo Harmonic Simulation (`turtlebot4_jazzy/sim/`)

### Step 1: Build the Simulation Docker Image

The simulation runs in an isolated ROS 2 Jazzy + Gazebo container (`turtlebot4:jazzy`) configured with `rmw_fastrtps_cpp`:

```bash
cd /home/future-lab/B002_Future_Lab_Bots/turtlebot4_jazzy/sim
docker build --no-cache -t turtlebot4:jazzy .
```

### Step 2: Generate the Lab SDF World (If Modified)

The laboratory geometry is defined in `turtlebot4_jazzy/config/lab.yaml` and compiled into `turtlebot4_jazzy/sim/worlds/my_lab.sdf`:

```bash
cd /home/future-lab/B002_Future_Lab_Bots/turtlebot4_jazzy
python3 scripts/gen_world.py config/lab.yaml sim/worlds/my_lab.sdf
```

### Step 3: Launch the Simulated Lab World

Run `run_lab_world.sh`, which auto-detects NVIDIA (`--gpus all`), Intel/AMD DRI (`/dev/dri`), or software rendering (`LIBGL_ALWAYS_SOFTWARE=1`):

```bash
cd /home/future-lab/B002_Future_Lab_Bots/turtlebot4_jazzy/sim
./run_lab_world.sh [SLAM] [NAV2] [X_POS] [Y_POS] [YAW]
```

Examples:

```bash
# Default: SLAM=true, Nav2=true, spawn at (0, 0, 0)
./run_lab_world.sh

# Spawn without Nav2 first (recommended on slower GPUs), then launch Nav2 separately
./run_lab_world.sh true false 0.0 0.0 0.0
```

If you launched with `NAV2=false`, open a second shell inside the running `tb4_sim` container (or on the host with matching RMW) and run:

```bash
cd /home/future-lab/B002_Future_Lab_Bots/turtlebot4_jazzy
./scripts/launch_nav2_separate.sh
```

> [!WARNING]
> Do not run the Gazebo simulation container (`--net host`) at the same time as the physical TurtleBot 4 on `ROS_DOMAIN_ID=0`, or simulated `/scan`, `/tf`, and `/odom` topics will collide with the real robot's telemetry.

---

## Mode 2: Control Center Interactive Simulation Mode

When testing the cell state machine or training new operators in the web UI:

### Simulating YOLO Detections & Cell Cycles

1. Open `http://localhost:3000` and switch the **Cell Control Panel** to **Manual Mode** (`POST /api/v1/cell/mode` with `{"mode": "manual"}`).
2. Trigger a synthetic YOLO classification without requiring a physical can under the wrist camera:

```bash
# Inject a synthetic detection ("blue", "red", or "invalid")
curl -s -X POST http://localhost:8000/api/v1/cobot/yolo_sim \
  -H "Content-Type: application/json" \
  -d '{"item_type": "blue"}' | jq
```

3. Step through the manual cycle approvals:
   - `POST /api/v1/cell/manual_start` — moves arm to `scan` and awaits operator confirmation.
   - `POST /api/v1/cell/step_pick` — authorizes `pick_approach → pick → place_approach`.
   - `POST /api/v1/cell/step_place` — authorizes `place`, TurtleBot handoff, vacuum release, and return to `home`.

### Simulating 3D Scene Geometry Without Physical Robots

You can also inspect the unified 3D cell scene (`map`, `mycobot_base_link`, semantic zones, and table collision geometry) in RViz without turning on the physical robots:

```bash
cd /home/future-lab/B002_Future_Lab_Bots/integration_cobot_tb4
./scripts/start_3d_rviz_only.sh
```

See [Submodule: integration_cobot_tb4](../reference/submodules/integration-cobot-tb4.md) for details on switching between `rich` and `minimal` semantic scene rendering.
