# ADR-0008: Privileged Host Agent (`:18080`) & Mission Signal Agent (`:18081`) as Local Micro-Daemons

- **Status**: Accepted
- **Date**: 2026-08
- **Related**: [ADR-0002](0002-singleton-ros-nodes.md), [ADR-0004](0004-trigger-helper-measured-reply.md), [ADR-0007](0007-ipc-host-backend.md)

---

## Context

The Control Center needs to perform two classes of host-level operations that should be decoupled from the FastAPI web server's request threads and in-process `rclpy` executor:

1. **System & Remote Recovery Actions**: Restarting the FastDDS Discovery Server (`fastdds discovery -i 0`), SSH-ing into the TurtleBot 4 (`192.168.0.21`) or Jetson Nano (`192.168.0.62`) to restart `create3_republisher` or `nano_micro_bridge.py`, and launching detached X11 GUI pipelines (`START_NAV_DISCOVERY.sh`, `RUN_PLANNING_PC.sh`).
2. **Deterministic ROS 2 Mission Signaling**: Publishing `/product_class` and `/item_released_on_tb4`, calling `/start_delivery` / `/stop_mission`, and waiting for `/turtlebot_at_pickup` on `ROS_DOMAIN_ID=0` without suffering from transient discovery delays when spawning short-lived `ros2 topic pub` subprocesses.

Spawning ephemeral `ros2 service call` or `ros2 topic pub` CLI processes via `subprocess.run()` took `2–4 seconds` per invocation to associate with the FastDDS Discovery Server and occasionally missed single-shot messages before subscriber matching completed.

## Decision

Split these responsibilities into two lightweight, loopback-only (`127.0.0.1`) Python daemons started automatically by `START_CONTROL_CENTER.sh`:

1. **Host Agent (`host_agent.py` on `127.0.0.1:18080`)**: Authenticated via `X-Agent-Token` (`HOST_AGENT_TOKEN`), responsible for Discovery Server lifecycle, RViz/MoveIt process supervision, and remote SSH recovery actions.
2. **Mission Signal Agent (`mission_signal_agent.py` on `127.0.0.1:18081`)**: A persistent ROS 2 Jazzy `SUPER_CLIENT` node (`mission_signal_agent`) that maintains pre-matched publishers (`/product_class`, `/item_released_on_tb4`), subscribers (`/turtlebot_at_pickup`, `/dock_status`), and service clients (`/start_delivery`, `/stop_mission`), verifying `get_subscription_count() >= 1` before publishing critical mission signals.

## Consequences

- **Positive**:
  - Sub-100 ms latency and verified subscriber matching for `/product_class` and `/item_released_on_tb4` handoffs.
  - Clean separation between web API routing and privileged process/SSH management.
- **Negative / Trade-offs**:
  - Adds two localhost ports (`:18080` and `:18081`) that must be monitored by `/api/v1/health/full` and `STOP_CONTROL_CENTER.sh`.
