# Using the Web Control Center Dashboard

The **Future Lab Control Center Dashboard** (`http://localhost:3000`) is the central graphical operator console for the **B002 Future Lab Bots** robotic cell. It unifies real-time telemetry, camera feeds, manual calibration, process supervision, and cooperative mission execution for both the **MyCobot 280** manipulator and the **TurtleBot 4** mobile robot inside a single browser interface.

For internal React/Next.js architecture and instructions on modifying the source code, see [Frontend Dashboard: Internals & Developer Guide](../reference/frontend.md).

---

## 1. Opening the Dashboard

- **Local Access (Host Control PC)**: Open `http://localhost:3000` in Chrome/Firefox after running `./START_CONTROL_CENTER.sh` (or `./future_lab_control_center/START_LAB.sh`).
- **Lab LAN / Remote Tailscale Access**: Open `http://<HOST_PC_IP>:3000` (e.g., `http://192.168.0.129:3000` on Lab Wi-Fi, or `http://100.86.49.29:3000` over Tailscale). The frontend automatically points API calls to `:8000` on whichever hostname appears in your browser's address bar.

---

## 2. Top Network Status Header & Language Switcher

At the top of every screen, the **`NetworkStatusHeader`** displays real-time system health polled every `2 s`:

| Element | Meaning |
| :--- | :--- |
| **`EN / PT` Toggle Button** | Switches the entire dashboard instantaneously between **English** and **Portuguese** (persisted in browser `localStorage` under `future_lab_lang`). Defaults to English. |
| **`PC Host` Badge** | `ONLINE` (green) when the FastAPI backend (`:8000`) responds cleanly. |
| **`Nano (Cobot)` Badge** | `ONLINE` (green) when the Jetson Nano HTTP hardware bridge (`:8088`) is reachable on `.62` or `.250`. |
| **`Camera MJPEG` Badge** | `STREAM` (green) when the MyCobot wrist camera stream (`:8080/stream.mjpg`) is serving frames; `OFFLINE` (amber) when stopped. |
| **`TurtleBot 4` Badge** | `ONLINE` (green) when the TurtleBot 4 Discovery Server / RPi4 telemetry link is active; `DISCONNECTED` otherwise. |

Below the header sits the **Tab Switcher**, letting you jump between the two main workspaces without interrupting active background polling:

1. **Cell Control (`MyCobot 280 & Vision`)**
2. **TurtleBot 4 (`AMR & Integrated 3D View`)**

---

## 3. Tab 1: Cell Control (`MyCobot 280 & Vision`)

This tab controls cooperative multi-robot sorting cycles, live wrist-camera YOLO inspection, suction pump actuation, and manipulator pose calibration.

### 3.1 Master Cell Control Card (`CellControlPanel`)

#### A. Integrated Real Operation (Full Cooperative Mode)

Located at the top of the panel, the **Integrated Real Mode** box runs the complete physical workflow with MoveIt, 3D visualization, and real YOLOv8 inspection:

- **Visual Readiness Pills**: Live green/gray indicators for **`MoveIt + RViz`**, **`Integrated 3D`** (`rviz2_cobot_tb4_3d`), and **`Headless YOLO`**.
- **Start / Stop Integrated Real Button**: Enabled when no other cycle is running and both **TurtleBot Ready** (`mission_ready`) and **Single Manager** (`mission_manager` running with `instances === 1`) are true.
  - Clicking **Start** brings up MoveIt, re-verifies Nano hardware, opens the unified 3D view, verifies the camera stream, launches headless YOLO, and moves the arm to `scan`.
- **YOLO Candidate Confirmation Banner**: When the model classifies a candidate can (`tin_valid_blue*` or `tin_valid_red*`), an amber confirmation box shows the detected class and confidence percentage. Click **Confirm & Execute** to release the physical pick-and-place and TurtleBot 4 delivery cycle.

#### B. Master Operation Buttons & Tuning Sliders

| Control | Behavior |
| :--- | :--- |
| **`RESTART NANO (HW)`** (top-right red button) | Opens the `RebootOverlayModal` progress tracker while remotely releasing/locking servos, freeing `/dev/ttyTHS1`, restarting the Jetson Nano bridge + camera, and relaunching MoveIt 2 inside Docker. |
| **`START AUTO MODE`** | Sets cell mode to `auto` and starts continuous inspection/delivery cycles. |
| **`MANUAL MODE` / `INTERRUPT OPERATION`** | When idle, switches to step-by-step **Manual Mode** (`Go to SCAN` → `Authorize PICK` → `Authorize PLACE`). While *any* cycle is running, this button pulses orange and becomes **`INTERRUPT OPERATION`**, pausing motion immediately and opening the confirmation modal (`Abort` vs. `Resume`). |
| **`EMERGENCY (HOME)`** | Calls `POST /api/v1/cell/stop`, halting the cycle cleanly and sending the arm back to `home`. |
| **Cooldown Slider (`1.0 s – 10.0 s`)** | Delay between consecutive automatic cycles. |
| **YOLO Confidence Slider (`30% – 90%`)** | Minimum detection threshold required to validate a can (`60%` recommended). |
| **Arm Speed Slider (`1% – 15%`)** | Conservative speed percentage cap (`arm_speed`) applied to joint motions. |

