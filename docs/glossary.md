# Glossary

Definitions of domain-specific terms, acronyms, and components used across the **B002 Future Lab Bots** codebase and documentation.

---

## A–D

- **AMCL (Adaptive Monte Carlo Localization)**: Probabilistic 2D particle-filter localization node (`nav2_amcl`) that estimates the TurtleBot 4's pose (`map -> odom`) by matching RPLIDAR `/scan` data against `Mapa_Lab.pgm`. Publishes `/amcl_pose` with `TRANSIENT_LOCAL` durability.
- **Anchor (`anchor.yaml`)**: The static 3D coordinate transformation (`map -> mycobot_base_link`) stored in `integration_cobot_tb4/config/anchor.yaml` that places the MyCobot 280 and its table inside the TurtleBot 4's SLAM map.
- **Create 3**: The iRobot mobile base underneath the TurtleBot 4. Runs embedded ROS 2 firmware at `192.168.186.2` (`usb0`) and provides wheel odometry (`/odom`), battery telemetry (`/battery_state`), and infrared autonomous docking (`/dock`, `/undock`).
- **create3_republisher**: Bridge node running on the TurtleBot 4 Raspberry Pi 4 (`192.168.0.21`) that forwards Create 3 topics from the internal `usb0` interface (`192.168.186.0/24`) to the lab Wi-Fi FastDDS Discovery Server (`192.168.0.129:11811`).
- **DDS (Data Distribution Service)**: The middleware layer underneath ROS 2 responsible for peer discovery and message transport (`FastDDS` / `rmw_fastrtps_cpp` on Domain 0; `CycloneDDS` / `rmw_cyclonedds_cpp` on Domain 42).
- **Discovery Server**: Unicast FastDDS coordination server running on `192.168.0.129:11811` (Domain 0) and `:11888` (Domain 42) that replaces unreliable Wi-Fi UDP multicast discovery.

---

## E–M

- **Hand-Guiding (Teach Mode)**: Calibrating manipulator poses by releasing servo holding torque (`POST /servos/release`), physically moving the MyCobot 280 arm by hand to the target posture, locking the servos (`POST /servos/lock`), and saving the resulting radian angles to `cobot_poses.yaml`.
- **Handshake (`Inter-Robot Handshake`)**: The closed-loop coordination protocol between the MyCobot 280 and TurtleBot 4 at `pickup_point` using `/product_class`, `/turtlebot_at_pickup`, and `/item_released_on_tb4`.
- **Host Agent (`host_agent.py`)**: Privileged localhost daemon on `127.0.0.1:18080` that manages host-level processes (Discovery Server, Nav2, RViz) and remote SSH recovery actions.
- **Integrated Real Mode (`integrated_real`)**: Full autonomous execution mode in `cell_routes.py` that verifies MoveIt 2, 3D RViz, wrist camera stream, and 5 consistent live YOLOv8 detections before running the physical 8-stage sorting handshake.
- **MCAP**: Modern modular container format for ROS 2 bag recordings (`*.mcap.zstd`), used by `experiments/record_trial.sh`.
- **Mission Manager (`mission_manager.py`)**: Central ROS 2 Jazzy node in `turtlebot4_jazzy/scripts/` that arbitrates single-mission execution across `DeliveryRoutine`, `FailureRoutine`, and `RestockRoutine`.
- **Mission Signal Agent (`mission_signal_agent.py`)**: Persistent ROS 2 Jazzy `SUPER_CLIENT` daemon on `127.0.0.1:18081` that publishes and verifies handshake signals on `ROS_DOMAIN_ID=0` without subprocess startup lag.
- **MoveIt 2 (`move_group`)**: Motion planning framework running inside the `mycobot_ros2` Docker container (ROS 2 Galactic, Domain 42).

---

## N–Z

- **`nano_micro_bridge.py`**: Lightweight HTTP server (`:8088`) running on the MyCobot's Jetson Nano (`192.168.0.62`) that drives the 6 servos over `/dev/ttyTHS1` (`1000000` baud) and controls the suction pump via BCM GPIO pins `20` and `21`.
- **OAK-D Pro**: Stereo depth and RGB AI camera mounted on the TurtleBot 4 (`luxonis/depthai-ros`).
- **`predock_point`**: Staging waypoint located `~0.50–0.67 m` directly in front of `dock_station`. The TurtleBot 4 always navigates to `predock_point` via Nav2 before invoking the Create 3 infrared `/dock` action.
- **QoS (Quality of Service)**: ROS 2 delivery policies (`RELIABLE` vs. `BEST_EFFORT`, `VOLATILE` vs. `TRANSIENT_LOCAL`). Mismatched QoS between publisher and subscriber silently prevents message delivery.
- **`ROS_SUPER_CLIENT`**: FastDDS client mode (`ROS_SUPER_CLIENT=True`) that requests the complete endpoint graph from the Discovery Server (`192.168.0.129:11811`), required by CLI tools, RViz, `ros2 bag`, and the Control Center backend.
- **TTL (Time-To-Live / Freshness Window)**: Maximum age allowed for a cached sensor or classification sample (e.g., `3.0 s` for `/dock_status`, `/odom`, `/scan`; `5.0 s` for `/product_class`) before the safety gates reject it as stale.
