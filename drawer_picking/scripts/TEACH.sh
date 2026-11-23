#!/bin/bash
# Configuration stage: saves the poses of the cycle (never moves the arm).
# Needs RUN_REAL.sh (or RUN_SIM.sh) running in another terminal.
#
#   ./scripts/TEACH.sh real            home, safe, drawer_1..4_pick, dropoff
#   ./scripts/TEACH.sh real 2          only drawer 2
#   ./scripts/TEACH.sh real dropoff    only the dropoff point
#   ./scripts/TEACH.sh real --retreat 0.06 2   approach 6 cm back instead of 8
#
# Real robot: [r] release servos (HOLD THE ARM), move it by hand, [Enter] save + lock.
# Simulation: drag the gimbal in RViz, Plan & Execute, [Enter].
# For a drawer pick, Enter also stores its approach pose straight back along the cup axis.
# Saved to config/drawer_poses_<mode>.yaml.
source "$(dirname "$0")/common.sh"
set_mode "$1"; shift
ros ros2 run drawer_picking drawer_teach --mode "$MODE" "$@"
