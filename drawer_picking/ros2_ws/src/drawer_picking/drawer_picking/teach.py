"""drawer_teach: configuration stage. Only saves poses; it never moves the arm.

Order: home, safe, drawer_1..4_pick, dropoff. Put the arm in the pose
(simulation: gimbal in RViz + Plan & Execute; real robot: [r] and move it by
hand) and press Enter.

For each drawer pick, Enter also stores the approach pose: --retreat
m (default 0.08) straight back along the cup axis, or as far as reachable
down to --min-retreat (default 0.03). The state machine then
does the motion: straight in along the cup axis, suction, straight back out.
The dropoff has no approach: the arm goes there with a free move.

Keys: Enter save | r release servos (real robot, HOLD THE ARM) | n skip | b back | q quit

Usage: ros2 run drawer_picking drawer_teach --mode sim|real [--retreat 0.08] [pose names or 1-4 ...]
  e.g. "2" teaches only drawer 2; "dropoff" only the dropoff point; "safe".
"""
import argparse
import sys
import time

import rclpy

from drawer_picking import poses
from drawer_picking.keyboard import Keyboard
from drawer_picking.robot import Robot

HELP = {
    'home': 'Initial / rest pose: arm clear of the cabinet and of the dropoff point.',
    'safe': 'Safe pose in front of the cabinet, well clear of it. Every trip to a drawer '
            'passes here. Keep the wrist about as it will be at the drawers.',
    'dropoff': 'Cup where the item is released (reached with a free move, no straight line).',
}
for d in poses.DRAWERS:
    HELP[f'drawer_{d}_pick'] = (
        f'Cup touching the item in drawer {d}, cup axis pointing the way the arm must go in. '
        'The state machine enters and leaves along that axis and turns the suction on here.')


MOVE_HINT = {
    'sim': 'In RViz: drag the gimbal, then Plan & Execute (or set the joints in the '
           'MotionPlanning "Joints" tab) and wait for the arm to get there.',
    'real': 'Press [r], move the arm by hand, then Enter.',
}
RETREAT_HINT = ('Usual causes: the arm is stretched out (e.g. at home, straight up) or a joint '
                'is near its limit. Bend the arm more (elbow and wrist), keep the cup pointing '
                'the way it must go in, and try again.')


def fmt(joints):
    return '[' + ', '.join(f'{v:+.3f}' for v in joints) + ']' if joints else '(not saved)'


def selected_poses(tokens):
    """'2' -> drawer 2 pick, 'dropoff' -> dropoff, else exact names."""
    valid = poses.taught_names()
    if not tokens:
        return valid
    chosen = [f'drawer_{t}_pick' if t.isdigit() else t for t in tokens]
    unknown = set(chosen) - set(valid)
    if unknown:
        sys.exit(f'Unknown pose(s): {sorted(unknown)}. Valid: {valid} or 1-4')
    return [n for n in valid if n in chosen]


def same_as(joints, saved, name):
    """Name of another saved pose at the same joints (the arm did not move), or None."""
    for other, value in saved.items():
        if other != name and other not in poses.APPROACH_OF.values() and \
                max(abs(a - b) for a, b in zip(joints, value)) < 0.01:
            return other
    return None


def teach(robot, mode, steps, retreat, min_retreat):
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
                        approach = poses.APPROACH_OF.get(name)
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
                            if approach:
                                back, used = robot.retreat(joints, retreat, min_retreat)
                                poses.save(path, approach, back)
                            poses.save(path, name, joints)
                        except RuntimeError as err:
                            print(f'  NOT saved: {err}.')
                            if approach:
                                print(f'  {RETREAT_HINT}')
                            continue
                        print(f'  saved {name} = {fmt(joints)}')
                        if approach:
                            short = ('' if used >= retreat - 1e-3
                                     else f' (not {retreat * 100:.0f}: that is as far as it goes)')
                            print(f'  saved {approach}: {used * 100:.1f} cm straight back along the cup axis{short}')
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
    parser.add_argument('--retreat', type=float, default=poses.RETREAT,
                        help='m from each drawer pick back to its approach, along the cup axis')
    parser.add_argument('--min-retreat', type=float, default=0.03,
                        help='accept a shorter approach (as far as reachable) down to this, m')
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
        teach(robot, args.mode, steps, args.retreat, args.min_retreat)
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
