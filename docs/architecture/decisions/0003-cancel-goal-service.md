# 0003 Cancel goals through the CancelGoal service

**Status:** accepted
**Date:** 2026-08-14

## Context

The emergency stop first sent zero velocity and reported success. With Nav2
active that does not stop the robot, because the controller rewrites
`/cmd_vel` on its next cycle. At runtime the installed `rclpy` also had no
`cancel_all_goals_async` on its action client, so a cancel based on that call
could not work, and the failure was silent.

## Decision

Cancel Nav2 goals by calling the `action_msgs/CancelGoal` **service**
`/navigate_to_pose/_action/cancel_goal` (phases 21a and 23a). Report success
only when the server replies. Otherwise the stop returns `partial`, and the
dashboard shows it in red.

## Consequences

- The stop works independently of the `rclpy` version.
- A stop can honestly report that it is unconfirmed.
- The zero-velocity burst is kept only as a secondary measure and is documented
  as not being the brake.

See [Emergency stop](../../guides/emergency-stop.md).
