# Remote Lab Access (VPN, Remote Desktop & SSH)

Operators and researchers can access the **Host Control PC** remotely to monitor experiments, view RViz/Gazebo 3D windows, or inspect logs without being physically inside Lab B002.

---

## Remote Access Architecture

| Layer | Technology | Address / Port | Purpose |
| :--- | :--- | :--- | :--- |
| **Mesh VPN** | **Tailscale** (`tailscaled.service`) | `<TAILSCALE_HOST_IP>` | Encrypted WireGuard overlay network connecting authorized workstations to the Host Control PC across NAT/campus firewalls. |
| **Remote Desktop (GUI)** | **NoMachine (`nxserver.service`)** | `<TAILSCALE_HOST_IP>:<REMOTE_DESKTOP_PORT>` (NX protocol) | Full hardware-accelerated X11 desktop session for viewing RViz2, MoveIt 2, and the Control Center browser UI. |
| **Remote Shell & Tunnels** | **OpenSSH Server (`sshd.service`)** | `<TAILSCALE_HOST_IP>:<SSH_PORT>` (VPN) / `<HOST_PC_IP>:<SSH_PORT>` (Lab LAN) | CLI administration, log inspection, and local port forwarding (`:<FRONTEND_PORT>`, `:<BACKEND_PORT>`). |

> [!CAUTION]
> Remote operation moves physical robots in Lab B002. Never trigger `handshake_test`, `integrated_real`, or Nav2 goals remotely unless a spotter is present in the lab or you have verified via live camera streams that the workspace is clear.

---

## Connecting via Tailscale + SSH

1. Ensure Tailscale is installed and authenticated on your authorized workstation:

```bash
tailscale status
```

2. Verify reachability of the Host Control PC (`<TAILSCALE_HOST_IP>`):

```bash
ping -c 3 <TAILSCALE_HOST_IP>
```

3. Connect via SSH (with optional local port forwarding for the Control Center UI and FastAPI backend):

```bash
ssh -p <SSH_PORT> \
  -L <FRONTEND_PORT>:127.0.0.1:<FRONTEND_PORT> \
  -L <BACKEND_PORT>:127.0.0.1:<BACKEND_PORT> \
  <HOST_USER>@<TAILSCALE_HOST_IP>
```

Once connected with `-L`, you can open `http://localhost:<FRONTEND_PORT>` directly in your local browser while the backend communicates locally on `127.0.0.1:<BACKEND_PORT>`.

---

## Connecting via NoMachine (Full Graphical Desktop)

Use **NoMachine** when you need to interact with X11 applications running on the Host PC (`rviz2`, MoveIt `move_group`, or Gazebo):

1. Install the NoMachine client on your workstation.
2. Create a new connection:
   - **Host**: `<TAILSCALE_HOST_IP>` (via Tailscale) or `<HOST_PC_IP>` (on Lab B002 Wi-Fi)
   - **Port**: `<REMOTE_DESKTOP_PORT>`
   - **Protocol**: `NX`
   - **Username**: `<HOST_USER>`
3. Authenticate with your local `<HOST_USER>` system credentials.

---

## Verifying Remote Access Services on the Host PC

If remote connections fail, check the service states on the Host PC:

```bash
# Verify Tailscale VPN status and IP
systemctl status tailscaled --no-pager
tailscale ip -4

# Verify NoMachine server status
systemctl status nxserver --no-pager

# Verify OpenSSH server status
systemctl status ssh --no-pager
```

---

## Accessing Sub-Nodes Through the Host PC (Jump Host)

The **Jetson Nano (`<JETSON_NANO_IP>`)** and **TurtleBot 4 Raspberry Pi (`<TURTLEBOT_IP>`)** live on the private `<LAB_SUBNET_CIDR>` lab subnet and do not run Tailscale directly. To reach them remotely, use the Host Control PC as an SSH ProxyJump (`-J`):

```bash
# SSH directly into the TurtleBot 4 Raspberry Pi via the Host PC
ssh -J <HOST_USER>@<TAILSCALE_HOST_IP> <TB4_USER>@<TURTLEBOT_IP>

# SSH directly into the MyCobot Jetson Nano via the Host PC
ssh -J <HOST_USER>@<TAILSCALE_HOST_IP> <NANO_USER>@<JETSON_NANO_IP>
```
