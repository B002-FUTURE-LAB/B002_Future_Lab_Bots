# Recover the Discovery Server

**Symptom:** commands to the robot (such as undock) are ignored or very slow,
`ros2 node list` is empty although `exit=0`, and the TurtleBot Discovery Server
on the Raspberry Pi shows a large receive queue.

## What was found in the real incident

The server was not frozen. It was **overloaded**, using about 142 % CPU, while
its receive queue stayed around 164 to 198 KB. Roughly 1,100 packets per second
came from the host PC, which was running **25 Nav2 processes from three
stacked generations**.

The cycle was a feedback loop:

1. Nav2 is started.
2. Discovery saturates, so `nav_readiness` turns red.
3. Someone starts Nav2 again on top of the old one.
4. More participants join, and discovery saturates further.

The root cause was in `START_LAB.sh`. It killed only the parent
`ros2 launch` processes with `pkill`, and left their **children** alive. Those
orphans kept registering on the server. The fix (phase 22a) makes the cleanup
kill the whole process tree and fail if it cannot confirm that none remain.

## Diagnose

On the Raspberry Pi:

```bash
sudo ss -lunp | grep 11811        # the 2nd number is Recv-Q, in bytes
ps -o %cpu,cmd -C fast-discovery-server
```

On the host PC, count Nav2 generations:

```bash
pgrep -af 'nav2|amcl|map_server|controller_server|planner_server|bt_navigator' | wc -l
```

Each node should appear **once**. Two or more of any node means stacked
generations.

!!! warning "A high Recv-Q alone proves nothing"
    A full queue means packets are waiting, not that the server is stuck.
    Read it together with CPU: about 100 % CPU with a full queue means
    overload from too much traffic; about 0 % CPU with a full queue means a real
    hang. Also measure who is sending, for example with `tcpdump` on port 11811.

## Fix

1. Stop the source of traffic: stop Nav2, localization and the visualization
   from the dashboard, or run
   `python3 host_agent/agent.py --cleanup` on the host.
2. Confirm the count above is zero before continuing.
3. Restart the Discovery Server on the Raspberry Pi
   (`discovery.service`) to flush the queue.
4. Reset the CLI cache: `ros2 daemon stop; ros2 daemon start`.
5. Start localization, then Nav2, **once each**, and wait for the dashboard to
   show them ready before starting anything else.

!!! tip "Do not start Nav2 twice"
    The launch routes start one generation and report success only after the
    managed nodes are active. If the dashboard still looks red, wait, instead of
    clicking launch again.
