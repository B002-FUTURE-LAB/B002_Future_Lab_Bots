# Configuration

The control center loads local network addresses, ports, and private credentials from a local `.env` file (`future_lab_control_center/.env`, ignored by Git).

To configure a fresh environment, download or copy **`future_lab_control_center/.env.example`** directly from the public [GitHub repository](https://github.com/B002-FUTURE-LAB/B002_Future_Lab_Bots/blob/main/future_lab_control_center/.env.example) to `.env` and fill in the values matching your laboratory setup:

```bash
cd ~/B002_Future_Lab_Bots/future_lab_control_center
cp .env.example .env
```

---

## Variables Defined in `.env.example`

Refer to [`future_lab_control_center/.env.example`](https://github.com/B002-FUTURE-LAB/B002_Future_Lab_Bots/blob/main/future_lab_control_center/.env.example) for the exact template keys and comments:

| Variable | Template Placeholder / Scope | Meaning |
|---|---|---|
| `HOST_PC_IP` | `<HOST_PC_IP>` | LAN IP address of the Host Control PC. |
| `JETSON_NANO_IP` | `<JETSON_NANO_IP>` | LAN IP address of the MyCobot Jetson Nano (Wi-Fi or wired). |
| `TURTLEBOT_IP` | `<TURTLEBOT_IP>` | LAN IP address of the TurtleBot 4 Raspberry Pi 4. |
| `BACKEND_PORT` | `<BACKEND_PORT>` | Port used by the FastAPI backend. |
| `FRONTEND_PORT` | `<FRONTEND_PORT>` | Port used by the Next.js web dashboard. |
| `CAMERA_STREAM_URL` | `http://<JETSON_NANO_IP>:<CAMERA_STREAM_PORT>/stream.mjpg` | MJPEG video stream URL for the wrist camera. |
| `DEFAULT_COOLDOWN_SEC` | `5.0` | Pause between automatic cell cycles (seconds). |
| `DEFAULT_YOLO_CONF` | `0.60` | Minimum YOLO confidence threshold (`0.0–1.0`). |
| `DEFAULT_VELOCITY_SCALING` | `0.20` | Manipulator velocity scaling factor. |
| `JETSON_NANO_SSH_USER` | `<NANO_USER>` | See `.env.example` in the GitHub repository. |
| `JETSON_NANO_SSH_PASSWORD` | `<PRIVATE_CREDENTIAL>` | Private local value set in `.env` (see `.env.example` on GitHub). |
| `HOST_AGENT_TOKEN` | `<PRIVATE_CREDENTIAL>` | Private local value set in `.env` (see `.env.example` on GitHub). |
| `OPCUA_USER` | `<OPCUA_USER>` | See `.env.example` in the GitHub repository. |
| `OPCUA_PASSWORD` | `<PRIVATE_CREDENTIAL>` | Private local value set in `.env` (see `.env.example` on GitHub). |

!!! warning "The settings route writes to `.env`"
    `PUT /api/v1/settings/` updates your local `.env` file while the backend is running. Edits made by hand and edits made through the dashboard share the same file.

---

## Other Configuration Files

| File | Holds |
|---|---|
| `future_lab_control_center/docker-compose.yml` | Container settings, ROS environment, and volume mounts. |
| `turtlebot4_jazzy/params/waypoints.yaml` | Navigation waypoints and timeout/freshness thresholds. |
| `cobot/mycobot_docker/cobot_poses.yaml` | Calibrated 6-DOF manipulator poses. |
| `integration_cobot_tb4/config/anchor.yaml` | Static `map -> mycobot_base_link` transform and table dimensions. |
