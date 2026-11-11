# Safety model

The control center is built on one rule: **report only what was measured.**
A button that says "done" must mean the system observed it, not that a command
was sent.

## Principles

### 1. Success needs a reply

| Action | When it counts as success |
|---|---|
| Cancel a Nav2 goal | The `CancelGoal` server answered. Otherwise the result is `partial`. |
| Launch Nav2 or localization | The managed nodes are active. |
| Stop a process | Its absence is confirmed. |
| Set the initial pose | Fresh AMCL evidence arrived. |
| Undock | The maneuver result confirms it. |
| Trigger a mission service | The ROS service replied. A timeout is an error. |
| Wake the OAK-D camera | Frames were received. |

### 2. Stopping is cancelling, not zero velocity

Sending zero velocity does not stop a robot that Nav2 is driving, because the
controller rewrites `/cmd_vel` on its next cycle. The real brake is cancelling
the goal. The zero-velocity burst is only a secondary measure.
See [Emergency stop](../guides/emergency-stop.md).

### 3. State comes from telemetry and cannot be forced

The docked state comes from Create 3 telemetry. The route that used to force
it (`POST /api/v1/turtlebot/set_dock_status`) is deprecated, because forcing a
state hides real faults.

### 4. Refuse when evidence is missing

The Mission Manager refuses to undock when `/dock_status` is absent or stale,
and a mission stops when `/undock` is unavailable, instead of continuing on a
guess. See [Mission handshake](mission-handshake.md).

### 5. Do not repeat an ambiguous request

If a mission trigger times out, the request may already have been delivered.
The host agent therefore reports the state as indeterminate and does not retry
on its own. See [decision 0004](decisions/0004-trigger-helper-measured-reply.md).

### 6. Hardware first

Software stops are a second line of defense. The physical button on the Create
3, and power to the arm, are the first. See [Emergency stop](../guides/emergency-stop.md).
