# REST API

The backend is a FastAPI application served on port **`<BACKEND_PORT>`**. Interactive
OpenAPI documentation is available at `/docs` while the backend is running.

This page lists every route. A CI check (`tools/docs/check_route_coverage.py`)
fails the build if a route exists in the code but is missing here, so the list
cannot silently go stale.

!!! note "Where the descriptions come from"
    Each description is taken from the route handler's own docstring in
    `future_lab_control_center/backend/api/` (the docstrings are written in
    Portuguese in the code and are translated here). Request and response
    bodies are defined by the Pydantic models in the same files and are shown,
    always up to date, in the live `/docs` page.

Total: **80 routes** in five routers.

## Cell control — `/api/v1/cell`

Orchestrates the whole cell (cobot plus TurtleBot) and the safety stops.
Source: `backend/api/cell_routes.py`.

| Route | Purpose |
|---|---|
| `GET /api/v1/cell/status` | Global status of the automated cell. |
| `POST /api/v1/cell/mode` | Change the cell's master settings: mode, cooldown and YOLO confidence. |
| `POST /api/v1/cell/integrated_real/preflight` | Validate both robots and their communication without moving anything or assuming a class. |
| `POST /api/v1/cell/integrated_real/start` | Start the visualizations and arm one cycle for a real YOLO classification. |
| `POST /api/v1/cell/integrated_real/confirm_detection` | Authorize pick and delivery, only for the measured candidate that is still visible. |
| `POST /api/v1/cell/integrated_real/stop` | Request a stop; the worker then measures pump OFF and HOME, or performs a rollback. |
| `POST /api/v1/cell/test_handshake/preflight` | Validate every link of the integrated test without commanding motion. |
| `POST /api/v1/cell/test_handshake` | Run a full automatic cycle in which the cobot simulates a YOLO detection, to test the handshake with the TurtleBot 4. |
| `POST /api/v1/cell/auto/start` | Start continuous automatic mode. |
| `POST /api/v1/cell/auto/stop` | Stop automatic mode. |
| `POST /api/v1/cell/manual/start_scan` | Manual step 1: move the arm to SCAN and turn on YOLO vision inspection. |
| `POST /api/v1/cell/manual/authorize_pick` | Manual step 2: advance to PICK, only if YOLO detected a valid can. |
| `POST /api/v1/cell/manual/authorize_place` | Manual step 3: advance to release the can at PLACE, when the arm is at PLACE_APPROACH. |
| `POST /api/v1/cell/interrupt` | Interrupt button (manual and auto): freezes the robot motors at the current point (under 5 ms) and opens a confirmation. |
| `POST /api/v1/cell/interrupt/confirm` | Answer the confirmation: `abort=true` aborts and releases the can at the pick point; `abort=false` continues. |
| `POST /api/v1/cell/stop` | Soft emergency stop: pump off, automatic mode cancelled, YOLO vision off, arm returned to HOME. See [Emergency stop](../guides/emergency-stop.md). |
| `POST /api/v1/cell/panic` | Master panic button: stops everything (pump, camera, YOLO, robot, motors and MoveIt planning). |
| `POST /api/v1/cell/reset_panic` | Leave the panic state and trigger a clean restart of MoveIt, the camera and the Nano hardware bridge. |

## Cobot control — `/api/v1/cobot`

Controls the MyCobot 280 arm. Source: `backend/api/cobot_routes.py`.

| Route | Purpose |
|---|---|
| `GET /api/v1/cobot/poses` | All saved poses (memory and disk), the status of each pose and the last-saved date. |
| `POST /api/v1/cobot/move/{pose_name}` | Move the arm to a named pose. Disables the isolated YOLO test first, for safety. |
| `POST /api/v1/cobot/pump` | Turn the suction pump on (`on=true`) or off (`on=false`). |
| `POST /api/v1/cobot/yolo_test` | Enable or disable the isolated YOLO classification test. |
| `GET /api/v1/cobot/yolo_test/status` | Whether the isolated YOLO test is active (checks that the process is alive). |
| `POST /api/v1/cobot/teach/release` | Teach mode: release the motor torque so the arm can be moved by hand. **Hold the arm.** |
| `POST /api/v1/cobot/teach/lock` | Teach mode: lock the motor torque at the current position. |
| `POST /api/v1/cobot/teach/record/{pose_name}` | Record the current joint angles under a pose name, in memory, and save to disk automatically. |
| `POST /api/v1/cobot/teach/save` | Save all recorded poses to the YAML file, with a timestamp. |
| `DELETE /api/v1/cobot/teach/clear` | Back up the last saved poses to a `.yaml.bak` file, then clear the active calibration. |
| `POST /api/v1/cobot/teach/restore` | Restore the last saved calibration from the `.yaml.bak` backup. |
| `POST /api/v1/cobot/teach/playback` | Start, pause or resume trajectory playback without touching the camera or the pump. |

