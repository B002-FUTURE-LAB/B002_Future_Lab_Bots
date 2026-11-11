# First Delivery Mission

This tutorial walks you through running your first end-to-end cooperative mission between the **MyCobot 280** and the **TurtleBot 4**, starting with a zero-motion preflight check, proceeding to a synthetic handshake test, and finishing with a full vision-driven sorting mission (`Integrated Real Mode`).

---

## Prerequisites

Before starting a mission, verify that:

1. The Control Center stack is running (`./START_CONTROL_CENTER.sh`) and open at `http://localhost:3000`.
2. In the top **Network Status Header**, the indicators for **Host API**, **MyCobot (Nano)**, **TurtleBot 4**, and **Discovery Server** are green.
3. The MyCobot workspace and the TurtleBot 4 navigation corridors are clear of obstacles.
4. All 6 required manipulator poses (`home`, `scan`, `pick_approach`, `pick`, `place_approach`, `place`) exist in `cobot/mycobot_docker/cobot_poses.yaml` (see [Calibrate Cobot Poses](../guides/calibrate-cobot-poses.md)).

---

## Step 1: Prepare TurtleBot 4 Localization and Mission Manager

Switch to the **TurtleBot 4** tab in the Control Center dashboard (or run the commands via REST API):

1. **Start Nav2 Navigation**: Click **Launch Navigation (Nav2)** (`POST /api/v1/turtlebot/launch/nav`).
2. **Verify AMCL Localization**:
   - If the robot is docked on its charging station, click **Docked Pose** (`POST /api/v1/turtlebot/dock_pose`) to initialize AMCL at the known dock coordinates (`x = 0.068`, `y = -0.004`, `yaw = 3.133 rad`).
   - Otherwise, set the 2D Pose Estimate in RViz or via the dashboard's **Initial Pose** controls (see [Set Initial Pose and Dock Pose](../guides/set-initial-pose-and-dock-pose.md)).
3. **Start the Mission Manager**: Click **Start Mission Manager** (`POST /api/v1/turtlebot/mission_manager/start`).
4. **Check Readiness Gate**: Verify that the readiness badge reports `mission_ready: true`:

```bash
curl -s http://localhost:8000/api/v1/turtlebot/nav_readiness | jq
```

Expected key fields:

- `"mission_ready": true`
- `"amcl_fresh": true`
- `"dock_status_fresh": true`

---

## Step 2: Run the Hardware Handshake Test (Synthetic Vision)

Before relying on live YOLO classification, validate the physical pick-and-place and inter-robot ROS 2 handoff using a deterministic class (`blue` or `red`).

1. Place a can at the calibrated **PICK** spot on the MyCobot table.
2. Ensure the TurtleBot 4 is docked (or localized with fresh telemetry) and the suction pump is **OFF**.
3. Trigger the standalone handshake test via the **Cell Control Panel** or via `curl`:

```bash
curl -s -X POST http://localhost:8000/api/v1/cell/handshake_test \
  -H "Content-Type: application/json" \
  -d '{"item_class": "blue"}' | jq
```

4. Monitor progress in real time:

```bash
curl -s http://localhost:8000/api/v1/cell/status | jq '.handshake'
```

The handshake engine steps through 8 verified phases:

| Phase | Action Verified |
| :--- | :--- |
| `1/8 moving_scan` | MyCobot moves to `scan` and verifies joint convergence (`goto_pose_verified`). |
| `2/8 starting_turtlebot` | Host publishes fresh `/product_class` (`tin_valid_blue`) and calls `/start_delivery`; verifies `DeliveryRoutine` accepted `delivery_blue`. |
| `3/8 cobot_picking` | While TurtleBot undocks and navigates to `pickup_point`, MyCobot moves `pick_approach → pick` and confirms `pump_active == true`. |
| `4/8 cobot_placing` | MyCobot moves `pick_approach → place_approach → place` holding the can. |
| `5/8 waiting_turtlebot_pickup` | Waits up to `100 s` for `True` on `/turtlebot_at_pickup`. If it times out, the Cobot rolls back the can to `pick` instead of dropping it. |
| `6/8 releasing_item` | Turns suction pump OFF (`set_pump_verified(False)`) and publishes `/item_released_on_tb4` via the Host Mission Signal Agent (`:18081`). |
| `7/8 cobot_returning_home` | MyCobot returns `place_approach → home`. |
| `8/8 waiting_delivery_and_dock` | TurtleBot 4 navigates to `delivery_blue`, returns to `predock_point`, and completes physical docking (`/dock_status == true`). |

---

## Step 3: Run a Full Vision-Driven Mission (`Integrated Real Mode`)

Once the physical handshake succeeds, run the full autonomous pipeline with live YOLOv8 classification and 3D visualization:

1. Place a **Blue** or **Red** can under the wrist camera zone on the MyCobot table.
2. In the **Cell Control Panel**, start **Integrated Real Mode** (or call `POST /api/v1/cell/integrated_real/start`):

```bash
curl -s -X POST http://localhost:8000/api/v1/cell/integrated_real/start | jq
```

3. The orchestrator automatically:
   - Launches MoveIt 2 + RViz for the manipulator (`RUN_PLANNING_PC.sh`) and verifies `move_group` is alive.
   - Re-verifies the Jetson Nano HTTP bridge (`:8088`) after the Planning PC startup.
   - Launches the unified 3D cell RViz (`rviz2_cobot_tb4_3d`).
   - Checks/restarts the wrist-camera MJPEG stream (`http://192.168.0.62:8080/stream.mjpg`) and starts the headless YOLOv8 detector.
   - Moves the MyCobot to `scan` and collects **5 distinct, recent YOLO samples** within a `0.8 s – 3.0 s` window agreeing on the canonical class (`tin_valid_blue` or `tin_valid_red`).
4. Depending on the mode selected:
   - If **Operator Confirmation** is requested (`awaiting_confirm`), click **Confirm & Execute** (`POST /api/v1/cell/integrated_real/confirm`) once the candidate class is displayed.
   - The cell then executes the full 8-stage physical handshake and delivery cycle.

---

## Stopping or Aborting Safely

If you need to pause or abort the mission at any point:

- **Soft Interrupt / Pause**: Click **Interrupt** in the Cell Control Panel (`POST /api/v1/cell/interrupt`). A modal asks whether to **Resume (`abort: false`)** or **Abort (`abort: true`)** (`POST /api/v1/cell/interrupt_confirm`).
- **Safe Abort Cleanup**: Confirming **Abort** returns the can to the `pick` pose if the suction pump is active, turns the pump off, returns the MyCobot to `home`, cancels the TurtleBot 4 navigation goal, and commands the TurtleBot 4 to return to its dock.
- **Emergency Stop (PANIC)**: For immediate servo torque release on the MyCobot and velocity zeroing on the TurtleBot, see [Emergency Stop](../guides/emergency-stop.md).
