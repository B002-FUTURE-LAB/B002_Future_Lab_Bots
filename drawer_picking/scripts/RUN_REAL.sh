#!/bin/bash
# Real robot: restart mycobot_bridge on the Jetson Nano (same steps as
# cobot/mycobot_docker/RUN_PLANNING_PC.sh), then MoveIt 2 + RViz + cabinet.
# Needs JETSON_NANO_SSH_PASSWORD in future_lab_control_center/.env
# (JETSON_NANO_IP and JETSON_NANO_SSH_USER are optional).
# Then, in another terminal: ./scripts/TEACH.sh real (once), ./scripts/RUN_STATE_MACHINE.sh real
source "$(dirname "$0")/common.sh"
set_mode real

ENV_FILE="$ROOT/../future_lab_control_center/.env"
[ -f "$ENV_FILE" ] && { set -a; source "$ENV_FILE"; set +a; }
PASS="${JETSON_NANO_SSH_PASSWORD:?Set JETSON_NANO_SSH_PASSWORD in $ENV_FILE}"
NANO="${JETSON_NANO_SSH_USER:-er}@${JETSON_NANO_IP:-192.168.0.62}"
nano() { timeout 12 sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=8 "$NANO" "$1"; }

ensure_container
stop_ros
build

echo "Restarting mycobot_bridge on $NANO..."
nano "echo '$PASS' | sudo -S fuser -k /dev/ttyTHS1; pkill -9 -f mycobot_bridge" >/dev/null 2>&1
sleep 2
nano 'nohup bash ~/start_bridge.sh >/tmp/bridge.log 2>&1 </dev/null &' >/dev/null 2>&1
sleep 4
if [ "$(nano 'pgrep -f mycobot_bridge | wc -l' 2>/dev/null)" -gt 0 ] 2>/dev/null; then
  echo "Bridge OK"
else
  echo "Bridge FAILED. Check: ssh $NANO 'cat /tmp/bridge.log'"; exit 1
fi

xhost +local:root >/dev/null 2>&1
ros ros2 launch drawer_picking drawer_cell.launch.py use_mock_bridge:=false
