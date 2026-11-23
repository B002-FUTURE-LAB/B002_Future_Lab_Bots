# drawer_picking

The MyCobot 280 JN fetches an item from one of **four drawers**, releases it
at a **dropoff point**, and returns home. Press `1`-`4` to choose the drawer,
as many times as you want.

To avoid hitting the cabinet (the planner does not know it), every trip to a
drawer goes through a taught **safe** pose, and the arm goes **in and out of
the drawer in a straight line along the suction cup axis**, slowly, and back
out the same way. The dropoff is reached with a normal (free) move.

You first **teach** the poses by hand (configuration stage). Then the state
machine moves through them. In simulation, example poses are preselected.

## Run

| Step | Simulation | Real robot |
| :--- | :--- | :--- |
| 1. Bringup (terminal 1) | `./scripts/RUN_SIM.sh` | `./scripts/RUN_REAL.sh` |
| 2. Teach poses (once) | optional: `./scripts/TEACH.sh sim` | `./scripts/TEACH.sh real` |
| 3. Run (terminal 2) | `./scripts/RUN_STATE_MACHINE.sh sim` | `./scripts/RUN_STATE_MACHINE.sh real --speed 0.1` |

- The first run builds the Docker image (several minutes). ARM64 hosts work too.
- `RUN_REAL.sh` needs `JETSON_NANO_SSH_PASSWORD` in `future_lab_control_center/.env`.
- In real mode only taught poses are used. If one is missing, the state
  machine refuses to start and lists it.

## First time on the lab host

1. Get the code (the branch must be pushed first, `cobot` included):
   ```bash
   git clone --recurse-submodules -b feat/drawer-picking <repo-url>
   # or, in an existing clone:
   git fetch && git checkout feat/drawer-picking && git submodule update --init --recursive
   ```
2. Host needs: Docker with the `compose` plugin, `sshpass`, a desktop session
   (RViz window), and network access to the Jetson Nano.
3. `future_lab_control_center/.env` must define `JETSON_NANO_SSH_PASSWORD`
   (optional: `JETSON_NANO_IP`, default `192.168.0.62`; `JETSON_NANO_SSH_USER`, default `er`).
4. Stop anything else driving the arm: `docker stop mycobot_ros2` (and the
   Control Center cell, if it is running).
5. Run the "Real robot" column above. Commit `config/drawer_poses_real.yaml`
   after teaching to keep the poses.

## Teach (configuration stage)

`TEACH.sh` **only saves poses; it never moves the arm**. Order: `home`,
`safe`, `drawer_1_pick` .. `drawer_4_pick`, `dropoff`. For each one, put the
arm in the pose and press `Enter`:

- Simulation: drag the gimbal in RViz, **Plan & Execute**, `Enter`.
- Real robot: `r` (servos go limp, **hold the arm**), move it by hand, `Enter`
  (saves and locks the servos).

| Pose | Where |
| :--- | :--- |
| `home` | Initial / rest pose |
| `safe` | In front of the cabinet, well clear of it, wrist about as at the drawers |
| `drawer_N_pick` | Cup on the item, **cup axis pointing the way the arm must go in** |
| `dropoff` | Cup where the item is released |

For each drawer pick, `Enter` also stores the approach pose 8 cm
straight back along the cup axis (`--retreat` to change), or as far as
reachable down to 3 cm (`--min-retreat`). If not even that is reachable the
pose is not saved and the reason is shown. Usual causes: the arm is
stretched out (`home` is straight up, a singular pose: no straight line is
possible from there), a joint is at its limit, or the pose is in collision.
Bend the elbow and wrist more. If you press `Enter` while the arm is still
exactly at another saved pose (it has not moved), the wizard asks again. Everything else
(straight in, suction, straight out, dropoff, release) is done by the state machine.

Keys: `Enter` save, `r` release servos (real only), `n` skip, `b` back, `q` quit.
Re-teach part of the cell: `TEACH.sh real 2` (drawer 2), `TEACH.sh real dropoff`, `TEACH.sh real safe`.
Poses go to `config/drawer_poses_real.yaml` (or `_sim.yaml`). The previous file
is kept as `.bak`.

## State machine

```
IDLE -> GO_SAFE -> GO_DRAWER_APPROACH -> ENTER_DRAWER* -> SUCTION_ON -> EXIT_DRAWER*
     -> BACK_TO_SAFE -> GO_DROPOFF -> RELEASE -> RETURN_HOME -> IDLE
* straight line along the cup axis (--linear-speed, default 2 cm/s); the rest are free moves
any error -> ERROR -> straight back out (if inside) -> safe (if near the cabinet)
          -> release at the dropoff (if held) -> home -> IDLE
```

The whole sequence is the `CYCLE` table in `state_machine.py`. Keys pressed
during a cycle are ignored. Before every straight move the path is checked:
it must follow the cup axis (within 5 deg), without tilting the cup, and be
100% reachable, or the arm does not move. In real mode the state machine
asks for confirmation before its first move to `home`.

## Files

```text
drawer_picking/
├── docker-compose.yml        # container drawer_picking_ros2, cobot packages mounted (not copied)
├── config/                   # taught poses: drawer_poses_real.yaml, drawer_poses_sim.yaml
├── scripts/                  # RUN_SIM, RUN_REAL, TEACH, RUN_STATE_MACHINE (+ common.sh)
└── ros2_ws/src/drawer_picking/
    ├── drawer_picking/
    │   ├── state_machine.py  # the cycle (pure Python, unit tested)
    │   ├── poses.py          # pose names, example poses, load/save, checks
    │   ├── robot.py          # free moves (/move_action), straight lines (/compute_cartesian_path), bridge services
    │   ├── main.py           # drawer_state_machine: keys 1-4
    │   ├── teach.py          # drawer_teach: configuration stage
    │   ├── keyboard.py       # single-key input
    │   └── cabinet.py        # shows the example cabinet in RViz
    ├── launch/drawer_cell.launch.py   # cobot MoveIt + RViz + cabinet pose (CABINET)
    ├── config/drawer_cell.rviz        # robot, cabinet, MotionPlanning (gimbal + plan preview)
    ├── meshes/kks5_wall_assembly.stl
    └── test/
```

From the `cobot` submodule it uses `mycobot_description` (URDF),
`mycobot_280_jn_moveit_config` (MoveIt, RViz) and `mycobot_hw_interface`
(`mycobot_bridge`, mock in simulation). Do not run this container and
`cobot`'s `mycobot_ros2` stack at the same time: both use `ROS_DOMAIN_ID=42`.

## Example cell (simulation)

The KKS5 wall cabinet is shown 0.30 m in front of the robot. It is a visual
reference only, not a planning obstacle. The four example drawers are the
central bins of its two upper rows. The example poses use different wrist
configurations per drawer, so the wizard and the state machine warn about
big joint swings between `safe` and the drawers; teach the real cell with a
similar wrist to avoid that. Seen from the robot: `1` upper-left,
`2` upper-right, `3` lower-left, `4` lower-right.

## Tests

```bash
cd ros2_ws/src/drawer_picking && python3 -m pytest test -q
```
