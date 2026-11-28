# Pick Items from the Drawer Cabinet

You want the MyCobot 280 to fetch an item from one of four drawers, release
it at a dropoff point, and return home. You choose the drawer with the keys
`1` to `4`, as many times as you want.

You teach the target poses by hand first (configuration stage), then the
state machine moves through them. Everything is in the `drawer_picking/`
folder at the repository root; its `README.md` lists the files.

!!! warning "One stack at a time"
    The `drawer_picking_ros2` container and the `cobot` container
    `mycobot_ros2` both use `ROS_DOMAIN_ID=42`. Run `docker stop mycobot_ros2`
    before you start this cell.

---

## How It Works

| Item | Value | Source |
| :--- | :--- | :--- |
| Cycle | `IDLE`, `safe`, drawer approach, straight in, suction on, straight out, `safe`, dropoff (free move), release, `home` | `CYCLE` in `state_machine.py` |
| Straight-line moves | Cup tip on a straight line along the cup axis, at `--linear-speed` (default 0.02 m/s). Checked before moving: within 5 deg of the cup axis, no cup tilt, 100% reachable. | `linear()` in `robot.py` |
| Error handling | Any failure: straight back out if inside a drawer, `safe` if near the cabinet, release the item at the dropoff if held, `home`, `IDLE` | `state_machine.py` |
| Poses | Taught: `home`, `safe`, `drawer_N_pick` (N = 1..4), `dropoff`. Generated: `drawer_N_approach` (8 cm back along the cup axis). Radians. | `poses.py` |
| Real robot poses | Only poses taught with `TEACH.sh real`. No fallback to the simulation poses. | `config/drawer_poses_real.yaml` |
| Simulation poses | Preselected example, optional overrides | `poses.py`, `config/drawer_poses_sim.yaml` |
| Example cabinet | KKS5 wall cabinet, 0.30 m in front of the robot, visual only (not a planning obstacle) | `CABINET` in `launch/drawer_cell.launch.py` |

---

## Part 1: Simulation

### Step 1: Start the Simulated Cell

```bash
cd ~/B002_Future_Lab_Bots/drawer_picking
./scripts/RUN_SIM.sh
```

The first run builds the image from `cobot/mycobot_docker/Dockerfile` and takes
several minutes. On ARM64 hosts the script uses `ros:galactic` as the base
image.

**Check:** RViz shows only the arm and the cabinet in front of it. The
terminal prints `You can start planning now!`.

### Step 2: Run the State Machine

In a second terminal:

```bash
cd ~/B002_Future_Lab_Bots/drawer_picking
./scripts/RUN_STATE_MACHINE.sh sim
```

Press `1` (no `Enter` needed).

**Check:** the terminal prints the states from
`[STATE] GO_SAFE (drawer 1)` to `[STATE] IDLE`, with
`-> drawer_1_pick (straight line, 8.0 cm)` on the way in, then
`Drawer 1 done`. Press `2`, `3`, `4` or `1` again to repeat.

### Step 3: Run the Unit Tests

```bash
cd ~/B002_Future_Lab_Bots/drawer_picking/ros2_ws/src/drawer_picking
python3 -m pytest test -q
```

**Check:** all tests pass (`test_geometry.py` is skipped outside the container).

---

## Part 2: Real Robot

!!! note "Not verified"
    Part 2 was not tested on the physical robot yet. In simulation the
    teach wizard, pump and servo calls were tested against the mock bridge,
    which accepts them without moving hardware.

### Step 1: Start the Real Cell

`future_lab_control_center/.env` must define `JETSON_NANO_SSH_PASSWORD`.

```bash
cd ~/B002_Future_Lab_Bots/drawer_picking
./scripts/RUN_REAL.sh
```

**Check:** the script prints `Bridge OK`, and the RViz arm follows the real
arm.

### Step 2: Teach the Poses (Configuration Stage)

In a second terminal:

```bash
./scripts/TEACH.sh real
```

The wizard **only saves poses; it never moves the arm**. It asks, in order,
for `home`, `safe`, `drawer_1_pick` to `drawer_4_pick` and `dropoff`. For
each pose:

