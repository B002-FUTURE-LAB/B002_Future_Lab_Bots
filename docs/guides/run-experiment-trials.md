# Run Experiment Trials (60-Trial Campaign)

This guide covers the step-by-step operational workflow for executing and recording standardized experimental runs using the `experiments/` toolkit (`record_trial.sh`, `generate_campaign_plan.py`, and `validate_trial.py`).

For the full scientific methodology, hypothesis definitions, and statistical analysis plan, see [60-Trial Experimental Protocol](../research/trial-protocol.md) and [Audit Logging & Event Pipeline](../research/audit-logging.md).

---

## Overview of the Experimental Campaign

A complete campaign consists of **60 physical runs** divided across **3 obstacle conditions** (20 runs per condition: 10 `blue` cans and 10 `red` cans):

1. `no_obstacle`: Clear navigation corridors between `pickup_point` and `delivery_blue` / `delivery_red`.
2. `static_obstacle`: A static cylindrical box/obstacle (`0.30 × 0.30 × 0.40 m`) placed at a fixed coordinate on the primary path, forcing Nav2 global/local replanning.
3. `dynamic_obstacle`: Controlled dynamic interference crossing the corridor when the TurtleBot 4 passes a reference mark (`1.0 m` after leaving `pickup_point`).

All raw data is stored outside the Git repository at `~/B002_experiment_data/<campaign_id>/` (overrideable via `B002_EXPERIMENT_ROOT`).

---

## Step 1: Generate the Randomized Campaign Plan

Before starting a new campaign, generate a balanced, seed-reproducible run schedule (`plan.csv`):

```bash
cd ~/B002_Future_Lab_Bots
python3 experiments/generate_campaign_plan.py \
  --campaign campaign_20260815 \
  --seed 20260815
```

This creates `~/B002_experiment_data/campaign_20260815/plan.csv` containing 60 rows (`trial_number`, `condition`, `run_in_condition`, `can_color`), with balanced 10 `blue` + 10 `red` allocations per condition.

---

## Step 2: Run the Zero-Motion Smoke Test (`--smoke`)

Before running physical trials in a session, always execute a 10-second smoke recording to verify that ROS 2 Discovery, MCAP bag recording, dashboard state polling, and event relaying work cleanly:

```bash
cd ~/B002_Future_Lab_Bots
./experiments/record_trial.sh --smoke --duration 10 --campaign campaign_20260815
```

What `--smoke` verifies (`experiments/validate_trial.py --mode smoke`):

- Recorded MCAP duration $\ge 2.0\text{ s}$.
- Required baseline topics have messages: `/tf`, `/tf_static`, `/diagnostics`, `/future_lab/events`.
- `dashboard_state.jsonl` exists and contains 1 Hz snapshots from `/api/v1/cell/status`, `/api/v1/turtlebot/status`, `/api/v1/turtlebot/nav_readiness`, `/api/v1/cobot/status`, and `/api/v1/health/full`.
- Writes `validation.json` with `"valid": true`.

---

## Step 3: Execute a Physical Trial (`record_trial.sh`)

For each row in `plan.csv`:

1. **Position the Physical Can**: Place the specified can (`blue` or `red`) at the pickup mark on the MyCobot table.
2. **Verify Robot Initial State**:
   - TurtleBot 4 is docked (`is_docked: true`), battery $\ge 25\%$, and `mission_ready: true`.
   - MyCobot is at `home` (`pump_active: false`).
3. **Start the Trial Recorder**:

```bash
cd ~/B002_Future_Lab_Bots
./experiments/record_trial.sh \
  --condition no_obstacle \
  --run 1 \
  --can blue \
  --campaign campaign_20260815 \
  --operator "LabOperator" \
  --notes "Run 01 nominal"
```

4. **Trigger the Mission**:
   - While `record_trial.sh` is recording, trigger **Integrated Real Mode** (`POST /api/v1/cell/integrated_real/start`) or the **Handshake Test** (`POST /api/v1/cell/handshake_test`) from the Control Center dashboard.
5. **Stop the Recorder**:
   - Once the TurtleBot 4 finishes docking back at `dock_station` and the MyCobot is at `home`, press **`Ctrl+C`** in the `record_trial.sh` terminal.

---

## Step 4: Automatic Post-Trial Validation & Artifacts

When you press `Ctrl+C`, `record_trial.sh` gracefully stops `ros2 bag record`, `ffmpeg`, `sample_dashboard_state.py`, and `event_relay.py`, captures a final snapshot (`post_snapshot.json`), and runs `validate_trial.py --mode real`.

Each trial directory (`~/B002_experiment_data/<campaign>/trials/<trial_id>/`) contains:

| File / Folder | Description |
| :--- | :--- |
| `trial_manifest.json` | Start/end timestamps, Git commit SHAs of root + all 3 submodules, operator name, condition, run number, can color. |
| `pre_snapshot.json` / `post_snapshot.json` | Complete API status snapshots before and after the trial. |
| `rosbag/metadata.yaml` & `*.mcap.zstd` | Zstd-compressed MCAP rosbag of navigation, TF, diagnostics, `/product_class`, `/turtlebot_at_pickup`, `/item_released_on_tb4`, `/mycobot/joint_states`, and `/future_lab/events`. |
| `dashboard_state.jsonl` | 1 Hz time series of all Control Center backend endpoints during the trial. |
| `backend_events_before.jsonl` / `backend_events_after.jsonl` | Snapshots of `backend/runtime/events.jsonl`. |
| `cobot_camera.mp4` | H.264 (`10 fps`) recording of the MyCobot wrist camera MJPEG stream (unless `--no-video` was passed). |
| `validation.json` | Automated validation report checking duration ($\ge 30\text{ s}$) and message counts across all 12 required `REAL` topics. |

> [!TIP]
> Single-instance locking (`flock` on `$EXPERIMENT_ROOT/.record_trial.lock`) prevents accidentally running two trial recorders simultaneously.
