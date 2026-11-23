"""drawer_state_machine: press 1-4 to fetch an item from that drawer.

Keys: 1-4 drawer, h home, q quit.

Usage: ros2 run drawer_picking drawer_state_machine --mode sim|real [--speed 0.2] [--linear-speed 0.02]
"""
import argparse
import queue
import sys
import threading

import rclpy

from drawer_picking import poses
from drawer_picking.keyboard import Keyboard
from drawer_picking.robot import Robot
from drawer_picking.state_machine import DrawerStateMachine

MENU = '\n  Keys: [1] [2] [3] [4] drawer   [h] home   [q] quit\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--mode', choices=['sim', 'real'], default='sim')
    parser.add_argument('--speed', type=float, default=0.2, help='free moves: velocity scaling 0-1')
    parser.add_argument('--linear-speed', type=float, default=0.02,
                        help='straight-line moves (in/out of the drawer): cup speed, m/s')
    parser.add_argument('--settle', type=float, default=1.0, help='seconds to wait after the pump')
    args, ros_args = parser.parse_known_args()

    pose_set = poses.load(args.mode)
    missing = poses.problems(pose_set)
    if missing:
        print(f'Poses not ready for mode "{args.mode}":\n  ' + '\n  '.join(missing))
        print(f'Teach them first: ./scripts/TEACH.sh {args.mode}')
        return 1
    for warning in poses.warnings(pose_set):
        print(f'WARNING: {warning}')

    rclpy.init(args=ros_args)
    node = rclpy.create_node('drawer_state_machine')
    log = node.get_logger()
    requests = queue.Queue()
    robot = Robot(node, args.speed, args.linear_speed)

    sm = DrawerStateMachine(robot, pose_set, poses.DRAWERS, args.settle,
                            on_state=lambda state: log.info(f'[STATE] {state}'))
    stop = threading.Event()

    def read_keys():
        with Keyboard() as kb:
            while not stop.is_set():
                key = kb.get()
                if key:
                    requests.put(key)

    try:
        robot.wait_ready()
        if args.mode == 'real':
            input('The arm will move to home with a free move. If it is inside a drawer or near the '
                  'cabinet, move it out first (TEACH.sh: [r] release). Press Enter to continue... ')
        sm.go_home()
        threading.Thread(target=read_keys, daemon=True).start()
        print(MENU, flush=True)
        while rclpy.ok():
            try:
                key = requests.get(timeout=0.2)
            except queue.Empty:
                continue
            if key == 'q':
                break
            if key == 'h':
                sm.go_home()
            elif key.isdigit() and int(key) in poses.DRAWERS:
                sm.poses = poses.load(args.mode)      # pick up poses re-taught meanwhile
                if sm.run_cycle(int(key)):
                    log.info(f'Drawer {key} done ({sm.cycles_done} cycles so far).')
            else:
                continue
            while not requests.empty():              # drop keys pressed during the cycle
                requests.get_nowait()
            print(MENU, flush=True)
        sm.go_home()
    except (RuntimeError, KeyboardInterrupt) as err:
        log.error(str(err) or 'interrupted')
    finally:
        stop.set()
        robot.shutdown()
        node.destroy_node()
        rclpy.try_shutdown()
    return 0


if __name__ == '__main__':
    sys.exit(main())