1. Press `r`. After 2 seconds the servos go limp: **hold the arm**.
2. Move the arm by hand to the pose.
3. Press `Enter`. The position is saved and the servos lock.

For `drawer_N_pick`, `Enter` also stores the approach pose,
8 cm straight back along the cup axis, or as far as reachable down to 3 cm
(`--retreat`, `--min-retreat`). If not even 3 cm is reachable, nothing is
saved and the reason is shown: usually the arm is stretched out (`home`,
straight up, is singular), a joint is at its limit, or the pose is in
collision. Bend the elbow and wrist more and try again.
The straight moves in and out, the suction and the release are done by the
state machine, not by the wizard.

| Key | Action |
| :---: | :--- |
| `Enter` | Save the current position (and lock the servos) |
| `r` | Release the servos to move the arm by hand (real robot only) |
| `n` / `b` / `q` | Skip / back / quit (quit locks the servos) |

In simulation there is no `r`: drag the gimbal in RViz, click **Plan &
Execute**, wait until the arm gets there, then press `Enter`. You can also
type joint values in the **Joints** tab of the MotionPlanning panel. If the
arm has not moved (it is still at another saved pose), the wizard warns you.

Tips:

- The planner does not know the cabinet. Free moves happen only between
  `home`, `safe` and the approach poses. Teach `safe` in front of the cabinet,
  well clear of it, with the wrist about as it will be at the drawers. The
  wizard warns if a joint turns more than 1.5 rad between `safe` and a drawer.
- At `drawer_N_pick`, point the cup axis the way the arm must enter the
  drawer, and check that 8 cm back along it is outside the drawer.
- To re-teach part of the cell: `./scripts/TEACH.sh real 2` (drawer 2),
  `./scripts/TEACH.sh real dropoff` or `./scripts/TEACH.sh real safe`. The
  previous file is kept as `.bak`.

**Check:** the wizard ends with `All poses ready`.

!!! danger "Moving hardware"
    Keep a hand on the emergency stop the first time, start with
    `--speed 0.1 --linear-speed 0.01`, and run each drawer once while
    watching it before running cycles in a row. See
    [Emergency stop](emergency-stop.md).

### Step 3: Run the State Machine

```bash
./scripts/RUN_STATE_MACHINE.sh real --speed 0.1
```

Before its first move to `home` the state machine asks you to press `Enter`:
if the arm is inside a drawer, move it out first.

**Check:** the arm passes through `safe`, enters and leaves the drawer in a
straight line, the pump turns on in `SUCTION_ON` and off in `RELEASE`, and
every cycle ends at `home`.

---

## Troubleshooting

| Symptom | Cause | Fix |
| :--- | :--- | :--- |
| `Poses not ready for mode "real"` | Some poses were not taught yet | `./scripts/TEACH.sh real` (the message lists the missing ones) |
| `MoveIt (/move_action) not found` | The bringup is not running, or it runs in the other mode (different RMW) | Start `RUN_SIM.sh` or `RUN_REAL.sh` and use the same mode in every script |
| `path is ... deg off the cup axis` or `cup axis tilts` | The approach pose is not on the cup axis of the target (taught by hand, the target was re-taught, or it was taught before the `pump_tcp` fix in `cobot`) | Re-teach that pick with `TEACH.sh real N`; the approach is regenerated |
| `only N% of the straight line is reachable` | Joint limit or singularity on the line | Re-teach the target with another wrist position, or a smaller `--retreat` |
| A key does nothing | A cycle was running; keys pressed during a cycle are ignored | Wait for `[STATE] IDLE` |
| Topics from another robot stack appear | `mycobot_ros2` also runs on domain 42 | `docker stop mycobot_ros2` |

---

## Related Pages

- [Calibrate Cobot poses](calibrate-cobot-poses.md)
- [Submodule: cobot](../reference/submodules/cobot.md)
- [Operational scripts](../reference/scripts.md)
- [ROS interfaces](../reference/ros-interfaces.md)
