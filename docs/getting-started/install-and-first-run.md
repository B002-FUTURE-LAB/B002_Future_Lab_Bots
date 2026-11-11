# Install and first run

Run everything on the host PC as the user `future-lab`. The repository is
expected at `~/B002_Future_Lab_Bots`.

!!! warning "Fixed paths"
    `docker-compose.yml` and the systemd units contain absolute paths to
    `/home/future-lab/B002_Future_Lab_Bots`. Installing anywhere else needs
    those paths changed.

## 1. Configure the environment

```bash
cd ~/B002_Future_Lab_Bots/future_lab_control_center
cp .env.example .env
```

Edit `.env` for your network. The variables are described in
[Configuration](../reference/configuration.md).

## 2. Install the user services

```bash
mkdir -p ~/.config/systemd/user
cp ~/B002_Future_Lab_Bots/future_lab_control_center/host_agent/systemd/*.service \
   ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now future-lab-agent future-lab-cobot-discovery

# Let the services run without an open login session
sudo loginctl enable-linger future-lab
```

This installs the [host agent](../reference/host-agent.md) and the cobot
Discovery Server.

## 3. Check the host agent

```bash
curl -s http://127.0.0.1:8100/health
```

A healthy agent answers with `"ok": true`.

## 4. Optional: desktop shortcut

```bash
cp ~/B002_Future_Lab_Bots/future_lab_control_center/FutureLab.desktop ~/Desktop/
cp ~/B002_Future_Lab_Bots/future_lab_control_center/FutureLab.desktop ~/.local/share/applications/
chmod +x ~/Desktop/FutureLab.desktop ~/.local/share/applications/FutureLab.desktop
```

On GNOME, right-click the icon on the desktop and choose **Allow Launching**.

## 5. First run

```bash
cd ~/B002_Future_Lab_Bots/future_lab_control_center
./START_LAB.sh
```

The script starts the stack and opens the dashboard. Its steps are listed in
[Start and stop the lab](../guides/start-and-stop-the-lab.md). When it
finishes, the dashboard is at `http://localhost:3000` and the API documentation
at `http://localhost:8000/docs`.

!!! tip "Dry run"
    `./START_LAB.sh --check` only verifies the environment and does not start
    anything.
