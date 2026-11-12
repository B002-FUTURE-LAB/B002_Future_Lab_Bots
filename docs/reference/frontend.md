# Frontend Dashboard: Internal Architecture & Source Code Developer Guide

The **Control Center Web Dashboard** (`future_lab_control_center/frontend/`) is a **Next.js 14** (Pages Router, React 18, Tailwind CSS 3) web application served on port `<FRONTEND_PORT>`. It acts as the unified graphical layer over the FastAPI + ROS 2 backend (`:<BACKEND_PORT>`).

For an operator walkthrough of every screen, button, and modal, see [Using the Web Control Center Dashboard](../guides/using-the-dashboard.md).

---

## 1. Directory Structure

```text
future_lab_control_center/frontend/
├── Dockerfile                       # node:18-slim image running `npm run dev` on :<FRONTEND_PORT>
├── package.json                     # Next.js 14, React 18, lucide-react, Tailwind CSS 3
└── src/
    ├── pages/
    │   ├── _app.js                  # Wraps the app in <LanguageProvider> + globals.css
    │   └── index.js                 # Central state hub, polling loops & all API handlers (851 lines)
    ├── components/
    │   ├── NetworkStatusHeader.jsx  # Top bar: EN/PT toggle + Host, Nano, Camera, TB4 badges
    │   ├── CellControlPanel.jsx     # Master cell modes, Integrated Real, Handshake Test, sliders
    │   ├── CameraVisionPanel.jsx    # Wrist MJPEG player, YOLO test, optimistic pump toggle
    │   ├── TeachModePanel.jsx       # Servo release/lock, 6-pose table, playback, backup/restore
    │   ├── TurtleBotDashboardTab.jsx# Full TB4 tab: telemetry, OAK-D, D-Pad, Nav2, Mission & logs
    │   ├── TurtleBotPanel.jsx       # Legacy compact TB4 summary card (retained for reference)
    │   ├── PanicOverlayModal.jsx    # Full-screen blocking modal when panic_locked === true
    │   ├── InterruptOverlayModal.jsx# Pause decision modal (abort: true vs. abort: false)
    │   ├── RebootOverlayModal.jsx   # Timed 5-step hardware reboot progress modal
    │   └── NotificationToast.jsx    # Auto-dismissing (15 s) status/error toast banner
    ├── context/
    │   └── LanguageContext.js       # Bilingual React Context (`lang`, `toggleLanguage`, `t`, `tb`)
    ├── styles/
    │   └── globals.css              # Dark industrial theme (#0b0f19), `.glass-card`, `.btn-hover`
    └── utils/
        └── translations.js          # `translations.{pt,en}` + `BACKEND_EXACT_EN` / `translateBackendText`
```

---

## 2. How the Dashboard Works Internally

### 2.1 Dynamic API Resolution (`getApiBase()`)

In `future_lab_control_center/frontend/src/pages/index.js` (and directly in `TurtleBotDashboardTab.jsx`), the backend URL is computed dynamically from the browser's hostname:

