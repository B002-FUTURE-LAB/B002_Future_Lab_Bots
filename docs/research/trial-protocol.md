# 60-Trial Experimental Protocol

This page is the full English reference for the **60-Trial Experimental Campaign** conducted in Laboratory B002 (translated and expanded from the original lab protocol `docs/PROTOCOLO_60_ENSAIOS.md`).

For operational CLI commands, see [Run Experiment Trials](../guides/run-experiment-trials.md) and [Audit Logging & Event Pipeline](audit-logging.md).

---

## 1. Experimental Design & Factor Matrix

The experiment evaluates the end-to-end reliability, cycle time, localization precision, and recovery behavior of the cooperative **MyCobot 280 + TurtleBot 4** cell across **60 physical runs**:

| Experimental Condition (`--condition`) | Number of Runs | Can Allocation | Description |
| :--- | :---: | :---: | :--- |
| **`no_obstacle`** | 20 (`run 1..20`) | 10 `blue`, 10 `red` | Nominal baseline: clear laboratory corridors between `dock_station`, `pickup_point`, and `delivery_blue` / `delivery_red`. |
| **`static_obstacle`** | 20 (`run 1..20`) | 10 `blue`, 10 `red` | A static box obstacle (`0.30 × 0.30 × 0.40 m`) placed at a fixed floor mark along the primary delivery trajectory, forcing Nav2 local/global costmap replanning. |
| **`dynamic_obstacle`** | 20 (`run 1..20`) | 10 `blue`, 10 `red` | Dynamic human/object crossing: an obstacle crosses the navigation corridor perpendicularly when the TurtleBot 4 passes a floor trigger line `1.0 m` after departing `pickup_point`. |

### Randomization & Reproducibility

To prevent battery drain or thermal drift from biasing a single condition, run order is randomized within balanced blocks using `experiments/generate_campaign_plan.py` with a fixed PRNG seed (`--seed 20260815`), stored in `~/B002_experiment_data/<campaign>/plan.csv`.

---

## 2. Recorded Data Streams Per Trial

Every trial folder (`trials/<timestamp>_<condition>_runXX_<color>/`) captures four synchronized evidence streams:

1. **Zstd-Compressed ROS 2 MCAP Bag (`rosbag/`)**:
   - Navigation & Control: `/amcl_pose`, `/odom`, `/scan`, `/cmd_vel`, `/cmd_vel_unstamped`, `/navigate_to_pose/_action/status`, `/local_costmap/costmap`, `/global_costmap/costmap`, `/plan`.
   - Transforms & Diagnostics: `/tf`, `/tf_static`, `/diagnostics`, `/battery_state`, `/dock_status`, `/hazard_detection`.
   - Inter-Robot Handshake & Audit: `/product_class`, `/turtlebot_at_pickup`, `/item_released_on_tb4`, `/turtlebot_battery_emergency`, `/mycobot/joint_states`, `/future_lab/events`.
   - *Note*: Uncompressed OAK-D raw video (`/oakd/*`) is excluded from the MCAP bag to preserve disk I/O and DDS bandwidth.
2. **1 Hz Control Center State Series (`dashboard_state.jsonl`)**:
   - Sampled by `experiments/sample_dashboard_state.py` from `/api/v1/cell/status`, `/api/v1/turtlebot/status`, `/api/v1/turtlebot/nav_readiness`, `/api/v1/cobot/status`, and `/api/v1/health/full`.
3. **Structured Event Log (`backend_events_before.jsonl` & `backend_events_after.jsonl`)**:
   - Every state transition (`handshake_transition`, `integrated_real_transition`, and mutating HTTP calls) emitted by `backend/experiment_audit.py` with UTC timestamps and `monotonic_ns`.
4. **Wrist-Camera Video (`cobot_camera.mp4`)**:
   - Recorded at `10 fps` (`libx264`, `ultrafast`, `crf 28`) from `http://<JETSON_NANO_IP>:<CAMERA_STREAM_PORT>/stream.mjpg`.

---

## 3. Automated Trial Validation Criteria (`validate_trial.py`)

Immediately after stopping a recording, `experiments/validate_trial.py` inspects `rosbag/metadata.yaml` and `dashboard_state.jsonl` and writes `validation.json`:

| Criterion | `smoke` Mode | `real` Mode |
| :--- | :---: | :---: |
| **Minimum Bag Duration** | $\ge 2.0\text{ s}$ | $\ge 30.0\text{ s}$ |
| **`dashboard_state.jsonl` Present** | Required | Required |
| **Required Topics ($\ge 1$ message)** | `/tf`, `/tf_static`, `/diagnostics`, `/future_lab/events` | `/tf`, `/tf_static`, `/scan`, `/odom`, `/amcl_pose`, `/battery_state`, `/dock_status`, `/diagnostics`, `/product_class`, `/turtlebot_at_pickup`, `/item_released_on_tb4`, `/future_lab/events` |

---

## 4. Primary Metrics & Statistical Analysis Plan

From each validated trial, post-processing extracts:

- **End-to-End Cycle Time ($T_{\text{total}}$)**: Elapsed time from mission start (`starting_turtlebot`) to confirmed physical re-docking (`dock_status_measured == True`).
- **Phase Breakdown**:
  - $T_{\text{undock}}$: Undock + `8.0 s` stabilization.
  - $T_{\text{nav\_pickup}}$: Navigation time from `dock_station` to `pickup_point`.
  - $T_{\text{cobot\_pick\_place}}$: Manipulator time from `scan` through `pick` to `place` (executed in parallel with $T_{\text{undock}} + T_{\text{nav\_pickup}}$).
  - $T_{\text{handoff\_wait}}$: Waiting time at `pickup_point` until `/item_released_on_tb4`.
  - $T_{\text{nav\_delivery}}$: Navigation time from `pickup_point` to `delivery_blue` or `delivery_red` (primary metric affected by `no_obstacle` vs. `static_obstacle` vs. `dynamic_obstacle`).
  - $T_{\text{return\_dock}}$: Navigation to `predock_point` + IR docking completion.
- **Path Length & Efficiency**: Integrated odometry/AMCL path length $L = \sum \sqrt{\Delta x^2 + \Delta y^2}$ compared against the Euclidean baseline.
- **Success Rate & Rollback Rate**: Percentage of runs completing without safety rollback or operator intervention.
