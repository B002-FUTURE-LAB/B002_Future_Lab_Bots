# Submodule Reference: `turtlebot4_jazzy` (`Bot_HOF`)

- **Repository URL**: `git@github.com:B002-FUTURE-LAB/Bot_HOF.git`
- **Mount Path**: `turtlebot4_jazzy/`
- **ROS Distribution**: ROS 2 **Jazzy Jalisco** (`Ubuntu 24.04 LTS`)
- **DDS Configuration**: `ROS_DOMAIN_ID=0`, `RMW_IMPLEMENTATION=rmw_fastrtps_cpp`, Unicast Discovery Server (`192.168.0.129:11811`)

---

## Directory Layout

```text
turtlebot4_jazzy/
├── config/
│   ├── lab.yaml                          # Procedural laboratory geometry definition
│   └── super_client_configuration.xml    # FastDDS XML profile for SUPER_CLIENT connection to :11811
├── maps/
│   ├── Mapa_Lab.pgm                      # 2D occupancy grid raster map of Lab B002
│   └── Mapa_Lab.yaml                     # Map metadata (resolution, origin, thresholds)
├── params/
│   ├── nav2.yaml                         # Custom Nav2 parameters (MPPI/DWB controller, costmaps, AMCL)
│   └── waypoints.yaml                    # Mission waypoints and timeout/freshness parameters
├── scripts/
│   ├── mission_manager.py                # Central mission orchestrator node
│   ├── mission_base.py                   # Shared base class (undock, dock, Nav2 client, TF/sensor gates)
│   ├── delivery_routine.py               # Sorting delivery state machine (red / blue cans)
│   ├── failure_routine.py                # Defective item quarantine state machine
│   ├── restock_routine.py                # Inventory restock state machine
│   ├── cancel_navigation_goals.py        # Cancels active Nav2 NavigateToPose goals
│   ├── wait_for_map_tf.py                # Auto-publishes /initialpose from dock_station when docked
│   ├── navigate_once.py                  # Single-waypoint CLI navigation helper
│   ├── patrol.py                         # Standalone multi-waypoint patrol loop script
│   ├── vision_lid_classifier.py          # OAK-D / OpenCV lid color classifier
│   └── vision_lid_classifier_simple.py   # Lightweight HSV color classifier
├── sim/
│   ├── Dockerfile                        # ROS 2 Jazzy + Gazebo Harmonic simulation image
│   ├── run_lab_world.sh                  # Launches Gazebo simulation with GPU auto-detection
│   ├── run_docker.sh                     # Interactive container shell launcher
│   └── worlds/my_lab.sdf                 # Generated SDF world matching Lab B002
├── start_discovery_server.sh             # Starts FastDDS Discovery Server (ID 0 on :11811)
├── START_NAV_DISCOVERY.sh                # Launches Localization + Nav2 + wait_for_map_tf.py
├── START_SLAM_DISCOVERY.sh               # Launches SLAM Toolbox with Discovery Server
├── START_RVIZ_DISCOVERY.sh               # Launches RViz2 with Discovery Server
└── START_MISSION_DISCOVERY.sh            # Launches mission_manager.py with waypoints.yaml
```

---

## Waypoint Coordinates (`params/waypoints.yaml`)

All coordinates are defined in the `map` frame (`Mapa_Lab.yaml`):

| Waypoint Key | `x (m)` | `y (m)` | `yaw (rad)` | Role |
| :--- | :---: | :---: | :---: | :--- |
| `dock_station` | `0.0677` | `-0.0044` | `3.1333` | Physical charging station pose (`is_docked == True`). |
| `predock_point` | `-0.6080` | `-0.0220` | `-0.0080` | Staging pose `~0.67 m` in front of the dock used before `/dock`. |
| `pickup_point` | `-0.0252` | `0.8962` | `3.1394` | Loading position in front of the MyCobot 280 table. |
| `delivery_red` | `-2.3571` | `0.7931` | `-2.8634` | Drop-off destination for valid red cans (`tin_valid_red*`). |
| `delivery_blue` | `-2.2381` | `1.8891` | `2.6584` | Drop-off destination for valid blue cans (`tin_valid_blue*`). |
| `failure_pickup` | `-0.4530` | `0.8707` | `-1.6199` | Secondary pickup pose for defective items (`FailureRoutine`). |
| `failure_zone` | `-1.1678` | `2.0942` | `3.0933` | Quarantine zone for defective items (`FailureRoutine`). |
| `inventory_point` | `-1.7874` | `-0.0493` | `-3.1120` | Inventory collection point (`RestockRoutine`). |
| `supply_point` | `-0.5731` | `1.9974` | `0.0249` | Supply replenishment point (`RestockRoutine`). |

---

## Nav2 & Localization Customizations (`params/nav2.yaml`)

To ensure reliable navigation inside the compact B002 laboratory corridors:

- **Explicit `robot_model_type` for ROS 2 Jazzy**: In ROS 2 Jazzy, `nav2_amcl` requires the fully qualified plugin class name `nav2_amcl::DifferentialMotionModel` (earlier Humble configs used `differential`, which causes `amcl` to crash on startup in Jazzy).
- **Obstacle Inflation & Footprint**: Tuned for the TurtleBot 4's `0.318 m` diameter chassis so it can approach `pickup_point` within `0.30 m` of the MyCobot table without false lethal-costmap lockups.
- **Pre-Navigation Sensor Gate (`MissionBase`)**: Even after Nav2 lifecycle nodes activate, `MissionBase._wait_for_navigation_inputs` verifies 5 consecutive samples of fresh `/odom`, `/scan`, and `map -> odom -> base_link` transforms before dispatching `NavigateToPose`.