## Health — `/api/v1/health`

Source: `backend/api/health_routes.py`.

| Route | Purpose |
|---|---|
| `GET /api/v1/health/` | Network health, device pings and stream status, collected in parallel (asynchronously). |
| `POST /api/v1/health/restart_camera` | Run the official camera start routine, `RUN_NANO_CAMERA.sh start`, in the background. |
| `POST /api/v1/health/stop_camera` | Run `RUN_NANO_CAMERA.sh stop` to shut down the MJPEG server and end the YOLO test. |
| `POST /api/v1/health/restart_nano_hardware` | Restart the hardware communication bridge (`mycobot_hw`), lock the joints so they do not fall, turn off the pump and camera, and restart the system. |
| `POST /api/v1/health/launch_rviz` | Open the full MoveIt 2 + RViz window by running `RUN_PLANNING_PC.sh` directly. |

## Settings — `/api/v1/settings`

Source: `backend/api/settings_routes.py`.

| Route | Purpose |
|---|---|
| `GET /api/v1/settings/` | Currently active network settings and parameters. |
| `PUT /api/v1/settings/` | Update the settings **in the `.env` file** dynamically. |

!!! warning "This route writes to disk"
    `PUT /api/v1/settings/` modifies the `.env` file of the control center.
    See [Configuration](configuration.md).

## TurtleBot 4 — `/api/v1/turtlebot`

Source: `backend/api/turtlebot_routes.py`. Many of these routes delegate to the
[host agent](host-agent.md), because the ROS 2 Jazzy processes run on the host,
not inside the backend container.

### Status and diagnostics

| Route | Purpose |
|---|---|
| `GET /api/v1/turtlebot/status` | TurtleBot 4 status: battery, position, docking and simulation mode. |
| `GET /api/v1/turtlebot/ros_env` | The effective ROS environment of the process and what the rclpy node can see. |
| `GET /api/v1/turtlebot/processes` | State of the navigation stack processes, queried through the host agent. |
| `GET /api/v1/turtlebot/nav_readiness` | Navigation readiness, checked by ROS introspection. Read-only. |
| `GET /api/v1/turtlebot/amcl_status` | AMCL pose and covariance. Read-only. |
| `GET /api/v1/turtlebot/nav_poses` | The `dock_pose` from `nav_poses.yaml` and the real waypoints from `waypoints.yaml`. |
| `GET /api/v1/turtlebot/diagnose` | A full network test (ping) and an audit of ROS 2 topics on the TurtleBot 4 Discovery Server. |
| `GET /api/v1/turtlebot/logs` | Latest logs, queried through the host agent (`source` and `lines` query parameters). |
| `GET /api/v1/turtlebot/oakd_stream` | Live MJPEG stream of the OAK-D-PRO camera, with a 5 s timeout and a 300 s limit per connection. |
| `GET /api/v1/turtlebot/system/inventory` | The 10-item system health inventory, through the host agent. |

### Motion, docking and pose

| Route | Purpose |
|---|---|
| `POST /api/v1/turtlebot/teleop` | Manual linear and angular velocity control (`/cmd_vel`). |
| `POST /api/v1/turtlebot/dock` | Trigger only the native physical docking of the Create 3 (`/dock`). |
| `POST /api/v1/turtlebot/undock` | Send the undock command and wait for real confirmation of the maneuver. |
| `POST /api/v1/turtlebot/set_dock_status` | **Deprecated.** The dock state comes from Create 3 telemetry and cannot be forced. |
| `POST /api/v1/turtlebot/set_initial_pose` | Set the pose on the host; succeeds only after fresh AMCL evidence. |
| `POST /api/v1/turtlebot/save_dock_pose` | Save the current AMCL pose as the dock pose in `nav_poses.yaml`. Requires `amcl_ok`, a docked robot and the dock thresholds. |
| `POST /api/v1/turtlebot/clear_costmaps` | Clear the global and local Nav2 costmaps. A recovery path. |

