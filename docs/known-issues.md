# Known Issues & Hardware Limitations

This page documents the known hardware quirks, firmware limitations, and unimplemented endpoints of the B002 Future Lab Bots platform.

---

## 1. Local Environment Configuration (`.env`)

> [!IMPORTANT]
> **Configure `.env` Locally Before Running**
> Specific network addresses, service ports, and private device credentials are intentionally omitted from public documentation. Copy `future_lab_control_center/.env.example` from the [GitHub repository](https://github.com/B002-FUTURE-LAB/B002_Future_Lab_Bots/blob/main/future_lab_control_center/.env.example) to a local `.env` file (git-ignored) and fill in your laboratory values before launching the stack.

---

## 2. Submodule Branch & Git Metadata Quirks

- **`cobot` Submodule Branch (`featnew-yolo` vs `master`)**:
  - `.gitmodules` in the root repository lists `branch = master` for `cobot`, while the active pinned commit in `cobot/` is on the `featnew-yolo` branch (`git@github.com:B002-FUTURE-LAB/Cobot.git`).
  - Always use `git submodule update --init --recursive` (which checks out the exact pinned commit SHA) rather than `git submodule update --remote`.

---

## 3. Hardware & Firmware Limitations

### iRobot Create 3 Base (`<CREATE3_BASE_IP>`)

1. **Deep Sleep Off-Dock**: If the TurtleBot 4 is left undocked for more than ~15–20 minutes idle, the Create 3 base enters Deep Sleep and shuts down `usb0`. Software cannot wake it remotely; the robot must be placed physically on the powered charging dock.
2. **Post-Undock Odometry / Laser Stabilization**: Immediately after `/undock` completes, the Create 3 base's gyro/odometry and AMCL particle filter need several seconds to settle after backing off the dock ramp. `waypoints.yaml` enforces `post_undock_stabilize_s: 8.0` seconds before sending the first `NavigateToPose` goal. Reducing this below `5.0 s` increases initial path oscillation.
3. **IR Dock Alignment Sensitivity**: If `predock_point` is more than `~0.80 m` from `dock_station` or angled away from the IR emitter cone, `/dock` may fail on the first attempt. `MissionBase` is configured with `dock_tries: 2` and re-navigates to `predock_point` between attempts.

### MyCobot 280 & Jetson Nano (`<JETSON_NANO_IP>`)

1. **Compact 280 mm Kinematic Envelope**: Cartesian MoveIt planning (`RRTConnect`) frequently fails near workspace boundaries. All production pick-and-place routines therefore use calibrated 6-DOF joint-space targets (`cobot_poses.yaml`) verified via `goto_pose_verified()`.
2. **Serial `[0, 0, 0, 0, 0, 0]` Glitch Filtering**: The Atom firmware on `/dev/ttyTHS1` (`1000000` baud) occasionally returns all-zero angles or an empty list on a single serial read. `nano_micro_bridge.py` (`get_angles_safe`) automatically retries up to 4 times and rejects all-zero glitches unless intentionally commanded to `home`.
3. **Dual Network Interface (`<NANO_WIFI_IP>` Wi-Fi vs. `<NANO_ETH_IP>` Ethernet)**: Depending on whether the Ethernet cable is plugged in, the Nano may switch between its Wi-Fi and wired addresses. The backend probes configured candidates automatically (`settings.py`).

---

## 4. Unimplemented / Deprecated API Endpoints

- **`POST /api/v1/turtlebot/mission/patrol`**: Returns `HTTP 501 Not Implemented` because `MissionManager` currently exposes `/start_delivery`, `/start_failure`, and `/start_restock`, while `patrol.py` is a standalone script.
- **`POST /api/v1/turtlebot/dock_status`**: Deprecated no-op endpoint kept for backward frontend compatibility; dock status is read strictly from live Create 3 `/dock_status` telemetry.
