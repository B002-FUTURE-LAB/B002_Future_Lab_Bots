# Recover TurtleBot telemetry

**Symptom:** the dashboard shows `telemetry_ok: false`, battery `null`, and the
robot cannot undock, while the OAK-D camera may still stream.

## Why this happens

Battery, odometry and dock state do not come straight from the Create 3 base.
They travel through a chain:

```text
Create 3 base  ->  create3_republisher (Raspberry Pi)  ->  DDS  ->  backend
```

The backend creates its subscriptions **once**, at startup. So if a link
upstream is down, **restarting the backend does nothing**. Find the broken
link first.

## Diagnose, from the Raspberry Pi side

Run these over SSH on the Raspberry Pi (`<TB4_USER>@<TURTLEBOT_IP>`) with the
TurtleBot environment loaded (`source /etc/turtlebot4/setup.bash`).

| Check | Command | Healthy result |
|---|---|---|
| Base answers | `ping -c 2 <CREATE3_BASE_IP>` | replies in under 1 ms |
| Topics are published | `ros2 topic hz /battery_state` | a rate, not "does not appear to be published yet" |
| Base nodes registered | `ros2 node list` | includes `/create3_repub` and the `/_do_not_use/...` nodes |
| Base web app alive | `curl -s http://<CREATE3_BASE_IP>/` | a normal page, **not** "Oops, something went wrong" |

!!! warning "Ping is not proof"
    In one incident the base answered ping in 0.4 ms and its web server
    answered, but its internal application had crashed. The page said
    **"Oops, something went wrong"** and no topic was published. Ping only
    proves the network, not the application.

If `ros2 node list` returns nothing, stop the stale CLI daemon and retry:
`ros2 daemon stop; ros2 daemon start`. An empty list right after a restart can
be a stale daemon cache, not an empty graph.

## Fix

Work from the cheapest step to the most disruptive, and re-check after each.

1. **Restart the bringup** if the republisher is missing:
   `sudo systemctl restart turtlebot4.service` on the Raspberry Pi. Give it
   about a minute.
2. **Restart the Create 3 application** if its web page shows the error. See
   [Restart the Create 3 application](restart-the-create3-app.md).
3. **Restart the backend** only after the topics are flowing again:
   `docker compose restart backend` in `future_lab_control_center/`.

## Verify

```bash
curl -s http://localhost:<BACKEND_PORT>/api/v1/turtlebot/status
```

Expect `telemetry_ok: true` and `telemetry_age_s` close to `0`.

!!! danger "Never power the base off remotely"
    Do not call `ros2 service call /robot_power ...` to restart the base. It
    turns the sub-base **off**. See `INSTALL.md` in the control center.
