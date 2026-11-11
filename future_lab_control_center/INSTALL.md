# INSTALL.md — Installation and Operation Instructions

## 1. Installing User Systemd Services

In a host terminal (as user `future-lab`):

```bash
# Copy unit files to the user systemd directory
mkdir -p ~/.config/systemd/user
cp ~/B002_Future_Lab_Bots/future_lab_control_center/host_agent/systemd/*.service ~/.config/systemd/user/
systemctl --user daemon-reload

# Enable and start the services
systemctl --user enable --now future-lab-agent future-lab-cobot-discovery

# Enable linger so services stay running without an active login session
sudo loginctl enable-linger future-lab
```

## 2. Testing the Host Agent

```bash
curl -s http://127.0.0.1:8100/health | jq .
```

## 3. Desktop Shortcut

```bash
cp ~/B002_Future_Lab_Bots/future_lab_control_center/FutureLab.desktop ~/Desktop/
cp ~/B002_Future_Lab_Bots/future_lab_control_center/FutureLab.desktop ~/.local/share/applications/
chmod +x ~/Desktop/FutureLab.desktop ~/.local/share/applications/FutureLab.desktop
```
*In GNOME, right-click the Desktop icon and select **Allow Launching**.*

## 4. Manual Create 3 Recovery (If Needed)

- Create 3 base web interface: `http://192.168.186.2` (reachable from the TurtleBot 4 RPi over `usb0`).
- Physical button on the Create 3 base for electrical reset if unresponsive.
- **Warning:** Never call `ros2 service call /robot_power` for automated restarts, as it powers down the Create 3 base completely.