### Launching and stopping processes

Each launch route starts one process generation and reports success only after
the processes are confirmed; each stop route confirms they are gone.

| Route | Purpose |
|---|---|
| `POST /api/v1/turtlebot/launch_localization` | Start a generation; confirms only after `map_server` and AMCL are active. |
| `POST /api/v1/turtlebot/stop_localization` | Stop and confirm the absence of `map_server`, AMCL and the lifecycle manager. |
| `POST /api/v1/turtlebot/launch_nav2` | Start a generation; confirms only after the managed nodes are active. |
| `POST /api/v1/turtlebot/stop_nav2` | Stop and confirm the absence of the navigation processes. |
| `POST /api/v1/turtlebot/launch_viz` | Start a single RViz instance on the host. |
| `POST /api/v1/turtlebot/stop_viz` | Stop and confirm the absence of RViz. |
| `POST /api/v1/turtlebot/launch_integrated_3d` | Request the 3D scene and confirm that the launcher script finished without error. |
| `POST /api/v1/turtlebot/launch_mission_manager` | Start a single Mission Manager instance. |
| `POST /api/v1/turtlebot/stop_mission_manager_process` | Stop and confirm the absence of the Mission Manager. |
| `POST /api/v1/turtlebot/start_oakd_camera` | Wake the OAK-D through the host agent; confirms only after frames are received. |
| `POST /api/v1/turtlebot/restart_daemon` | Restart the ROS 2 daemon (`ros2 daemon stop && ros2 daemon start`) with the TurtleBot 4 environment. |

### Missions

| Route | Purpose |
|---|---|
| `POST /api/v1/turtlebot/trigger_delivery` | Call the ROS 2 part-delivery service `/start_delivery`. |
| `POST /api/v1/turtlebot/trigger_failure` | Call the ROS 2 service for collecting a defective part or discarding it, `/start_failure`. |
| `POST /api/v1/turtlebot/trigger_restock` | Call the ROS 2 raw-material restock service `/start_restock`. |
| `POST /api/v1/turtlebot/trigger_patrol` | **Not implemented.** Always returns HTTP 501, because the mission manager does not expose `/start_patrol`. |
| `POST /api/v1/turtlebot/stop_mission` | Interrupt the active mission and force the motors to stop; returns a transparent status. See [Emergency stop](../guides/emergency-stop.md). |
| `POST /api/v1/turtlebot/mission_test/product_class` | Publish only a synthetic classification. Moves no robot. |
| `POST /api/v1/turtlebot/mission_test/start_delivery` | Simulate the cobot's vision and start a delivery with a fresh, confirmed class. |
| `POST /api/v1/turtlebot/mission_test/item_released` | Publish only the synthetic "can released" signal. Does not move the cobot. |

### Simulation mode

These three handlers have no docstring in the code. The descriptions below
follow the dashboard text: a step-by-step simulation in which the user
confirms each stop with "OK", with no changes made to the Nano.

| Route | Purpose |
|---|---|
| `POST /api/v1/turtlebot/simulation/start` | Start the interactive simulation. |
| `POST /api/v1/turtlebot/simulation/next_step` | Advance to the next simulated step. |
| `POST /api/v1/turtlebot/simulation/stop` | Stop the simulation. |

### System recovery (through the host agent)

| Route | Purpose |
|---|---|
| `POST /api/v1/turtlebot/system/restart_backend` | Restart the backend container. |
| `POST /api/v1/turtlebot/system/restart_cobot_discovery` | Restart the myCobot Discovery Server (port `<COBOT_DISCOVERY_PORT>`). |
| `POST /api/v1/turtlebot/robot/restart_bringup` | Restart `turtlebot4.service` on the Raspberry Pi 4 over SSH. |
| `POST /api/v1/turtlebot/robot/start_oakd` | Wake the OAK-D camera on the Raspberry Pi 4 over SSH. |
