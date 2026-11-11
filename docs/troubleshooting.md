# Troubleshooting

Find your symptom, then follow the link. Every row comes from a problem that
actually happened in this lab.

| Symptom | Likely cause | Fix |
|---|---|---|
| `telemetry_ok: false`, battery `null` | Create 3 application crashed, or the republisher is down | [Recover TurtleBot telemetry](guides/recover-turtlebot-telemetry.md) |
| Base answers ping, web page says "Oops, something went wrong" | The Create 3 application crashed | [Restart the Create 3 application](guides/restart-the-create3-app.md) |
| Undock or other commands ignored, `ros2 node list` empty | Discovery Server overloaded by stacked Nav2 processes | [Recover the Discovery Server](guides/recover-discovery-server.md) |
| Dashboard shows telemetry lost right after a reset | `START_LAB.sh --reset` restarted the bringup | Wait about a minute. Avoid repeated resets. See [Start and stop the lab](guides/start-and-stop-the-lab.md) |
| Cobot does not respond after a Wi-Fi reconnect | The Jetson Nano got a different IP | Check `192.168.0.62` and `192.168.0.250`. See [Hardware and network](getting-started/hardware-and-network.md) |
| Stop mission answers `partial` | The Nav2 server did not confirm the cancellation | Use the physical Create 3 button. See [Emergency stop](guides/emergency-stop.md) |
| Backend logs `type object 'type' has no attribute '_TYPE_SUPPORT'` | A message class was used without being imported (the fix was an import of `Bool` in `cobot_node.py`) | Check that the message classes are imported in the node that fails |
| Dashboard page is blank | A frontend runtime error (identifiers used but not defined) | Open the browser console; check the component named in the error |
| `trigger_patrol` returns HTTP 501 | Not implemented: the mission manager has no `/start_patrol` | None. The route is a placeholder |
| `set_dock_status` has no effect | Deprecated: dock state comes from Create 3 telemetry | Fix the telemetry instead |

!!! tip "Add a row when you solve something new"
    A new person will meet the same problem. Add the symptom, the cause and a
    link to a guide, in the same pull request that fixes it.