```javascript
const getApiBase = () => {
  if (typeof window !== 'undefined') {
    const host = window.location.hostname || 'localhost';
    return `http://${host}:<BACKEND_PORT>/api/v1`;
  }
  return 'http://localhost:<BACKEND_PORT>/api/v1';
};
```

Because it avoids hardcoding `localhost`, accessing the dashboard over Lab Wi-Fi (`<TURTLEBOT_IP>:<FRONTEND_PORT>`) or Tailscale VPN (`<TAILSCALE_HOST_IP>:<FRONTEND_PORT>`) automatically targets the backend on `:<BACKEND_PORT>` at that same IP address.

### 2.2 Dual-Frequency Polling Architecture

Instead of fragile browser WebSockets that drop on Wi-Fi roaming, the dashboard uses two resilient HTTP polling intervals initialized in `useEffect` inside `src/pages/index.js` plus two scoped loops inside `TurtleBotDashboardTab.jsx`:

| Loop | Interval | Endpoints Polled | State Updated |
| :--- | :---: | :--- | :--- |
| **`refreshFastStatus()`** (`index.js`) | `2000 ms` | `/health/`, `/cell/status`, `/cobot/poses`, `/turtlebot/status` | `health`, `cellStatus`, `poses`, `tbStatus` (and resets optimistic flags) |
| **`refreshSlowStatus()`** (`index.js`) | `10000 ms` | `/turtlebot/nav_readiness`, `/turtlebot/processes` | `tbNavReadiness`, `tbProcesses` |
| **`fetchAmclAndPoses()`** (`TurtleBotDashboardTab`) | `2000 ms` | `/turtlebot/amcl_status`, `/turtlebot/nav_poses` | `amclStatus`, `navPoses` |
| **`fetchInventory()`** (`TurtleBotDashboardTab`) | `5000 ms` | `/turtlebot/system/inventory` | `inventoryItems` |

Every operator action handler in `index.js` calls `refreshStatus()` immediately after the `POST` completes so the UI reflects backend state changes without waiting up to 2 seconds for the next tick.

### 2.3 Safe API Error Wrapper & Optimistic UI

- **`safeApiCall(url, options, warningTitle)`**: Wraps `fetch()` in a `try/catch`, parses JSON safely (`.catch(() => ({}))`), translates backend error details via `tb(data.detail || data.message)`, and triggers a `NotificationToast` on HTTP errors or network failures without throwing unhandled React exceptions.
- **Optimistic State (`optimisticPump`, `optimisticYoloTest`)**: Buttons like **Pump ON/OFF** and **Test YOLO** update visually in `0 ms` on click and automatically sync back to authoritative `cellStatus` on the next `refreshFastStatus()` response.

### 2.4 Tab Rendering & Safety UI Interlocks

- **Preserving State Across Tabs**: Both tabs (`activeTab === 'cobot'` and `activeTab === 'turtlebot'`) remain mounted in the DOM using Tailwind visibility classes (`block` vs. `hidden`) rather than conditional unmounting, so input fields, log buffers, and diagnostics survive tab switches.
- **Teach Mode Lock (`TeachModePanel.jsx`)**: Automatically applies `opacity-70 pointer-events-none select-none` and shows an amber lock banner whenever `cellState.auto_running` is `true`.
- **Execution Gates (`CellControlPanel.jsx`)**: Both **Integrated Real Mode** and **Test Handshake** require `turtleReady` (`tbNavReadiness.mission_ready === true`) and `managerReady` (`mission_manager.running === true && instances === 1 && visible_on_ros_graph === true`) before enabling their start buttons.
- **Blocking Overlays**: `RebootOverlayModal`, `PanicOverlayModal` (`panic_locked === true`), and `InterruptOverlayModal` (`status === 'interrupted_paused'`) render as fixed `z-50` overlays above the entire page.

### 2.5 Bilingual Internationalization (`LanguageContext.js` + `translations.js`)

The `LanguageProvider` in `_app.js` manages `lang` (`'en'` default, persisted in `localStorage.getItem('future_lab_lang')`):

- **`t(key)`**: Looks up `translations[lang][key]` with automatic fallback to `translations.pt[key]`.
- **`tb(backendText)`**: Calls `translateBackendText(text, lang)` in `src/utils/translations.js` to translate exact FastAPI Portuguese strings (`BACKEND_EXACT_EN` lookup + phrase `.replace(...)` rules) into English whenever `lang === 'en'`.

---

## 3. Component Props & API Mapping Summary

| Component | Key Props / State | Backend Endpoints Used |
| :--- | :--- | :--- |
| **`NetworkStatusHeader`** | `healthData` | `GET /api/v1/health/` |
| **`CellControlPanel`** | `cellState`, `tbNavReadiness`, `tbProcesses`, `tbStatus` | `POST /cell/mode`, `/cell/auto/{start,stop}`, `/cell/integrated_real/{start,stop,confirm_detection}`, `/cell/manual/{start_scan,authorize_pick,authorize_place}`, `/cell/interrupt`, `/cell/interrupt/confirm`, `/cell/stop`, `/cell/panic`, `/cell/test_handshake` |
| **`CameraVisionPanel`** | `streamUrl`, `cameraOnline`, `lastYolo`, `pumpActive`, `yoloTestActive` | `GET <nano>:<CAMERA_STREAM_PORT>/stream.mjpg`, `POST /cobot/pump`, `/cobot/yolo_test`, `/health/restart_camera`, `/health/stop_camera` |
| **`TeachModePanel`** | `cellState`, `posesData` | `GET /cobot/poses`, `POST /cobot/teach/{release,lock,record/<name>,save,playback,restore}`, `DELETE /cobot/teach/clear`, `POST /cobot/move/<name>`, `POST /health/launch_rviz` |
| **`TurtleBotDashboardTab`** | `tbStatus`, `tbDiag`, `tbNavReadiness`, `tbProcesses` | `GET /turtlebot/{diagnose,amcl_status,nav_poses,logs,camera_feed,system/inventory}`, `POST /turtlebot/{dock,undock,teleop,set_initial_pose,save_dock_pose,clear_costmaps,launch_*,stop_*,trigger_*,mission_test/*}` |

---

## 4. How to Run, Modify & Extend the Dashboard Source Code

### 4.1 Running in Hot-Reload Development Mode

You can run the Next.js dev server directly on the Host Control PC for instant hot-reload while editing `.jsx` files (make sure the FastAPI backend is running on `:<BACKEND_PORT>` and stop any conflicting containerized `:<FRONTEND_PORT>` instance first):

```bash
cd ~/B002_Future_Lab_Bots/future_lab_control_center/frontend
npm install
npm run dev
```

To test production compilation and linting before committing:

```bash
npm run lint
npm run build
```

If running via Docker Compose (`future_lab_frontend`), `./frontend/src:/app/src` is bind-mounted in `docker-compose.yml`, so edits in `src/` hot-reload automatically inside the container. Only changes to `package.json` require rebuilding the image:

```bash
cd ~/B002_Future_Lab_Bots/future_lab_control_center
docker compose up -d --build frontend
```

### 4.2 Recipe: Adding a New Control Button End-to-End

Follow these 6 steps whenever you add a new robot action to the dashboard:

1. **Expose the backend route** in `future_lab_control_center/backend/api/<module>_routes.py` and document it in [REST API](rest-api.md) (checked by `check_route_coverage.py`).
2. **Add an async handler in `src/pages/index.js`** using `getApiBase()`, `safeApiCall()`, and `refreshStatus()`:

   ```javascript
   const handleMyNewAction = async (param) => {
     const apiBase = getApiBase();
     const { ok, data } = await safeApiCall(
       `${apiBase}/cell/my_new_action`,
       {
         method: 'POST',
         headers: { 'Content-Type': 'application/json' },
         body: JSON.stringify({ param })
       },
       t('myNewActionTitle')
     );
     if (ok) {
       setNotification({
         type: 'success',
         title: t('myNewActionSuccessTitle'),
         message: tb(data.message)
       });
     }
     refreshStatus();
   };
   ```

3. **Pass the handler prop** from `index.js` into the target component (`CellControlPanel`, `TeachModePanel`, `CameraVisionPanel`, or `TurtleBotDashboardTab`).
4. **Render the button using Tailwind + `.glass-card` / `.btn-hover`**, honoring safety lock conditions (`disabled={isCycleRunning}` or `isAutoRunning`) and `lucide-react` icons.
5. **Add bilingual keys in `src/utils/translations.js`**:
   - Add the new keys under both `translations.pt` and `translations.en`.
   - If the FastAPI backend returns a Portuguese `message` or `detail` string, add an exact translation entry in `BACKEND_EXACT_EN` at the bottom of `translations.js` so `tb(data.message)` translates it automatically in English mode.
6. **Verify locally** with `npm run build` and check browser DevTools Console for runtime or missing-key warnings.

### 4.3 Common Pitfalls When Editing Frontend Code

- **Hardcoding `localhost` in `fetch()`**: Always call `getApiBase()` (`window.location.hostname:<BACKEND_PORT>`) so remote operators on LAN or Tailscale can trigger actions.
- **Unwrapping raw `data.detail` without `tb()`**: Always wrap backend messages in `tb(...)` so English-mode users do not see raw Portuguese exceptions.
- **Leaving a modal unguarded**: Global overlays (`PanicOverlayModal`, `InterruptOverlayModal`) must always take priority over normal tabs; render them at the top of `<main>` inside `src/pages/index.js`.
- **Adding large dependencies without checking `Dockerfile`**: If you add a new npm package, update `package.json` and rebuild the frontend Docker image if using Compose.
