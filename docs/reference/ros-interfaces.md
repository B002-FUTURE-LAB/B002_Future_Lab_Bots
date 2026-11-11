# ROS interfaces

Interfaces used by the backend nodes, taken from
`backend/ros2_nodes/turtlebot_node.py` and `backend/ros2_nodes/cobot_node.py`.
Both nodes run inside the backend process.

!!! note "Quality of service"
    QoS profiles are defined in code (`QOS_LATCHED`, `QOS_AMCL`,
    `QOS_ROBOT_STREAM`, and others at the top of `turtlebot_node.py`). They are
    not repeated here, because a mismatch with the remote side silently drops
    messages. When something is published but not received, compare the QoS in
    the source with `ros2 topic info -v <topic>`.

## TurtleBot node — `future_lab_turtlebot_node`

### Subscriptions

| Topic | Type | Used for |
|---|---|---|
| `/battery_state` | `sensor_msgs/BatteryState` | Battery percentage and current. Also refreshes the telemetry timestamp. |
| `/odom` | `nav_msgs/Odometry` | Robot pose. Also refreshes the telemetry timestamp. |
| `/dock_status` | `irobot_create_msgs/DockStatus` | Docked state (debounced). Subscribed only if the message type is available. |
| `/amcl_pose` | `geometry_msgs/PoseWithCovarianceStamped` | Localization pose and covariance. |
| `/scan` | `sensor_msgs/LaserScan` | LiDAR data. |
| `/oakd/rgb/preview/image_raw/compressed` | `sensor_msgs/CompressedImage` | Camera stream (compressed). |
| `/oakd/rgb/preview/image_raw` | `sensor_msgs/Image` | Camera stream (raw fallback). |
| `/navigate_to_pose/_action/status` | `action_msgs/GoalStatusArray` | Nav2 goal status. |

### Publications

| Topic | Type | Used for |
|---|---|---|
| `/cmd_vel_unstamped` | `geometry_msgs/Twist` | Manual velocity commands. |
| `/cmd_vel` | `geometry_msgs/TwistStamped` | Manual velocity commands (stamped). |
| `/initialpose` | `geometry_msgs/PoseWithCovarianceStamped` | AMCL initial pose. |

### Clients

| Name | Type | Kind | Used for |
|---|---|---|---|
| `/navigate_to_pose` | `nav2_msgs/NavigateToPose` | action | Sending navigation goals. |
| `/navigate_to_pose/_action/cancel_goal` | `action_msgs/CancelGoal` | service | Cancelling Nav2 goals. See [decision 0003](../architecture/decisions/0003-cancel-goal-service.md). |
| `/start_delivery` | `std_srvs/Trigger` | service | Start a delivery mission. |
| `/start_failure` | `std_srvs/Trigger` | service | Start a defective-part mission. |
| `/start_restock` | `std_srvs/Trigger` | service | Start a restock mission. |
| `/stop_mission` | `std_srvs/Trigger` | service | Stop the Mission Manager's mission. |

The four mission services are provided by the Mission Manager in the
`turtlebot4_jazzy` repository.

## Cobot node — `future_lab_cobot_node`

### Subscriptions

| Topic | Type | Used for |
|---|---|---|
| `/joint_states` | `sensor_msgs/JointState` | Current joint angles. |
| `/joint_states_raw` | `sensor_msgs/JointState` | Raw joint angles. |
| `/product_class` | `std_msgs/String` | Class detected by YOLO. |
| `/turtlebot_at_pickup` | `std_msgs/Bool` | The TurtleBot reached the pickup point. |
| `/turtlebot_battery_emergency` | `std_msgs/Bool` | The TurtleBot's battery is critical (5 % or less). |

### Publications

| Topic | Type | Used for |
|---|---|---|
| `/joint_states_commands` | `sensor_msgs/JointState` | Direct joint commands to the arm. |
| `/product_class` | `std_msgs/String` | Announce the identified can class. |
| `/item_released_on_tb4` | `std_msgs/Bool` | The can was released onto the TurtleBot's tray. |
| `/future_lab/events` | `std_msgs/String` | Structured experiment events (JSON). Reliable, transient-local, depth 50. |

### Clients

| Name | Type | Kind |
|---|---|---|
| `/move_action` | `moveit_msgs/MoveGroup` | action |
| `/mycobot_arm_controller/follow_joint_trajectory` | `control_msgs/FollowJointTrajectory` | action |
| `/pump_on`, `/pump_off` | `std_srvs/Trigger` | service |
| `/release_servos`, `/lock_servos` | `std_srvs/Trigger` | service |

If the ROS service is not ready, the node falls back to an HTTP micro-bridge on
the Jetson Nano (port `8088`), and then to SSH. See
[Ports and addresses](ports-and-addresses.md).

## Environment set by the backend

`backend/main.py` and `docker-compose.yml` set `ROS_DOMAIN_ID=0`,
`RMW_IMPLEMENTATION=rmw_fastrtps_cpp`, `ROS_SUPER_CLIENT=True` and
`ROS_DISCOVERY_SERVER=192.168.0.129:11811;`.
