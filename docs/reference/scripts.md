# Operational Scripts Catalog

This page catalogs every operational shell and Python script across the root repository, the Control Center, the three submodules, and the `experiments/` toolkit.

---

## 1. Root & Control Center Scripts (`future_lab_control_center/`)

| Script Path | Runs On | Purpose |
| :--- | :--- | :--- |
| `START_CONTROL_CENTER.sh` | Host PC | Starts the Host Agent (`:<HOST_AGENT_PORT>`), Mission Signal Agent (`:<MISSION_SIGNAL_PORT>`), FastAPI backend (`:<BACKEND_PORT>`), and Next.js frontend (`:<FRONTEND_PORT>`). Supports `--status`. |
| `STOP_CONTROL_CENTER.sh` | Host PC | Gracefully stops the frontend, backend, Mission Signal Agent, and Host Agent processes. |
| `future_lab_control_center/START_LAB.sh` | Host PC | Full one-command lab bringup: checks VPN/network, starts Discovery Servers, brings up `mycobot_ros2` container, verifies Jetson Nano bridge and TurtleBot telemetry, and launches the Control Center. Supports `--status` and `--reset`. |
| `future_lab_control_center/STOP_LAB.sh` | Host PC | Stops the Control Center stack and auxiliary lab processes. |
| `future_lab_control_center/host_agent/host_agent.py` | Host PC (`127.0.0.1:<HOST_AGENT_PORT>`) | Privileged local daemon managing Discovery Server, GUI launchers, and SSH recovery actions. |
| `future_lab_control_center/host_agent/mission_signal_agent.py` | Host PC (`127.0.0.1:<MISSION_SIGNAL_PORT>`) | Persistent ROS 2 Jazzy `SUPER_CLIENT` daemon publishing `/product_class` and `/item_released_on_tb4`, calling `/start_delivery`, and monitoring `/turtlebot_at_pickup`. |
| `future_lab_control_center/scripts/yolo_test_vision.py` | Host PC / Nano | YOLOv8 vision classifier (`best.pt`) reading from `http://<JETSON_NANO_IP>:<CAMERA_STREAM_PORT>/stream.mjpg` and publishing detections to `/yolo_detections` / `/product_class`. Supports `--headless` and `--conf`. |

---

## 2. Submodule 1: TurtleBot 4 Scripts (`turtlebot4_jazzy/`)

| Script Path | Runs On | Purpose |
| :--- | :--- | :--- |
| `turtlebot4_jazzy/start_discovery_server.sh` | Host PC | Starts the FastDDS Discovery Server (`server_id=0`) on `<TURTLEBOT_IP>:<TB4_DISCOVERY_PORT>`. |
| `turtlebot4_jazzy/START_NAV_DISCOVERY.sh` | Host PC | Launches Nav2 localization (`Mapa_Lab.yaml`), `navigation.launch.py`, and `wait_for_map_tf.py` configured as a FastDDS `SUPER_CLIENT`. |
| `turtlebot4_jazzy/START_SLAM_DISCOVERY.sh` | Host PC | Launches online `slam_toolbox` mapping with FastDDS Discovery Server configuration. |
| `turtlebot4_jazzy/START_RVIZ_DISCOVERY.sh` | Host PC | Launches RViz2 preconfigured for TurtleBot 4 navigation on `ROS_DOMAIN_ID=0`. |
| `turtlebot4_jazzy/START_MISSION_DISCOVERY.sh` | Host PC | Starts the `mission_manager.py` node with `params/waypoints.yaml`. |
| `turtlebot4_jazzy/scripts/mission_manager.py` | Host PC | Central ROS 2 node exposing `/start_delivery`, `/start_failure`, `/start_restock`, `/stop_mission`, and `/save_dock_pose`. |
| `turtlebot4_jazzy/scripts/mission_base.py` | Host PC | Base class implementing `/undock`, `/dock`, `NavigateToPose`, AMCL/TF/scan readiness gates, and battery emergency safeguards. |
| `turtlebot4_jazzy/scripts/delivery_routine.py` | Host PC | Cooperative sorting routine (`fresh class → undock → pickup_point → handoff → delivery_red/blue → dock`). |
| `turtlebot4_jazzy/scripts/failure_routine.py` | Host PC | Defective item routine (`undock → failure_pickup → failure_zone → dock`). |
| `turtlebot4_jazzy/scripts/restock_routine.py` | Host PC | Inventory restock routine (`undock → inventory_point → supply_point → dock`). |
| `turtlebot4_jazzy/scripts/cancel_navigation_goals.py` | Host PC | Calls `/navigate_to_pose/_action/cancel_goal` (`CancelGoal` service) to abort active Nav2 trajectories. |
| `turtlebot4_jazzy/scripts/wait_for_map_tf.py` | Host PC | Auto-initializes `/initialpose` from `dock_station` when the robot starts docked (`is_docked == True`) and waits for `map -> base_link` TF. |
| `turtlebot4_jazzy/sim/run_lab_world.sh` | Host PC (Docker) | Launches Gazebo Harmonic + RViz + SLAM/Nav2 inside the `turtlebot4:jazzy` container using `worlds/my_lab.sdf`. |

---

## 3. Submodule 2: MyCobot 280 Scripts (`cobot/`)

