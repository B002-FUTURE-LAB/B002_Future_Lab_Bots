# Start and stop the lab

## Start

```bash
cd ~/B002_Future_Lab_Bots/future_lab_control_center
./START_LAB.sh            # normal start
./START_LAB.sh --check    # verify the environment only, change nothing
./START_LAB.sh --reset    # clean restart (read the warning below)
```

`START_LAB.sh` writes a log to `/tmp/start_lab_<date>.log`. In order, it:

1. Checks the user and the repository.
2. Checks that the Docker daemon is running.
3. Checks the `.env` file (creates it from `.env.example` if missing, except in `--check`).
4. Starts the cobot Discovery Server (port `<COBOT_DISCOVERY_PORT>`).
5. Starts the Docker containers and cleans up host processes.
6. Starts the host agent (port `<HOST_AGENT_PORT>`).
7. Waits for the backend (port `<BACKEND_PORT>`).
8. Waits for the frontend (port `<FRONTEND_PORT>`).
9. Checks the TurtleBot 4 (Raspberry Pi).
10. Checks the Jetson Nano.
11. Checks robot telemetry.
12. Opens the browser.

!!! danger "`--reset` restarts the robot's bringup"
    `--reset` runs `systemctl restart turtlebot4.service` on the Raspberry Pi.
    Every participant of the TurtleBot graph drops and re-registers on the
    Discovery Server, and the dashboard loses telemetry for a while. Do not run
    it repeatedly to "test" something. During one debugging session, six resets
    in about fifteen minutes took telemetry down again.

!!! info "`--reset` and stale Nav2 processes"
    `--reset` also calls the host agent with `--cleanup` to remove old or
    manually started process generations, and fails if it cannot confirm that
    none are left. See
    [Recover the Discovery Server](recover-discovery-server.md) for why this
    matters.

## Stop

There is no single stop script. Stop in this order:

1. Stop any running mission: [Emergency stop](emergency-stop.md).
2. In the dashboard, stop Nav2, localization and the visualization (each
   stop route confirms the processes are gone).
3. Stop the containers:

    ```bash
    cd ~/B002_Future_Lab_Bots/future_lab_control_center
    docker compose down
    ```

!!! note "Not verified"
    A full shutdown sequence, including the Raspberry Pi and the cobot, has not
    been written down yet. Add it here when you establish it.
