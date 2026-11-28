#!/bin/bash
# Configuration stage: saves the poses of the cycle (never moves the arm).
# Needs RUN_REAL.sh (or RUN_SIM.sh) running in another terminal.
#
#   ./scripts/TEACH.sh real            home, drawer_1..4_approach, dropoff
#   ./scripts/TEACH.sh real 2          only drawer 2
#   ./scripts/TEACH.sh real dropoff    only the dropoff point
#   ./scripts/TEACH.sh real --reach 0.06 2     drawer 2, item 6 cm ahead instead of 8 (check only)
#
# Real robot: [r] release servos (HOLD THE ARM), move it by hand, [Enter] save + lock.
# Simulation: drag the gimbal in RViz, Plan & Execute, [Enter].
# Drawer pose: cup 8 cm in front of the item, pointing at it. Enter saves it and checks
# that the 8 cm straight line forward is reachable (warning if not).
# Saved to config/drawer_poses_<mode>.yaml.
source "$(dirname "$0")/common.sh"
set_mode "$1"; shift
ros ros2 run drawer_picking drawer_teach --mode "$MODE" "$@"