#### C. Manual Step-by-Step Controls (Visible in Manual Mode)

When `mode === 'manual'`, a 3-column approval bar appears:

1. **Step 1 — Go to SCAN**: Moves the MyCobot to `scan` and turns on YOLO vision.
2. **Step 2 — Authorize PICK**: Remains disabled (`Waiting YOLO detection...`) until a valid can is detected; once detected, pulses green with the class and confidence. Clicking it executes `pick_approach → pick → pick_approach → place_approach`.
3. **Step 3 — Authorize PLACE**: Activates once the arm reaches `place_approach`. Clicking it moves to `place`, triggers the TurtleBot 4 handoff, turns the vacuum pump OFF, and returns to `home`.

#### D. Inter-Robot Handshake Test Panel (`Cobot -> TurtleBot 4`)

Use **`TEST HANDSHAKE (BLUE TIN)`** or **`TEST HANDSHAKE (RED TIN)`** to test the full 8-stage physical pick-place-deliver-dock cycle using a synthetic classification without waiting for live YOLO.

The status card underneath shows:

- Current phase (`idle`, `preflight_passed`, `moving_scan`, `starting_turtlebot`, `cobot_picking`, `cobot_placing`, `waiting_turtlebot_pickup`, `releasing_item`, `cobot_returning_home`, `waiting_delivery_and_dock`, `rollback`, `completed`, `failed`).
- Live gating booleans: **Turtle Ready**, **Single Manager**, and **Docked**.
- Active `run_id`, canonical class, and destination waypoint (`delivery_blue` or `delivery_red`).

---

### 3.2 Camera Vision & Suction Control (`CameraVisionPanel`)

- **Top Action Buttons**:
  - **Start / Restart Camera**: Restarts `nano_camera_server.py` on `:8080` and automatically schedules frame reconnection retries (`7 s`, `10 s`, `13 s`, `16 s`).
  - **Turn Off Camera**: Stops the Jetson Nano MJPEG stream.
  - **Test YOLO / Stop YOLO Test**: Toggles live standalone YOLOv8 inference overlay for bench testing.
  - **Turn On / Off Pump**: Direct suction pump toggle with **0 ms optimistic button feedback** while waiting for hardware confirmation.
  - **Raw Stream (`:8080`)**: Opens `http://<nano-ip>:8080/stream.mjpg` in a raw browser tab.
- **Video Viewport & Classification Badge**: Displays live camera frames and highlights the most recent fresh classification (`Red Tin`, `Blue Tin`, or generic object class with confidence `%`).

---

### 3.3 Teach Mode & Pose Calibration (`TeachModePanel`)

> [!IMPORTANT]
> When **Auto Mode** is actively running (`cellState.auto_running == true`), the entire Teach Mode panel displays an amber lock banner and disables pointer interaction so an operator cannot release servo torque mid-cycle.

Use this panel to calibrate the 6 poses stored in `cobot/mycobot_docker/cobot_poses.yaml`:

1. **Click `OPEN RVIZ 2 (3D)`** (optional) to view MoveIt 2 alongside physical calibration.
2. **Click `RELEASE MOTORS (1)`** while holding the arm with your hand, then guide the arm to the desired posture.
3. **Click `LOCK MOTORS (2)`** to re-engage holding torque.
4. **Click `RECORD (3)`** in the row for `home`, `scan`, `pick_approach`, `pick`, `place_approach`, or `place`.
5. **Test individually with `GO TO`** on any `Recorded` pose, or click **`PLAYBACK TEST`** to step through the recorded sequence.
6. **Click `SAVE TO DISK`** to persist the calibration cleanly (automatically creating `cobot_poses.yaml.bak`), **`CLEAR POSES`** to wipe, or **`RESTORE BACKUP`** to revert to the previous `.bak` snapshot.

---

## 4. Tab 2: TurtleBot 4 (`AMR & Integrated 3D View`)

This tab manages TurtleBot 4 localization, Nav2 bringup, OAK-D camera video, manual D-Pad driving, ROS 2 diagnostics, and Mission Manager routines.

### 4.1 Telemetry, Readiness Traffic Light & System Recovery

