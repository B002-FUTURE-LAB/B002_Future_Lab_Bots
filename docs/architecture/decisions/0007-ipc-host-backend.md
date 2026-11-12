# ADR-0007: Host-Native FastAPI Backend Instead of Containerized Backend

- **Status**: Accepted
- **Date**: 2026-08
- **Related**: [ADR-0001](0001-uvicorn-no-reload.md), [ADR-0002](0002-singleton-ros-nodes.md), [ADR-0008](0008-host-agent-outside-docker.md)

---

## Context

Early iterations of the `future_lab_control_center` ran the FastAPI backend inside a Docker container (`future_lab_backend` in `docker-compose.yml`) using `network_mode: host`. However, the backend needed to:

1. Subscribe directly to ROS 2 Jazzy topics (`/odom`, `/scan`, `/amcl_pose`, `/dock_status`, `/battery_state`, `/oakd/rgb/preview/image_raw`) via FastDDS Discovery Server (`<TURTLEBOT_IP>:<TB4_DISCOVERY_PORT>`).
2. Spawn and manage local X11 GUI processes (`rviz2`, MoveIt 2 `RUN_PLANNING_PC.sh`, `start_3d_monitoring.sh`) on the Host PC's display (`:0` / `:1003`).
3. Execute `docker exec mycobot_ros2 ...` commands to control the ROS 2 Galactic container and launch YOLOv8 processes using the host's Python virtual environment and GPU.

When FastDDS ran with `--ipc: host` or mismatched container UIDs/PIDs across container boundaries, shared-memory transport (`SHM`) locks in `/dev/shm/fastrtps_*` frequently wedged or failed to deliver large messages (`/map`, `/oakd/*`) between host nodes and containerized nodes.

## Decision

Run the **FastAPI Backend (`uvicorn backend.main:app`)** and **Next.js Frontend (`npm run dev`)** natively on the **Host Control PC** (`START_CONTROL_CENTER.sh`) under the `future-lab` user account with the host's native ROS 2 Jazzy installation (`/opt/ros/jazzy/setup.bash`), while keeping **ROS 2 Galactic (`mycobot_ros2`)** isolated inside its Ubuntu 20.04 Docker container on `ROS_DOMAIN_ID=42`.

## Consequences

- **Positive**:
  - `TurtleBotNode` shares the exact same OS kernel, UID, `/dev/shm`, and FastDDS version (`v2.14`) as the host Discovery Server (`<TURTLEBOT_IP>:<TB4_DISCOVERY_PORT>`) and Nav2 stack.
  - Direct access to `docker exec mycobot_ros2`, host SSH keys, X11 `DISPLAY`, and local filesystem paths without complex socket mounts.
- **Negative / Trade-offs**:
  - The Host PC must have Python dependencies (`fastapi`, `uvicorn`, `ultralytics`, `opencv-python`) installed in the host environment.
