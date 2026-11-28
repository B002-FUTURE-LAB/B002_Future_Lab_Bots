# Submodule Reference: `cobot` (`Cobot`)

- **Repository URL**: `git@github.com:B002-FUTURE-LAB/Cobot.git`
- **Mount Path**: `cobot/`
- **Active Branch**: `featnew-yolo`
- **Architecture**: Hybrid Host Container (**ROS 2 Galactic** in `mycobot_ros2` on `ROS_DOMAIN_ID=42`) + Physical **Jetson Nano** HTTP Micro-Bridge (`<JETSON_NANO_IP>:<NANO_BRIDGE_PORT>`)

---

## Directory Layout

```text
cobot/
├── nano_micro_bridge.py                  # HTTP :<NANO_BRIDGE_PORT> server running on the Jetson Nano (serial + GPIO)
├── START_COBOT_DISCOVERY_HOST.sh         # Starts optional FastDDS Discovery Server on :<COBOT_DISCOVERY_PORT> (Domain 42)
├── cobot_shadow_bridge/
│   ├── cobot_exporter_galactic.py        # Legacy UDP :<LEGACY_UDP_PORT> joint state exporter
│   └── cobot_importer_jazzy.py           # Legacy UDP :<LEGACY_UDP_PORT> joint state importer (/mycobot_shadow/joint_states)
└── mycobot_docker/
    ├── Dockerfile                        # Ubuntu 20.04 + ROS 2 Galactic + MoveIt 2 + pymycobot image
    ├── docker-compose.yml                # Defines mycobot_ros2 container (network_mode: host, Domain 42)
    ├── cobot_poses.yaml                  # Calibrated 6-DOF joint poses (home, scan, pick, place, etc.)
    ├── cyclone_dds_pc.xml                # CycloneDDS unicast peer config for Host PC
    ├── cyclone_dds_nano.xml              # CycloneDDS unicast peer config for Jetson Nano
    ├── fastdds_no_shm.xml                # FastDDS UDPv4-only profile (disables cross-container SHM lockups)
    ├── RUN_PLANNING_PC.sh                # Starts MoveIt 2 (move_group) + RViz2 + hardware bridge
    ├── START_NANO_BRIDGE.sh              # Deploys and launches nano_micro_bridge.py on Jetson Nano
    ├── RUN_TEACH.sh                      # Interactive CLI Teach Mode (servo release/lock)
    ├── SAVE_POSE.sh                      # Saves current /joint_states to cobot_poses.yaml
    ├── GO_POSE.sh                        # Commands manipulator to a named pose
    └── ws_overlay/                       # Colcon overlay workspace (mycobot_ros2 MoveIt config & nodes)
```

---

## Jetson Nano HTTP Hardware Micro-Bridge (`nano_micro_bridge.py`)

Running directly on the MyCobot's internal **Jetson Nano** (`<JETSON_NANO_IP>:<NANO_BRIDGE_PORT>` / `<JETSON_NANO_IP>:<NANO_BRIDGE_PORT>`), `nano_micro_bridge.py` provides deterministic, zero-DDS-overhead hardware access over HTTP:

### Hardware Connections on the Jetson Nano

- **Serial Bus**: `/dev/ttyTHS1` at `1000000` baud (`MyCobot('/dev/ttyTHS1', 1000000)`).
- **Suction Pump GPIO (`RPi.GPIO` BCM mode)**:
  - `PIN_PUMP_MOTOR = 20` (Active-LOW: `GPIO.LOW` = ON, `GPIO.HIGH` = OFF)
  - `PIN_PUMP_VALVE = 21` (Active-LOW vent valve: `GPIO.LOW` = sealed/suction, `GPIO.HIGH` = release/vent)
  - When turning the pump **OFF**, `nano_micro_bridge.py` sets pin `20` `HIGH`, pulses pin `21` `LOW` for `50 ms` to vent residual vacuum immediately, and sets pin `21` `HIGH`.

### HTTP Endpoints (`:<NANO_BRIDGE_PORT>`)

| Method & Path | Query / Parameters | Response & Behavior |
| :--- | :--- | :--- |
| `GET /status` | — | Returns `{"ok": true, "mock": false, "gpio_ready": true, "pump_active": bool, "servos_released": bool, "panicked": bool}`. |
| `GET /get_angles` | — | Reads physical encoder angles via `mc.get_angles()` (up to 4 retries, filters out `[0,0,0,0,0,0]` serial glitches) and returns `{"angles": [d1..d6]}` in degrees. |
| `GET /move_joints` | `j=d1,d2,d3,d4,d5,d6&speed=1..100` | Clears panic state and calls `mc.send_angles(angles, speed)`. Rejects execution if `mock == True`. |
| `POST /pump/on` | — | Activates vacuum suction (`GPIO 20 LOW`, `GPIO 21 LOW`) and sets `pump_active = True`. |
| `POST /pump/off` | — | Deactivates suction, vents the valve (`50 ms` pulse), and sets `pump_active = False`. |
| `POST /servos/release` | — | Calls `mc.release_all_servos()` so the operator can hand-guide the arm in Teach Mode. |
| `POST /servos/lock` | — | Calls `mc.power_on()` / `mc.focus_all_servos()` to lock all 6 joints at their current angles. |
| `GET /panic` | — | Immediately releases all servos (`mc.release_all_servos()`) and sets `panicked = True`. |

---

## `mycobot_ros2` Container Configuration (`mycobot_docker/docker-compose.yml`)

- **Container Name**: `mycobot_ros2`
- **Image**: `mycobot_galactic:latest` (Ubuntu 20.04 Focal + ROS 2 Galactic + MoveIt 2)
- **Networking & IPC**: `network_mode: host`, `ipc: host`, `privileged: true`, `shm_size: '2gb'`
- **Environment**: `ROS_DOMAIN_ID=42`, `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp`
- **Mounted Volumes**:
  - `./cobot_poses.yaml:/root/cobot_poses.yaml`
  - `./ws_overlay/src:/root/ros2_ws/src/overlay`
  - `/tmp/.X11-unix:/tmp/.X11-unix:rw`

---

## Extension Points Used by Other Modules

The `drawer_picking/` module at the repository root reuses this submodule
without copying it. It needs these small, backward-compatible changes (branch
`feat/drawer-picking`):

| File | Change |
| :--- | :--- |
| `mycobot_280_jn_moveit_config/launch/galactic_demo.launch.py` | Optional argument `rviz_config` (default `config/moveit.rviz`). |
| `mycobot_docker/Dockerfile`, `docker-compose.yml` | Optional build argument `BASE_IMAGE` for ARM64 hosts (`ros:galactic`); installs `ros-galactic-rmw-fastrtps-cpp`, which `ros:galactic` lacks. |
| `mycobot_description/urdf/mycobot_280_jn/mycobot_280_jn.urdf.xacro` | `pump_tcp` (tip of the MoveIt group) moved to the suction cup face: `xyz="0 0.008 0.0962"` in `pump_head`, `+z` out of the cup, coaxial with joint 6 (about 106 mm from `link6`). It was on the side mounting plate with `+z` along `link6` `+y`, so straight-line moves went sideways. |

Existing scripts keep their default behavior. The `pump_tcp` fix changes only
Cartesian targets on that frame; the existing pick-and-place uses joint poses.

!!! note "Not verified"
    The 106 mm cup offset comes from the `pump_head.dae` mesh. It was not
    measured on the real robot. See
[Pick items from the drawer cabinet](../../guides/run-drawer-picking.md).
