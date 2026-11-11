# Mission handshake

The cobot and the TurtleBot coordinate a can transfer with a small set of ROS
topics and services.

## Signals

| Signal | Type | Direction | Meaning |
|---|---|---|---|
| `/product_class` | `std_msgs/String` | cobot node publishes and subscribes | The class of the identified can. |
| `/turtlebot_at_pickup` | `std_msgs/Bool` | TurtleBot to cobot | The TurtleBot reached the pickup point. |
| `/item_released_on_tb4` | `std_msgs/Bool` | cobot to TurtleBot | The can was released and the pump is off. |
| `/turtlebot_battery_emergency` | `std_msgs/Bool` | TurtleBot to cobot | The TurtleBot's battery is critical (5 % or less). |
| `/start_delivery` | `std_srvs/Trigger` | backend to Mission Manager | Start a delivery. |
| `/start_failure` | `std_srvs/Trigger` | backend to Mission Manager | Start a defective-part mission. |
| `/start_restock` | `std_srvs/Trigger` | backend to Mission Manager | Start a restock mission. |
| `/stop_mission` | `std_srvs/Trigger` | backend to Mission Manager | Stop the active mission. |

## Class to destination

The delivery routine maps a class to a destination only for **explicitly
recognized** classes:

| Destination | Accepted classes |
|---|---|
| `delivery_red` | `red`, `vermelho`, `vermelha`, `tin_valid_red`, `tin_valid_red_square` |
| `delivery_blue` | `blue`, `azul`, `tin_valid_blue`, `tin_valid_blue_square` |

An unknown or invalid class **never defaults to red**: the routine does not
choose a destination at all.

## Rules the Mission Manager enforces

- **Undock needs fresh dock data.** If `/dock_status` is missing or stale, the
  undock is refused instead of assumed.
- **No continuing without an undock.** If `/undock` is unavailable, rejected or
  fails, the mission stops. It no longer carries on "directly to navigation".
- **Wait after undocking.** Navigation does not start until a stabilization
  period has passed and fresh scan and odometry data have arrived.
- **A failed mission while undocked sends the robot back to the dock** (battery
  safeguard), then reports failure.
- **A mission completes once.** The completion callback is idempotent.

## Completion evidence

A delivery is complete only when all of the following were observed **after
the start time**: the target was reached, docking finished, and the Mission
Manager is free. If the Manager reports an explicit failure, the wait stops
with a failure. This is implemented by `POST /wait_delivery_complete` on the
[mission signal agent](../reference/host-agent.md).

!!! warning "Not yet documented"
    The full step-by-step sequence of the mission routines (pickup, delivery,
    return) lives in `turtlebot4_jazzy/scripts/` and was not read for this
    version. Add the state machine for `delivery_routine.py`,
    `failure_routine.py` and `restock_routine.py`, and the way the two ROS
    domains exchange these topics.
