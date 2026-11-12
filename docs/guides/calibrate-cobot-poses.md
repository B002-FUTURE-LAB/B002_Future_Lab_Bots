# Calibrate Cobot Poses (Teach Mode)

The **MyCobot 280** uses 6 named joint-space poses stored in `cobot/mycobot_docker/cobot_poses.yaml` to execute inspection and pick-and-place cycles. Whenever the supply table, camera mount, or TurtleBot `pickup_point` is adjusted, recalibrate these poses using **Teach Mode**.

---

## The 6 Required Poses

All cell workflows (`auto`, `manual`, `handshake_test`, and `integrated_real`) require these 6 pose keys in `cobot/mycobot_docker/cobot_poses.yaml` (angles stored in **radians** for `[joint1, joint2, joint3, joint4, joint5, joint6]`):

| Pose Name | Purpose in Cycle | Typical Joint Values (rad) |
| :--- | :--- | :--- |
| `home` | Safe parked posture outside the camera field of view and away from the TurtleBot tray. | `[0.0, 0.0, 0.0, 0.0, 0.0, 0.0]` |
| `scan` | Overhead camera posture looking down at the supply table for YOLOv8 classification. | `[1.264, -0.056, -1.169, -0.178, 0.044, -0.175]` |
| `pick_approach` | Safe hover posture ~8–10 cm directly above the supply table pickup spot. | `[1.309, -0.579, -0.840, 0.036, 0.059, -0.251]` |
| `pick` | Contact posture where the suction cup presses gently onto the top lid of the can on the table. | `[1.298, -0.946, -0.780, 0.281, 0.089, -0.253]` |
| `place_approach` | Safe hover posture above the TurtleBot 4 loading tray at `pickup_point`. | `[-0.869, -0.371, -1.031, -0.068, -0.051, -0.145]` |
| `place` | Release posture just above the TurtleBot 4 tray where turning the vacuum pump OFF deposits the can upright. | `[-0.869, -0.506, -1.093, 0.059, -0.030, -0.138]` |

> [!IMPORTANT]
> If any of these 6 poses is missing from `cobot_poses.yaml`, the preflight gate in `cell_routes.py` (`_handshake_infrastructure_preflight`) returns `HTTP 409 Conflict` and refuses to start the cycle.

---

## Calibrating Poses via the Control Center Dashboard (Recommended)

The **Teach Mode Panel** (`TeachModePanel.jsx`) in the Control Center dashboard lets you calibrate poses by hand-guiding the physical robot arm or jogging individual joints:

1. Open `http://localhost:<FRONTEND_PORT>` and locate the **Teach Mode & Calibration** panel.
2. **Release Servos (Hand-Guiding)**:
   - Hold the manipulator arm firmly with one hand so it does not drop under gravity.
   - Click **Release Servos** (`POST /api/v1/cobot/release_servos` → calls `POST http://<JETSON_NANO_IP>:<NANO_BRIDGE_PORT>/servos/release`).
   - Move the arm smoothly by hand to the desired posture (e.g., pressing the suction cup onto the can at `pick`, or hovering over the docked/staged TurtleBot tray at `place`).
3. **Lock Servos**:
   - Click **Lock Servos** (`POST /api/v1/cobot/lock_servos` → calls `POST http://<JETSON_NANO_IP>:<NANO_BRIDGE_PORT>/servos/lock`) to re-engage holding torque at the current posture.
4. **Verify Live Joint Angles**:
   - Check the live joint readout in the panel (`GET /api/v1/cobot/status`, polled from `http://<JETSON_NANO_IP>:<NANO_BRIDGE_PORT>/get_angles`).
5. **Save Pose**:
   - Select or type the pose name (`home`, `scan`, `pick_approach`, `pick`, `place_approach`, or `place`).
   - Click **Save Current Pose** (`POST /api/v1/cobot/poses/<name>`).
6. **Test Transition**:
   - Click **Go To Pose** next to `pick_approach` and `pick` at low speed (`0.15`–`0.30`) to verify smooth collision-free motion.

---

## Calibrating Poses via CLI Scripts (`cobot/mycobot_docker/`)

You can also calibrate poses directly from a terminal on the Host PC while the `mycobot_ros2` container is running:

### Step 1: Enter Interactive Teach Mode

```bash
cd ~/B002_Future_Lab_Bots/cobot/mycobot_docker
./RUN_TEACH.sh
```

`RUN_TEACH.sh` connects to the Jetson Nano (`<JETSON_NANO_IP>`), releases the servo motors so you can guide the arm by hand, and prints the live joint angles in radians. Press `Enter` when positioned to lock the servos back in place.

### Step 2: Save the Current Joint State as a Named Pose

In another terminal on the Host PC, run `SAVE_POSE.sh <pose_name>`:

```bash
cd ~/B002_Future_Lab_Bots/cobot/mycobot_docker
./SAVE_POSE.sh pick
```

`SAVE_POSE.sh` reads a single message from `/joint_states` inside `mycobot_ros2` and writes the 6 radian values under the specified key in `cobot/mycobot_docker/cobot_poses.yaml`.

### Step 3: Test Saved Poses from CLI

```bash
cd ~/B002_Future_Lab_Bots/cobot/mycobot_docker
./GO_POSE.sh pick_approach
./GO_POSE.sh pick
./GO_POSE.sh home
```

---

## Automatic Backup & Restore (`cobot_poses.yaml.bak`)

Every time you save or delete a pose through the Control Center API (`cobot_node.py`):

- The backend automatically copies `cobot_poses.yaml` to `cobot/mycobot_docker/cobot_poses.yaml.bak` before writing changes.
- To revert to the previous calibration, click **Restore Pose Backup** in the Teach Mode Panel or call:

```bash
curl -s -X POST http://localhost:<BACKEND_PORT>/api/v1/cobot/poses_restore_backup | jq
```

---

## How Hardware Pose Verification Works (`goto_pose_verified`)

During handshake tests and `Integrated Real Mode`, the backend does not rely on open-loop sleep timers. Instead, `CobotNode.goto_pose_verified(pose_name, speed)` (`backend/ros2_nodes/cobot_node.py`):

1. Sends the target joint angles to the Jetson Nano HTTP bridge (`GET /move_joints?j=d1,d2,d3,d4,d5,d6&speed=S`) and publishes the trajectory on `/arm_controller/follow_joint_trajectory` for RViz/MoveIt synchronization.
2. Polls `GET http://<JETSON_NANO_IP>:<NANO_BRIDGE_PORT>/get_angles` until the maximum per-joint error between measured physical encoder angles and the target pose is within tolerance (default `0.15 rad` / `~8.6°`), or raises an error on timeout.
