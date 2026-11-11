# Known Issues, Limitations & Technical Debt

This page documents the known hardware quirks, software limitations, and planned improvements of the B002 Future Lab Bots platform as of the current handoff state.

---

## 1. Security & Credentials Management (`.env` Isolation)

> [!IMPORTANT]
> **Keep `.env` and `.agent_token` Local Only**
> All SSH passwords (`JETSON_NANO_SSH_PASSWORD`), OPC-UA credentials (`OPCUA_PASSWORD`), and Host Agent authentication tokens (`HOST_AGENT_TOKEN`) have been extracted from the codebase into `future_lab_control_center/.env` (symlinked at `.env` in the repository root). Both `.env` and `.agent_token` are listed in `.gitignore` and must never be committed to Git.

### Credential Variables Loaded from `future_lab_control_center/.env`

1. `HOST_AGENT_TOKEN`: Loaded by `future_lab_control_center/host_agent/agent.py` and `future_lab_control_center/backend/api/turtlebot_routes.py` (`settings.get_agent_token()`).
2. `JETSON_NANO_SSH_USER` and `JETSON_NANO_SSH_PASSWORD`: Loaded by `backend/api/{cell_routes,health_routes}.py`, `backend/ros2_nodes/cobot_node.py`, and the shell scripts in `cobot/mycobot_docker/`.
3. `OPCUA_USER` and `OPCUA_PASSWORD`: Loaded by `turtlebot4_jazzy/factory_integration/{app.py,opcua_net_test.py}`.

---

## 2. Submodule Branch & Git Metadata Quirks

- **`cobot` Submodule Branch (`featnew-yolo` vs `master`)**:
  - `.gitmodules` in the root repository lists `branch = master` for `cobot`, while the active pinned commit in `cobot/` is on the `featnew-yolo` branch (`git@github.com:B002-FUTURE-LAB/Cobot.git`).
  - Always use `git submodule update --init --recursive` (which checks out the exact pinned commit SHA) rather than `git submodule update --remote`.

---

## 3. Hardware & Firmware Limitations

### iRobot Create 3 Base (`192.168.186.2`)

1. **Deep Sleep Off-Dock**: If the TurtleBot 4 is left undocked for more than ~15–20 minutes idle, the Create 3 base enters Deep Sleep and shuts down `usb0`. Software cannot wake it remotely; the robot must be placed physically on the powered charging dock.
2. **Post-Undock Odometry / Laser Stabilization**: Immediately after `/undock` completes, the Create 3 base's gyro/odometry and AMCL particle filter need several seconds to settle after backing off the dock ramp. `waypoints.yaml` enforces `post_undock_stabilize_s: 8.0` seconds before sending the first `NavigateToPose` goal. Reducing this below `5.0 s` increases initial path oscillation.
3. **IR Dock Alignment Sensitivity**: If `predock_point` is more than `~0.80 m` from `dock_station` or angled away from the IR emitter cone, `/dock` may fail on the first attempt. `MissionBase` is configured with `dock_tries: 2` and re-navigates to `predock_point` between attempts.

### MyCobot 280 & Jetson Nano (`192.168.0.62`)

1. **Compact 280 mm Kinematic Envelope**: Cartesian MoveIt planning (`RRTConnect`) frequently fails near workspace boundaries. All production pick-and-place routines therefore use calibrated 6-DOF joint-space targets (`cobot_poses.yaml`) verified via `goto_pose_verified()`.
2. **Serial `[0, 0, 0, 0, 0, 0]` Glitch Filtering**: The Atom firmware on `/dev/ttyTHS1` (`1000000` baud) occasionally returns all-zero angles or an empty list on a single serial read. `nano_micro_bridge.py` (`get_angles_safe`) automatically retries up to 4 times and rejects all-zero glitches unless intentionally commanded to `home`.
3. **Dual IP Address (`192.168.0.62` Wi-Fi vs. `192.168.0.250` Ethernet)**: Depending on whether the Ethernet cable is plugged in, the Nano answers on `.62` or `.250`. The backend probes both automatically (`settings.py`).

---

## 4. Unimplemented / Deprecated API Endpoints

- **`POST /api/v1/turtlebot/mission/patrol`**: Returns `HTTP 501 Not Implemented` because `MissionManager` currently exposes `/start_delivery`, `/start_failure`, and `/start_restock`, while `patrol.py` is a standalone script.
- **`POST /api/v1/turtlebot/dock_status`**: Deprecated no-op endpoint kept for backward frontend compatibility; dock status is read strictly from live Create 3 `/dock_status` telemetry.
