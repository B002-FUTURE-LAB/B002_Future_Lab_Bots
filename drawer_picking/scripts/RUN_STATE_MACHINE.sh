#!/bin/bash
# State machine: keys 1-4 fetch an item from that drawer, h home, q quit.
# Needs RUN_SIM.sh / RUN_REAL.sh running. In real mode, only taught poses are used.
#
#   ./scripts/RUN_STATE_MACHINE.sh sim
#   ./scripts/RUN_STATE_MACHINE.sh real --speed 0.1 --linear-speed 0.015
source "$(dirname "$0")/common.sh"
set_mode "$1"; shift
ros ros2 run drawer_picking drawer_state_machine --mode "$MODE" "$@"
