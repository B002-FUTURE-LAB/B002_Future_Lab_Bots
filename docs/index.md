# B002 Future Lab Bots

Documentation for the **B002 Future Lab** robotic cell: a **TurtleBot 4**
mobile robot and a **MyCobot 280** arm that cooperate to move cans, controlled
from a web dashboard.

## What the system does

- The **cobot** picks a can, identifies it with a YOLO vision model and signals
  the TurtleBot.
- The **TurtleBot 4** navigates with Nav2 to the pickup point, receives the can,
  delivers it to the correct destination and returns to its dock.
- A **control center** (FastAPI backend, Next.js dashboard and a host agent)
  starts the processes, shows telemetry and provides the safety stops.

## Where to start

| If you want to... | Read |
|---|---|
| Understand the hardware and the network | [Hardware and network](getting-started/hardware-and-network.md) |
| Install and run the control center | [Install and first run](getting-started/install-and-first-run.md) |
| Operate the lab day to day | [Start and stop the lab](guides/start-and-stop-the-lab.md) |
| Stop a robot right now | [Emergency stop](guides/emergency-stop.md) |
| Something is not working | [Troubleshooting](troubleshooting.md) |
| Look up a route, topic or port | [Reference](reference/rest-api.md) |
| Understand why it is built this way | [Architecture](architecture/system-overview.md) |
| Change these docs | [How to edit these docs](contributing/how-to-edit-these-docs.md) |

## How this documentation is organized

The site follows the [Diataxis](https://diataxis.fr/) idea: each page is exactly
one of four kinds, so you always know what to expect.

| Kind | Purpose | Section |
|---|---|---|
| Tutorial | Learn by following steps | Getting started |
| How-to guide | Solve one concrete task | Guides |
| Reference | Look up exact facts | Reference |
| Explanation | Understand the why | Architecture |

!!! info "Status of this documentation"
    This is a first version. Pages state when something was **not verified** on
    the real hardware. Treat those notes as open tasks, and remove them when
    you verify the behavior.
