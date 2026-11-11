# Repository map

`B002_Future_Lab_Bots` is an **aggregator repository**. It holds the control
center and the documentation, and it records which versions of three other
repositories belong together. Those three are **Git submodules**.

```text
B002_Future_Lab_Bots/
├── future_lab_control_center/   # backend, frontend, host agent, scripts, tests
├── turtlebot4_jazzy/            # submodule: TurtleBot 4, Nav2, mission routines
├── cobot/                       # submodule: MyCobot 280, Docker, MoveIt, Nano bridge
├── integration_cobot_tb4/       # submodule: 3D visualization and joint bridge
├── experiments/                 # scripts for the trial campaign
├── docs/                        # this documentation
├── tools/docs/                  # checks that run on the docs in CI
└── mkdocs.yml                   # documentation site configuration
```

## Control center

| Path | Contents |
|---|---|
| `backend/main.py` | The FastAPI app, middleware that audits mutating requests, ROS environment. |
| `backend/api/` | The five routers. See [REST API](rest-api.md). |
| `backend/ros2_nodes/` | `turtlebot_node.py` and `cobot_node.py`. See [ROS interfaces](ros-interfaces.md). |
| `backend/mission_readiness.py`, `mission_signal_evidence.py` | Mission readiness checks and evidence used by the simulated signals. |
| `backend/experiment_audit.py` | Structured event logging for experiments. |
| `frontend/` | The Next.js dashboard. Components include `TurtleBotDashboardTab`, `CellControlPanel`, `CameraVisionPanel`, `TeachModePanel`, and the panic, interrupt and reboot overlays. |
| `host_agent/` | The [host agent](host-agent.md), its helpers and the systemd units. |
| `tests/` | Unit tests for the backend and host agent. |
| `START_LAB.sh` | One-click startup. See [Start and stop the lab](../guides/start-and-stop-the-lab.md). |

## Submodules

| Submodule | Repository | Branch |
|---|---|---|
| `turtlebot4_jazzy` | `MHC-CodeSmith/Bot_HOF` | `main` |
| `cobot` | `MHC-CodeSmith/Cobot` | `master` in `.gitmodules`; `featnew-yolo` is the branch in use |
| `integration_cobot_tb4` | `MHC-CodeSmith/integration_cobot_tb4` | `main` |

!!! warning "Submodules"
    After cloning, run `git submodule update --init`. The documentation build
    does **not** need the submodules.

!!! note "Not yet documented"
    The internals of the three submodules (their launch files, nodes and
    configuration) are not documented here yet. Add a page per submodule.

## Tests

The tests in `future_lab_control_center/tests/` cover mission safety,
navigation cancellation, process management, the host agent helpers, the
node singletons and the experiment audit.
