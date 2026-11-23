#!/bin/bash
# Shared helpers for the drawer_picking scripts (sourced, not run).
#
#   set_mode sim|real   sets ROS_ENV (sim: FastDDS, all local; real: CycloneDDS, PC <-> Jetson Nano)
#   ensure_container    creates/starts the drawer_picking_ros2 container (ARM64 aware)
#   build               colcon build of the workspace
#   ros <command>       runs a ROS command inside the container

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONTAINER=drawer_picking_ros2

set_mode() {
  MODE="$1"
  case "$MODE" in
    sim)  RMW="export RMW_IMPLEMENTATION=rmw_fastrtps_cpp FASTDDS_BUILTIN_TRANSPORTS=UDPv4" ;;
    real) RMW="export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp" ;;
    *) echo "First argument must be sim or real"; exit 1 ;;
  esac
  ROS_ENV="export ROS_DOMAIN_ID=42; $RMW; unset CYCLONEDDS_URI
    source /opt/ros/galactic/setup.bash
    [ -f /root/drawer_ws/install/setup.bash ] && source /root/drawer_ws/install/setup.bash"
}

ensure_container() {
  if ! docker inspect "$CONTAINER" >/dev/null 2>&1; then
    # osrf/ros:galactic-desktop is x86_64 only; use the multi-arch image on ARM64.
    case "$(uname -m)" in aarch64|arm64) export BASE_IMAGE="${BASE_IMAGE:-ros:galactic}" ;; esac
    echo "Creating $CONTAINER (first time: building the image takes several minutes)..."
    docker compose -f "$ROOT/docker-compose.yml" up -d --build || exit 1
  fi
  docker start "$CONTAINER" >/dev/null || exit 1
  if [ "$(docker inspect -f '{{.State.Running}}' mycobot_ros2 2>/dev/null)" = "true" ]; then
    echo "WARNING: cobot's mycobot_ros2 container is also running on ROS_DOMAIN_ID=42. Stop it: docker stop mycobot_ros2"
  fi
}

build() {
  docker exec "$CONTAINER" bash -c "$ROS_ENV; cd /root/drawer_ws && colcon build --symlink-install 2>&1 | tail -2" || exit 1
}

stop_ros() {
  docker exec "$CONTAINER" bash -c "pkill -9 -f 'ros2|rviz|move_group|robot_state|static_transform|mycobot_bridge|drawer_|cabinet_marker'" 2>/dev/null || true
}

ros() {
  local tty=-i; [ -t 0 ] && tty=-it
  docker exec $tty -e DISPLAY="${DISPLAY:-:0}" "$CONTAINER" bash -c "$ROS_ENV; $*"
}