| Script Path | Runs On | Purpose |
| :--- | :--- | :--- |
| `cobot/nano_micro_bridge.py` | Jetson Nano (`:<NANO_BRIDGE_PORT>`) | Lightweight HTTP hardware server interfacing with `pymycobot` (`/dev/ttyTHS1` @ `1000000` baud) and RPi.GPIO (BCM pins `20`, `21`). |
| `cobot/START_COBOT_DISCOVERY_HOST.sh` | Host PC | Starts the optional FastDDS Discovery Server for `ROS_DOMAIN_ID=42` on port `<COBOT_DISCOVERY_PORT>`. |
| `cobot/mycobot_docker/RUN_PLANNING_PC.sh` | Host PC (`mycobot_ros2`) | Launches MoveIt 2 (`move_group`), `robot_state_publisher`, RViz2, and restarts the physical bridge inside `mycobot_ros2`. |
| `cobot/mycobot_docker/START_NANO_BRIDGE.sh` | Host PC → Nano (SSH) | Deploys and starts `nano_micro_bridge.py` (`:<NANO_BRIDGE_PORT>`) on the Jetson Nano (`<JETSON_NANO_IP>`). |
| `cobot/mycobot_docker/RUN_TEACH.sh` | Host PC → Nano | Interactive CLI Teach Mode: releases servos for hand-guiding and locks them on `Enter`. |
| `cobot/mycobot_docker/SAVE_POSE.sh` | Host PC (`mycobot_ros2`) | Saves the current `/joint_states` angles into `cobot_poses.yaml` under `<pose_name>`. |
| `cobot/mycobot_docker/GO_POSE.sh` | Host PC (`mycobot_ros2`) | Moves the MyCobot arm to a named pose from `cobot_poses.yaml`. |
| `cobot/mycobot_docker/RUN_PICK_AND_PLACE.sh` | Host PC (`mycobot_ros2`) | Standalone pick-and-place test cycle script. |

---

## 4. Submodule 3: 3D Integration Scripts (`integration_cobot_tb4/`)

| Script Path | Runs On | Purpose |
| :--- | :--- | :--- |
| `integration_cobot_tb4/scripts/start_3d_monitoring.sh` | Host PC | Launches the complete unified 3D Digital Twin: static transform `map -> mycobot_base_link`, UDP joint exporter/receiver, semantic scene markers, and `rviz2_cobot_tb4_3d`. |
| `integration_cobot_tb4/scripts/start_3d_rviz_only.sh` | Host PC | Launches the 3D RViz scene (`config/cobot_tb4_3d.rviz`) without restarting the robot stacks. |
| `integration_cobot_tb4/scripts/calibrate_cobot_anchor.sh` | Host PC | Helper to update the `x, y, z, yaw` anchor of `mycobot_base_link` in `config/anchor.yaml`. |
| `integration_cobot_tb4/scripts/generate_b002_Dual_views.sh` | Host PC | Generates `generated/b002_scene_2d_overview.png`, `b002_semantic_preview.png`, and `b002_dual_lab.sdf`. |
| `integration_cobot_tb4/tools/tools_mycobot_joint_udp_exporter.py` | `mycobot_ros2` (Domain 42) | Subscribes to `/joint_states` in ROS 2 Galactic and sends JSON UDP packets to `127.0.0.1:<UDP_JOINT_PORT>`. |
| `integration_cobot_tb4/tools/tools_mycobot_joint_udp_receiver.py` | Host PC (Domain 0) | Receives UDP joint angles on `:<UDP_JOINT_PORT>` and republishes `/mycobot/joint_states` in ROS 2 Jazzy. |
| `integration_cobot_tb4/tools/b002_scene_marker_publisher.py` | Host PC (Domain 0) | Publishes 3D `MarkerArray` visualization of tables, zones, and labels from `config/b002_scene.yaml`. |

---

## 5. Experimental Campaign & Documentation CI Scripts

| Script Path | Runs On | Purpose |
| :--- | :--- | :--- |
| `experiments/generate_campaign_plan.py` | Host PC | Generates a randomized, balanced 60-trial schedule (`plan.csv`) with a fixed PRNG seed. |
| `experiments/record_trial.sh` | Host PC | Records a complete experimental run (or `--smoke` test): Zstd MCAP rosbag, 1 Hz dashboard JSONL, MJPEG camera MP4, event relay, and post-run validation. |
| `experiments/event_relay.py` | Host PC | Tails `backend/runtime/events.jsonl` and republishes deduplicated events to `/future_lab/events`. |
| `experiments/sample_dashboard_state.py` | Host PC | Polls 5 Control Center API endpoints at `1 Hz` into `dashboard_state.jsonl`. |
| `experiments/validate_trial.py` | Host PC | Verifies MCAP duration and required topic message counts (`SMOKE` vs `REAL`) and writes `validation.json`. |
| `tools/docs/check_english.py` | Host PC / CI | Verifies that all published documentation pages under `docs/` are written 100% in English. |
| `tools/docs/check_route_coverage.py` | Host PC / CI | Verifies that every FastAPI `@router.<method>` in `backend/api/*_routes.py` is documented in `docs/reference/rest-api.md`. |
| `tools/docs/check_env_coverage.py` | Host PC / CI | Verifies that every variable in `future_lab_control_center/.env.example` is documented in `docs/reference/configuration.md`. |