- **Telemetry Alert Banner**: Appears prominently in red if `telemetry_ok === false` (meaning `/odom`, `/battery_state`, or `/dock_status` stopped arriving from the Create 3 base).
- **Navigation Readiness & ROS 2 Traffic Light**: Displays live introspection badges for `/odom`, `/scan`, `/amcl_pose`, `/dock_status`, `/navigate_to_pose`, and `Mission Manager`.
- **Metric Cards**: Battery `%` & current (`A`) & charging indicator, Dock status (`Docked` vs. `Undocked`), live odometry/map pose `(x, y, yaw)`, and OAK-D status.
- **System Health & Inventory**: Lists detected nodes/services and provides 3 recovery buttons: **Restart Backend**, **Restart Cobot Discovery**, and **Restart TB4 Bringup** (with confirmation prompts).

### 4.2 OAK-D Live Feed, D-Pad Teleop & Network Diagnostics

- **OAK-D Camera Card**: Shows the live OAK-D RGB preview streamed via `GET /api/v1/turtlebot/camera_feed` (rate-limited at 5 FPS) with a **Start OAK-D Camera** button.
- **Manual Teleop D-Pad**:
  - Quick **`UNDOCK`** and **`DOCK`** buttons in the card header (plus an amber reminder whenever `isDocked == true`, because Create 3 ignores `/cmd_vel` while docked).
  - Directional pad buttons send velocity pulses (`+0.25 m/s` forward, `-0.25 m/s` reverse, `±0.6 rad/s` turn left/right) and a red center **Stop** button (`0.0, 0.0`).
- **ROS 2 Network Diagnostics**: Clicking **Diagnose** probes ping reachability (`192.168.0.129`) and counts visible ROS 2 topics on the Discovery Server.

### 4.3 Nav2 Startup Sequencer, Initial Pose & Mission Manager

The **Nav2 Sequencer** enforces the safe 5-step mobile navigation startup order:

1. **Step 1 — Start Localization** (`map_server` + `amcl`) + Stop button.
2. **Step 2 — Launch RViz2** (`view_navigation`) + Stop button.
3. **Steps 3 & 4 — Undock & Initial Pose**:
   - Enter `X`, `Y`, `Yaw (rad)` manually or click **`Use Dock Pose`** to prefill `dock_station` coordinates from `waypoints.yaml`.
   - Click **`Send Initial Pose`** (`/initialpose`) and watch the **AMCL Convergence** badge (`converged` / covariance).
   - Optionally click **`Save Current Dock Pose`** (`/save_dock_pose`) if the physical dock moved, or **`Clear Costmaps`** if Nav2 is blocked by phantom obstacle ghosts.
4. **Step 5 — Launch Nav2 Stack** (`controller_server`, `planner_server`, `bt_navigator`, `opennav_docking`) + Stop button.
5. **Integrated 3D View Card**: Click **`Launch 3D View`** to open the unified `integration_cobot_tb4` RViz2 scene combining both robots.

The **Mission Manager** panel lets you start/stop `mission_manager.py` and manually test individual mission signals (`Test Delivery: Blue / Red`, `Signal Item Released`, `Failure Routine`, `Restock Routine`, or **`CANCEL MISSION`**).

### 4.4 Real-Time Terminal Log Console

At the bottom of the TurtleBot 4 tab, the live log viewer tails host process logs with category tabs (**Localization**, **Nav2**, **Mission**, **RViz**, **All**), color-coding `ERROR`/`Failed` in red, `WARN` in amber, and `INFO`/`active` in green.

---

## 5. Global Safety & Progress Modals

| Modal | When It Appears | Operator Action Required |
| :--- | :--- | :--- |
| **`PanicOverlayModal`** | Full-screen red lock whenever `cell.panic_locked === true`. Indicates pump OFF, camera/MoveIt halted, and servo motors locked. | Verify the physical table and floor are completely clear, then click **Reset Panic & Restart Hardware**. |
| **`InterruptOverlayModal`** | Appears when `cell.status === 'interrupted_paused'` after clicking **Interrupt Operation**. | Choose **Abort Operation** (`abort: true` — returns any held item safely to `pick` and sends arm to `home`) or **Resume Operation** (`abort: false` — re-dispatches the interrupted pose). |
| **`RebootOverlayModal`** | Appears after clicking **Restart Nano (HW)** and displays a 5-stage progress bar (`~14 s` total) before refreshing status. | Wait for completion; the modal closes automatically. |
| **`NotificationToast`** | Top-right floating banner triggered by any API success, warning, or connection error. Auto-dismisses after `15 s` or on clicking `×`. | Read status or error message; errors from Portuguese backend routes are automatically translated when the UI is in English. |
