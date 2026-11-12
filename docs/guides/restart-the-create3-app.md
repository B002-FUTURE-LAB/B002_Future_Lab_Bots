# Restart the Create 3 application

Use this when the Create 3 answers ping but publishes no topics, and its web
page shows **"Oops, something went wrong"**. See
[Recover TurtleBot telemetry](recover-turtlebot-telemetry.md) for how to reach
that conclusion.

## Open the base's web interface

The base serves a web interface at `http://<CREATE3_BASE_IP>`. It is reachable from
the Raspberry Pi (use `curl` over SSH), and from other machines only if you
route to that subnet. The menu has **Application > Restart application** and
**Application > Reboot robot**.

## Two options

| Option | Endpoint | Effect | Time |
|---|---|---|---|
| Restart the application | `POST /api/restart-app` | Restarts only the Create 3 robot application | up to about a minute |
| Reboot the robot | `POST /api/reboot` | Reboots the whole base | several minutes |

Both are taken from the base's own web page. From the Raspberry Pi:

```bash
curl -s -X POST --connect-timeout 5 http://<CREATE3_BASE_IP>/api/restart-app
curl -s -X POST --connect-timeout 5 http://<CREATE3_BASE_IP>/api/reboot
```

!!! note "What was verified"
    In the recorded incident the **reboot** was the call that was executed. It
    answered `{"status":"Reboot in progress."}`, and telemetry came back after
    the bringup was restarted. The lighter **restart-app** endpoint exists on the
    page but has **not been tested in this lab**. Try it first next time, and
    update this page with the result.

    A wrong endpoint name (for example `/api/restart-application`) returns the
    same "Oops" HTML page, which looks like a failure. Always read the response.

## After the base is back

1. Wait until the web page shows its normal menu instead of "Rebooting Robot".
2. Restart the bringup: `sudo systemctl restart turtlebot4.service` on the
   Raspberry Pi.
3. Wait about a minute, then restart the backend:
   `docker compose restart backend`.
4. Verify with `GET /api/v1/turtlebot/status`: `telemetry_ok` must be `true`.
