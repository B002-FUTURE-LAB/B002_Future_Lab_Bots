# Set Initial Pose and Dock Pose

Accurate localization in the `map` frame (`turtlebot4_jazzy/maps/Mapa_Lab.yaml`) is required before the TurtleBot 4 can execute autonomous missions. The `MissionBase` pre-navigation gate refuses to send any Nav2 goal unless `/amcl_pose` has been updated within the last `3.0 s` (`nav_input_max_age_s`) with at least `5` stable samples.

---

## When to Use Each Method

| Situation | Recommended Method |
| :--- | :--- |
| Robot is physically sitting on the charging dock | **Docked Pose Shortcut** (`POST /api/v1/turtlebot/dock_pose`) |
| Robot is undocked at a known position on the laboratory floor | **Interactive 2D Pose Estimate** (Dashboard map or RViz) |
| Charging dock was physically moved to a new location in the room | **Calibrate & Save New Dock Pose** (`/save_dock_pose` service) |

---

## Method 1: Initialize Pose While Docked (Recommended)

When the TurtleBot 4 is resting on its charging station (`/dock_status` reports `is_docked: true`), initialize AMCL directly from the calibrated `dock_station` coordinates stored in `turtlebot4_jazzy/params/waypoints.yaml`:

### Via Control Center Dashboard

1. Open the **TurtleBot 4** tab in `http://localhost:<FRONTEND_PORT>`.
2. Ensure **Launch Navigation (Nav2)** is active.
3. Click **Set Docked Pose** in the localization panel.

### Via REST API

```bash
curl -s -X POST http://localhost:<BACKEND_PORT>/api/v1/turtlebot/dock_pose | jq
```

This publishes a `geometry_msgs/msg/PoseWithCovarianceStamped` message on `/initialpose` with the calibrated dock coordinates (`x = 0.068`, `y = -0.004`, `yaw = 3.133 rad`, covariance `0.05` on X/Y and `0.03` on yaw) and waits until `/amcl_pose` converges within:

- Position error $\le 0.25\text{ m}$ (`DOCK_POSE_MAX_DISTANCE_M`)
- Yaw error $\le 0.35\text{ rad}$ (`DOCK_POSE_MAX_YAW_ERROR_RAD`)

---

## Method 2: Set Arbitrary Initial Pose (`2D Pose Estimate`)

If the TurtleBot 4 starts away from the dock:

### Via Dashboard Interactive Map

1. In the **TurtleBot 4** tab, locate the **2D Occupancy Map** canvas (`GET /api/v1/turtlebot/map`).
2. Click the robot's physical location on the map and drag in the direction the robot is facing, or enter `x`, `y`, and `yaw` (radians) in the manual pose inputs.
3. Click **Apply Initial Pose**.

### Via REST API

```bash
curl -s -X POST http://localhost:<BACKEND_PORT>/api/v1/turtlebot/initial_pose \
  -H "Content-Type: application/json" \
  -d '{"x": -0.608, "y": -0.022, "yaw": 3.133}' | jq
```

### Via RViz2

1. Launch RViz on the Host PC (`POST /api/v1/turtlebot/launch/rviz`).
2. Click **2D Pose Estimate** in the top toolbar.
3. Click and drag on the map at the robot's position and heading.

---

## How Automatic Dock Localization Works (`wait_for_map_tf.py`)

When `START_NAV_DISCOVERY.sh` launches the navigation stack on the Host PC, it also launches `turtlebot4_jazzy/scripts/wait_for_map_tf.py`:

1. The helper node subscribes to `/dock_status` (`irobot_create_msgs/msg/DockStatus`) and `/amcl_pose`.
2. As soon as AMCL is active and `/dock_status` confirms `is_docked == True`, it automatically publishes `/initialpose` using `dock_station` from `waypoints.yaml`.
3. It verifies that the `map -> odom -> base_link` TF chain is valid before exiting.

---

## Method 3: Recalibrate and Save the Physical Dock Coordinates

If the charging station is physically relocated inside Lab B002, update `dock_station` and `predock_point` in `turtlebot4_jazzy/params/waypoints.yaml`:

1. Localize the robot accurately using RViz **2D Pose Estimate** so that laser scans (`/scan`) align tightly with the walls on the map.
2. Dock the robot onto the charging station (`POST /api/v1/turtlebot/mission/dock`).
3. With the Mission Manager running and the robot docked, call the `/save_dock_pose` service on the Host PC:

```bash
ros2 service call /save_dock_pose std_srvs/srv/Trigger "{}"
```

What `/save_dock_pose` does (`MissionBase._save_dock_pose_From_tf`):

1. Looks up the current transform `map -> base_link` via TF2.
2. Saves that pose as `dock_station` in `turtlebot4_jazzy/params/waypoints.yaml`.
3. Computes `predock_point` automatically **0.50 m directly in front of the dock** along the dock approach heading (`px = x + 0.50 * cos(yaw)`, `py = y + 0.50 * sin(yaw)`).
4. Atomically rewrites `turtlebot4_jazzy/params/waypoints.yaml` so future missions and `dock_pose` calls use the new coordinates immediately.
