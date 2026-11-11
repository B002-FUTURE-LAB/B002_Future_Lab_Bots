# Configuration

The control center reads its settings from the file
`future_lab_control_center/.env`. Copy `.env.example` to `.env` and adjust it.
`.env` is private and is not tracked by Git.

## Variables

| Variable | Default in `.env.example` | Meaning |
|---|---|---|
| `HOST_PC_IP` | `192.168.0.204` | Address of the host PC. |
| `JETSON_NANO_IP` | `192.168.0.250` | Address of the Jetson Nano. The backend also probes `192.168.0.62`. |
| `TURTLEBOT_IP` | `192.168.0.129` | Address of the TurtleBot's Raspberry Pi. |
| `BACKEND_PORT` | `8000` | Port of the FastAPI backend. |
| `FRONTEND_PORT` | `3000` | Port of the dashboard. |
| `CAMERA_STREAM_URL` | `http://192.168.0.250:8080/stream.mjpg` | MJPEG stream of the cobot camera. |
| `DEFAULT_COOLDOWN_SEC` | `5.0` | Pause between automatic cycles. |
| `DEFAULT_YOLO_CONF` | `0.60` | Minimum YOLO confidence to accept a detection. |
| `DEFAULT_VELOCITY_SCALING` | `0.20` | Arm velocity scaling factor. |

!!! warning "The settings route writes to this file"
    `PUT /api/v1/settings/` updates `.env` while the backend is running. Edits
    made by hand and edits made through the dashboard share the same file.

## Other files that hold configuration

| File | Holds |
|---|---|
| `future_lab_control_center/docker-compose.yml` | Container settings, ROS environment, mounts. |
| `future_lab_control_center/.agent_token` | The host agent token (private). |
| `turtlebot4_jazzy/params/waypoints.yaml` | Navigation waypoints used by missions. |
| `nav_poses.yaml` | The saved dock pose. |
| `cobot/.../test_table_poses.yaml` | The cobot's saved poses. |
