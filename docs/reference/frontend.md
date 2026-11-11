# Frontend Architecture (Next.js 14 Dashboard)

The **Control Center Web Dashboard** (`future_lab_control_center/frontend/`) is a **Next.js 14** (Pages Router, React 18, Tailwind CSS) single-page operator console served on `http://localhost:3000`.

---

## Directory Structure

```text
future_lab_control_center/frontend/src/
├── pages/
│   ├── _app.js                      # Wraps app in LanguageProvider + global CSS
│   └── index.js                     # Main dashboard layout, tab switcher, polling loops
├── components/
│   ├── NetworkStatusHeader.jsx      # Top bar health badges, recovery buttons, EN/PT toggle
│   ├── CellControlPanel.jsx         # Auto/Manual cycle controls, Handshake & Integrated Real modes
│   ├── CameraVisionPanel.jsx        # Live MJPEG wrist-camera stream, YOLO bounding boxes & simulation
│   ├── TeachModePanel.jsx           # Servo release/lock, live 6-DOF joint angles, pose calibration
│   ├── TurtleBotPanel.jsx           # Summary TurtleBot telemetry card on the main Cell view
│   ├── TurtleBotDashboardTab.jsx    # Full TurtleBot 4 console (2D Map, OAK-D, Nav2, Dock, Mission Manager)
│   ├── PanicOverlayModal.jsx        # Full-screen Emergency Stop (PANIC) lock & reset modal
│   ├── InterruptOverlayModal.jsx    # Cycle Pause confirmation modal (Resume vs. Safe Abort)
│   ├── RebootOverlayModal.jsx       # Progress modal during Jetson Nano / RPi4 hardware reboots
│   └── NotificationToast.jsx        # Non-blocking operator toast notifications
├── context/
│   └── LanguageContext.js           # React context providing t() translation lookup (pt / en)
└── utils/
    └── translations.js              # Bilingual dictionary (Portuguese & English UI strings)
```

---

## Component Responsibilities & API Bindings

| Component | Polled / Called Endpoints | Key Features |
| :--- | :--- | :--- |
| **`NetworkStatusHeader.jsx`** | `GET /api/v1/health/full`, `POST /api/v1/health/recover/*` | Displays real-time connectivity for Host API, MyCobot Nano (`:8088`), TurtleBot 4 (`:11811` / telemetry), and Camera (`:8080`), plus one-click recovery actions and language switcher. |
| **`CellControlPanel.jsx`** | `GET /api/v1/cell/status`, `POST /api/v1/cell/mode`, `/auto_start`, `/manual_start`, `/step_pick`, `/step_place`, `/handshake_test`, `/integrated_real/*` | Controls the cooperative cell state machine: Auto Mode, Manual Step-by-Step Mode, Standalone Handshake Test (`blue`/`red`), and `Integrated Real Mode` (with visual preflight and YOLO candidate confirmation). |
| **`CameraVisionPanel.jsx`** | `GET http://192.168.0.62:8080/stream.mjpg`, `POST /api/v1/cobot/yolo_start`, `/yolo_stop`, `/yolo_sim` | Embeds the live wrist-camera MJPEG feed, starts/stops the YOLOv8 detector, and provides synthetic item injection (`blue`, `red`, `invalid`) for simulation. |
| **`TeachModePanel.jsx`** | `GET /api/v1/cobot/status`, `GET /api/v1/cobot/poses`, `POST /api/v1/cobot/release_servos`, `/lock_servos`, `/goto_pose`, `/poses/<name>`, `/poses_restore_backup` | Hand-guiding calibration console for the 6 required manipulator poses (`home`, `scan`, `pick_approach`, `pick`, `place_approach`, `place`), joint sliders, and vacuum pump toggle (`POST /api/v1/cobot/pump`). |
| **`TurtleBotDashboardTab.jsx`** | `GET /api/v1/turtlebot/status`, `/nav_readiness`, `/processes`, `/map`, `/camera`, `POST /api/v1/turtlebot/mission/*`, `/initial_pose`, `/dock_pose`, `/teleop` | Dedicated TurtleBot 4 operations center: interactive 2D OccupancyGrid map canvas with live robot pose and waypoints, OAK-D Pro camera preview, virtual joystick (`cmd_vel`), Nav2/SLAM/RViz/3D launchers, and Mission Manager controls. |
| **`PanicOverlayModal.jsx`** | `POST /api/v1/cell/panic`, `POST /api/v1/cell/panic_reset` | Activated whenever `cell_state.panic_locked == true`. Blocks normal controls until the operator verifies the workspace and clicks **Reset Panic & Home**. |
| **`InterruptOverlayModal.jsx`** | `POST /api/v1/cell/interrupt`, `POST /api/v1/cell/interrupt_confirm` | Displayed when a cycle is paused mid-motion. Lets the operator choose **Continue (`abort: false`)** (re-sends interrupted trajectory) or **Abort (`abort: true`)** (rolls back can and returns to `home`). |

---

## Polling Architecture & State Synchronization

The frontend uses bounded HTTP polling (`pages/index.js` and `TurtleBotDashboardTab.jsx`) rather than fragile browser WebSockets so that temporary Wi-Fi hiccups or backend restarts recover seamlessly:

- **Core Cell & Robot State**: Polled every `1000 ms` (`1 Hz`) via `GET /api/v1/cell/status`, `GET /api/v1/cobot/status`, and `GET /api/v1/turtlebot/status`.
- **Infrastructure Health**: Polled every `3000–5000 ms` via `GET /api/v1/health/full` and `GET /api/v1/turtlebot/nav_readiness`.
- **2D Map & Waypoints**: Loaded on tab mount and refreshed on demand (`GET /api/v1/turtlebot/map`, `GET /api/v1/turtlebot/waypoints`).

---

## Internationalization (`LanguageContext.js` & `translations.js`)

All user-facing labels, status badges, and modal prompts support instant switching between **Portuguese (`pt`)** and **English (`en`)** via `useLanguage()` (`const { t, language, toggleLanguage } = useLanguage()`). When adding a new button or status message in any `.jsx` component, add its key under both `pt` and `en` in `future_lab_control_center/frontend/src/utils/translations.js`.
