# Host agent

The **host agent** is a small HTTP service that runs on the host PC, outside
Docker. The backend runs in a container but must start ROS 2 Jazzy processes
(Nav2, localization, RViz) and restart services on the host, so it asks the
agent to do it.

- **Address:** `http://127.0.0.1:8100` (loopback only).
- **Source:** `future_lab_control_center/host_agent/agent.py`.
- **Service:** the user unit `future-lab-agent`.

## Authentication

Every route except `GET /health` requires the header `X-Agent-Token`. The
token is read from the file `future_lab_control_center/.agent_token`. Keep that
file private. It is not tracked by Git.

## Routes

| Route | Purpose |
|---|---|
| `GET /health` | Liveness probe. No token needed. |
| `GET /status` | State of every managed process. |
| `GET /logs/<target>` | Log of a managed process. |
| `GET /system/inventory` | The 10-item health inventory of the whole stack. |
| `POST /ros/set_initial_pose` | Publish the AMCL initial pose from the host. |
| `POST /ros/wait_map_tf` | Wait for the map transform. |
| `POST /ros/trigger_mission` | Call one allowed mission service: `start_delivery`, `start_failure`, `start_restock` or `stop_mission`. Anything else is rejected. |
| `POST /launch/<target>` | Start a managed process. |
| `POST /stop/<target>` | Stop a managed process and confirm it is gone. |
| `POST /system/restart_backend` | Restart the backend container. |
| `POST /system/restart_cobot_discovery` | Restart the cobot Discovery Server. |
| `POST /robot/restart_bringup` | Restart `turtlebot4.service` on the Raspberry Pi over SSH. |
| `POST /robot/start_oakd` | Wake the OAK-D camera over SSH. |

Managed `<target>` values come from `LAUNCH_SPECS` in `agent.py`:
`localization`, `nav2`, `viz` and `mission_manager`.

### Behavior worth knowing

- A launch reports success only after the process is confirmed, and a second
  launch of a running target is refused with HTTP 409 (`ProcessConflict`).
- A stop confirms the processes are gone, or fails with HTTP 500 (`StopFailed`).
- `/ros/trigger_mission` is serialized with a lock and **requires a real reply
  from the ROS service**. A timeout is reported as an error and must not be
  retried automatically, because the request may already have been delivered.
  See [decision 0004](../architecture/decisions/0004-trigger-helper-measured-reply.md).

### Command line

```bash
python3 host_agent/agent.py --cleanup
```

Stops every managed process, including old generations started manually, and
exits non-zero if it cannot confirm that none remain. `START_LAB.sh --reset`
uses it.

## Mission signal agent

A second loopback service, `mission_signal_agent.py`, listens on
`http://127.0.0.1:8101` with the same token. It backs the dashboard's simulated
cobot signals.

| Route | Purpose |
|---|---|
| `POST /publish` | Publish a simulated signal and confirm it was seen. |
| `POST /start_delivery` | Publish a fresh class and start a delivery as one action. |
| `POST /wait_pickup` | Wait for `/turtlebot_at_pickup`. A timeout is not reported as arrival. |
| `POST /wait_delivery_complete` | Wait for the target, docking and a free Mission Manager, all after the start time. |

Its user unit is `future-lab-mission-signal`.

## Systemd units

| Unit | Purpose |
|---|---|
| `future-lab-agent` | The host agent. `KillMode=control-group`, so its children stop with it. |
| `future-lab-cobot-discovery` | Fast DDS Discovery Server on port 11888. |
| `future-lab-mission-signal` | The mission signal agent. |
