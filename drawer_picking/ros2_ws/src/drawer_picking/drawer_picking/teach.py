"""drawer_teach: configuration stage. Only saves poses; it never moves the arm.

Order: home, drawer_1..4_approach, dropoff. Put the arm in the pose
(simulation: gimbal in RViz + Plan & Execute; real robot: [r] and move it by
hand) and press Enter. Enter always saves.

Each drawer has ONE pose: the cup --reach m (default 0.08) in front of the
item, pointing at it. The state machine does the rest: straight in along the
cup axis by --reach, suction, straight back out to this pose. After saving a
drawer pose the wizard checks that line and warns if it is not possible
(the pose is kept; move the arm and press Enter again to replace it).
The dropoff has no straight line: the arm goes there with a free move.

Keys: Enter save | r release servos (real robot, HOLD THE ARM) | n skip | b back | q quit

Usage: ros2 run drawer_picking drawer_teach --mode sim|real [--reach 0.08] [pose names or 1-4 ...]
  e.g. "2" teaches only drawer 2; "dropoff" only the dropoff point; "home".
"""
import argparse
import sys
import time

import rclpy

from drawer_picking import poses
from drawer_picking.keyboard import Keyboard
from drawer_picking.robot import Robot

HELP = {
    'home': 'Initial and safe pose, in front of the cabinet and well clear of it. Every trip '
            'to a drawer starts and ends here. Keep the wrist about as it will be at the drawers.',
    'dropoff': 'Cup where the item is released (reached with a free move, no straight line).',
}
for d in poses.DRAWERS:
    HELP[f'drawer_{d}_approach'] = (
        f'Cup in front of the item in drawer {d}, at the reach distance, cup axis pointing at it '
        '(the way the arm must go in). The state machine goes straight in along that axis, '
        'turns the suction on and comes straight back here.')


MOVE_HINT = {
    'sim': 'In RViz: drag the gimbal, then Plan & Execute (or set the joints in the '
           'MotionPlanning "Joints" tab) and wait for the arm to get there.',
    'real': 'Press [r], move the arm by hand, then Enter.',
}
REACH_HINT = ('Keep the elbow and wrist bent (a stretched arm cannot go further forward), '
              'keep joints away from their limits and the cup pointing at the item, and Enter again; or [n] to keep this pose and go on.')


def fmt(joints):
    return '[' + ', '.join(f'{v:+.3f}' for v in joints) + ']' if joints else '(not saved)'


def selected_poses(tokens):
    """'2' -> drawer 2 pose, 'dropoff' -> dropoff, else exact names."""
    valid = poses.pose_names()
    if not tokens:
        return valid
    chosen = [f'drawer_{t}_approach' if t.isdigit() else t for t in tokens]
    unknown = set(chosen) - set(valid)
    if unknown:
        sys.exit(f'Unknown pose(s): {sorted(unknown)}. Valid: {valid} or 1-4')
    return [n for n in valid if n in chosen]


def same_as(joints, saved, name):
    """Name of another saved pose at the same joints (the arm did not move), or None."""
    for other, value in saved.items():
        if other != name and other in poses.pose_names() and \
                max(abs(a - b) for a, b in zip(joints, value)) < 0.01:
            return other
    return None


def teach(robot, mode, steps, reach):
    path = poses.POSE_FILES[mode]
    released = False
    confirm = None          # pose waiting for a second Enter (arm did not move)
    keys = '[Enter] save  ' + ('[r] release servos  ' if mode == 'real' else '') + '[n] skip  [b] back  [q] quit'

    i = 0
    with Keyboard() as kb:
        try:
            while i < len(steps):
                name = steps[i]
                print(f'\n--- {i + 1}/{len(steps)}: {name} ---\n  {HELP[name]}')
                print(f'  saved: {fmt(poses.load(mode).get(name))}\n  {keys}')
                while True:
                    key = kb.get()
                    if key is None:
                        continue
                    if key in '\r\n':
                        time.sleep(0.5)                  # let the readings settle
                        joints = list(robot.joints)
                        same = same_as(joints, poses.load(mode), name)
                        if same and confirm != name:
                            confirm = name
                            print(f'  The arm is exactly where {same} is: it has not moved. '
                                  f'{MOVE_HINT[mode]} Press Enter again to save it anyway.')
                            continue
                        confirm = None
                        try:
                            if released:
                                robot.call('lock_servos')
                                released = False
                        except RuntimeError as err:
                            print(f'  warning: {err}')
                        poses.save(path, name, joints)
                        print(f'  saved {name} = {fmt(joints)}')
                        if name.startswith('drawer_'):
                            try:
                                why = robot.check_forward(joints, reach)
                            except RuntimeError as err:
                                why = str(err)
                            if why:
                                print(f'  WARNING: the {reach * 100:.0f} cm straight line forward along the '
                                      f'cup axis is not possible from here: {why}.\n'
                                      f'  The cycle would stop at this drawer. {REACH_HINT}')
                                continue
                            print(f'  OK: {reach * 100:.0f} cm straight forward along the cup axis is reachable.')
                        i += 1
                    elif key == 'r' and mode == 'real':
                        print('  HOLD THE ARM - releasing servos in 2 s...')
                        time.sleep(2.0)
                        try:
                            robot.call('release_servos')
                            released = True
                        except RuntimeError as err:
                            print(f'  error: {err}')
                        continue
                    elif key == 'n':
                        i += 1
                    elif key == 'b':
                        i = max(0, i - 1)
                    elif key == 'q':
                        return
                    else:
                        continue
                    break
        finally:
            if released:
                robot.call('lock_servos')


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--mode', choices=['sim', 'real'], default='real')
    parser.add_argument('--reach', type=float, default=poses.REACH,
                        help='m from each drawer pose forward to the item, along the cup axis (check only)')
    parser.add_argument('only', nargs='*', help='poses to teach: names, drawer numbers or "dropoff"')
    args, ros_args = parser.parse_known_args()
    steps = selected_poses(args.only)

    rclpy.init(args=ros_args)
    node = rclpy.create_node('drawer_teach')
    robot = Robot(node)
    try:
        robot.wait_ready()
        how = ('press [r], move the arm by hand, then Enter' if args.mode == 'real'
               else 'drag the gimbal in RViz, Plan & Execute, then Enter')
        print(f'\nTEACH ({args.mode}): {len(steps)} pose(s). For each one: {how}.')
        teach(robot, args.mode, steps, args.reach)
        taught = poses.load(args.mode)
        for warning in poses.warnings(taught):
            print(f'\nWARNING: {warning}')
        missing = poses.problems(taught)
        if missing:
            print('\nStill missing:\n  ' + '\n  '.join(missing))
        else:
            print(f'\nAll poses ready. Run: ./scripts/RUN_STATE_MACHINE.sh {args.mode}')
    except (RuntimeError, KeyboardInterrupt) as err:
        node.get_logger().error(str(err) or 'interrupted')
    finally:
        robot.shutdown()
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
