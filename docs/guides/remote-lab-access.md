# Remote Lab Access (Tailscale, NoMachine & SSH)

Operators and researchers can access the **Host Control PC** (`future-lab`) remotely to monitor experiments, view RViz/Gazebo 3D windows, or inspect logs without being physically inside Lab B002.

---

## Remote Access Architecture

| Layer | Technology | Address / Port | Purpose |
| :--- | :--- | :--- | :--- |
| **Mesh VPN** | **Tailscale** (`tailscaled.service`) | `100.86.49.29` | Encrypted WireGuard overlay network connecting remote laptops to the Host Control PC across NAT/campus firewalls. |
| **Remote Desktop (GUI)** | **NoMachine (`nxserver.service`)** | `100.86.49.29:4000` (NX protocol) | Full hardware-accelerated X11 desktop session for viewing RViz2, MoveIt 2, and the Control Center browser UI. |
| **Remote Shell & Tunnels** | **OpenSSH Server (`sshd.service`)** | `100.86.49.29:22` (VPN) / `192.168.0.129:22` (Lab LAN) | CLI administration, log inspection, and local port forwarding (`:3000`, `:8000`). |

> [!CAUTION]
> Remote operation moves physical robots in Lab B002. Never trigger `handshake_test`, `integrated_real`, or Nav2 goals remotely unless a spotter is present in the lab or you have verified via live camera streams that the workspace is clear.

---

## Connecting via Tailscale + SSH

1. Ensure Tailscale is installed and authenticated on your remote workstation:

```bash
tailscale status
```

2. Verify reachability of the Host Control PC (`100.86.49.29`):

```bash
ping -c 3 100.86.49.29
```

3. Connect via SSH (with optional local port forwarding for the Control Center UI and FastAPI backend):

```bash
ssh -L 3000:127.0.0.1:3000 -L 8000:127.0.0.1:8000 future-lab@100.86.49.29
```

Once connected with `-L`, you can open `http://localhost:3000` directly in your local browser while the backend communicates locally on `127.0.0.1:8000`.

---

## Connecting via NoMachine (Full Graphical Desktop)

Use **NoMachine** when you need to interact with X11 applications running on the Host PC (`rviz2`, MoveIt `move_group`, or Gazebo):

1. Install the NoMachine client on your laptop.
2. Create a new connection:
   - **Host**: `100.86.49.29` (via Tailscale) or `192.168.0.129` (on Lab B002 Wi-Fi)
   - **Port**: `4000`
   - **Protocol**: `NX`
   - **Username**: `future-lab`
3. Log in with the `future-lab` system credentials.

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

The **Jetson Nano (`192.168.0.62`)** and **TurtleBot 4 Raspberry Pi (`192.168.0.21`)** are on the private `192.168.0.0/24` lab subnet and do not run Tailscale directly. To reach them remotely, use the Host Control PC as an SSH ProxyJump (`-J`):

```bash
# SSH directly into the TurtleBot 4 Raspberry Pi via the Host PC
ssh -J future-lab@100.86.49.29 ubuntu@192.168.0.21

# SSH directly into the MyCobot Jetson Nano via the Host PC
ssh -J future-lab@100.86.49.29 er@192.168.0.62
```
