# 🤖 Future Lab Control Center

Unified Web Control Panel for Managing and Operating the Laboratory Robotic Cell (**MyCobot 280** + **TurtleBot 4**).

---

## 🌟 Key Features

- **Integrated Cell Monitoring**: Master control player (`Start`, `Interrupt`, `Emergency/Home`), Real Integrated Operation (`MoveIt + 3D View + Headless YOLO + Handshake + Delivery`), and mode selection (`Automatic` vs `Manual`).
- **Cobot Control & Vision**: Real-time MJPEG camera stream with live YOLO classification badge, adjustable confidence threshold (60%), post-pick cooldown (5s), and suction pump control.
- **Teach Mode & Pose Calibration**: Interactive table with the status of all 6 poses (`home`, `scan`, `pick_approach`, `pick`, `place_approach`, `place`), timestamped recording, playback testing, disk persistence, and backup restoration.
- **TurtleBot 4 Navigation & Missions**: Real-time Nav2 & AMCL readiness semaphore, 2D initial pose estimation, dock pose calibration, autonomous mission triggers (`delivery`, `failure`, `restock`), OAK-D live stream, and manual D-Pad teleoperation.
- **Dynamic Network & Service Diagnostics**: Live 10-service laboratory health inventory (`HOST_PC`, `JETSON_NANO`, `TURTLEBOT 4`, `CREATE 3`) and one-click service recovery.
- **Bilingual Interface (`🇧🇷 PT` / `🇺🇸 EN`)**: Full Portuguese and English support across all panels, modals, and status messages.

---

## 📁 Project Architecture

```text
future_lab_control_center/
├── .env.example          # Network configuration template (IPs and ports)
├── .env                  # Local configuration (gitignored)
├── .gitignore            # Repository ignore rules
├── README.md             # Project documentation
├── INSTALL.md            # Systemd user services & desktop launcher setup
├── host_agent/           # Host-side HTTP agent (:8100) for ROS 2 Jazzy & systemd control
├── backend/              # Python server (FastAPI + rclpy ROS 2)
│   ├── api/              # REST endpoints (cell, cobot, turtlebot, health, settings)
│   ├── config/           # Dynamic network settings & saved dock poses
│   └── ros2_nodes/       # ROS 2 hardware bridge & telemetry nodes
└── frontend/             # User Interface (Next.js + TailwindCSS)
    └── src/
        ├── components/   # Visual UI widgets & modals
        ├── context/      # LanguageContext (PT/EN internationalization)
        ├── pages/        # Main application dashboard
        └── utils/        # Translations dictionary & helpers
```
