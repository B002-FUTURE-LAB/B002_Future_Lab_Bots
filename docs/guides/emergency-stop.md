# Emergency stop

!!! danger "If a robot is moving and about to cause harm"
    Use the **physical button on the Create 3** (TurtleBot) or cut power to the
    arm. The software stops below are a second line of defense, not the first.

There are three software stops. Pick the one that matches the situation.

| Situation | Stop | Route |
|---|---|---|
| Cobot cycle must end safely | Soft emergency stop | `POST /api/v1/cell/stop` |
| Everything must halt | Panic | `POST /api/v1/cell/panic` |
| TurtleBot is on a mission | Stop mission | `POST /api/v1/turtlebot/stop_mission` |

## Soft emergency stop (cell)

Turns the pump off, cancels automatic mode, disables YOLO vision and returns
the arm to HOME.

## Panic (cell)

Stops everything: pump, camera, YOLO, robot, motors and MoveIt planning, and
locks the arm servos. To recover, call `POST /api/v1/cell/reset_panic`, which
starts a clean MoveIt, camera and Nano hardware bridge.

## Stop mission (TurtleBot)

`POST /api/v1/turtlebot/stop_mission` does, in this order:

1. **Cancels every Nav2 goal** through the `CancelGoal` service of
   `/navigate_to_pose`. This is the real brake.
2. Kills the simulation subprocesses.
3. Clears the simulation state.
4. Calls the Mission Manager's `/stop_mission` service.
5. Sends a burst of zero velocity at 20 Hz for 2 s.

!!! warning "A zero-velocity burst is not the brake"
    While Nav2 is active, its controller overwrites `/cmd_vel` on the next
    cycle. Only the goal cancellation in step 1 actually stops the robot.

### Reading the answer

The response has `status` set to `success` or `partial`.

| `status` | Meaning | What to do |
|---|---|---|
| `success` | The Nav2 server answered the cancellation. | Done. |
| `partial` | The cancellation was **not confirmed**. | If the robot is still moving, use the physical button on the Create 3. |

The dashboard shows a `partial` result in red. The system never reports
success unless the server replied.

See [Safety model](../architecture/safety-model.md) for the reasoning, and
[decision 0003](../architecture/decisions/0003-cancel-goal-service.md).
