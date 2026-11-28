#!/bin/bash
# Simulated cell (no robot): mock bridge + MoveIt 2 + RViz + example cabinet.
# Then, in another terminal: ./scripts/RUN_STATE_MACHINE.sh sim
source "$(dirname "$0")/common.sh"
set_mode sim
ensure_container
stop_ros
build
xhost +local:root >/dev/null 2>&1
ros ros2 launch drawer_picking drawer_cell.launch.py use_mock_bridge:=true
