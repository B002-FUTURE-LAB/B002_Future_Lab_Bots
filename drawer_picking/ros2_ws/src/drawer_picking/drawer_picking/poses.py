"""Named joint poses used by the drawer cycle.

Two modes:
  sim  - DEFAULT_POSES below (example cell) + overrides from drawer_poses_sim.yaml
  real - ONLY poses taught with scripts/TEACH.sh (drawer_poses_real.yaml).
         No fallback to the simulation poses.

Joint order: joint1..joint6, radians.

All taught by hand: home, drawer_N_approach, dropoff. home is the initial
and the safe pose: every trip to a drawer starts and ends there. Each drawer has
ONE pose (drawer_N_approach): the cup in front of the item, pointing at it.
From there the state machine goes REACH m forward in a straight line along
the cup axis, turns the suction on and comes back to the same pose along
the same line. The dropoff is reached with a free move (no straight line).
"""
import os
import shutil

import yaml

JOINT_NAMES = [
    'joint2_to_joint1', 'joint3_to_joint2', 'joint4_to_joint3',
    'joint5_to_joint4', 'joint6_to_joint5', 'joint6output_to_joint6',
]

# From cobot/.../mycobot_description/urdf/mycobot_280_jn/mycobot_280_jn.urdf.xacro
JOINT_LIMITS = [
    (-2.9321, 2.9321), (-2.4434, 2.4434), (-2.6179, 2.6179),
    (-2.6179, 2.6179), (-2.7052, 2.7925), (-3.14159, 3.14159),
]

DRAWERS = (1, 2, 3, 4)

REACH = 0.08   # m, straight line forward from drawer_N_approach to the item, along the cup axis

POSE_FILES = {
    'sim': '/root/drawer_config/drawer_poses_sim.yaml',
    'real': '/root/drawer_config/drawer_poses_real.yaml',
}

# Example cell (simulation): cabinet of drawer_cell.launch.py, the 4 central
# bins of its two upper rows. Seen from the robot: 1 upper-left,
# 2 upper-right, 3 lower-left, 4 lower-right. Computed with MoveIt IK.
# home (initial and safe pose): cup 13 cm in front of the base, pointing at the cabinet.
# The item is REACH m in front of each drawer pose, along the cup axis.
DEFAULT_POSES = {
    'home': [-0.0142, -2.1008, 1.521, 1.3831, 1.0571, 0.0205],
    'drawer_1_approach': [0.9152, -1.7336, 1.8125, -1.4751, -2.4366, 2.0186],
    'drawer_2_approach': [-0.2007, -0.4694, -0.3141, -1.4724, 2.4829, -2.9624],
    'drawer_3_approach': [0.2857, -2.2678, 1.8266, -1.12, 1.1229, -2.5429],
    'drawer_4_approach': [-0.2970, -0.7211, -1.3365, -0.0842, 1.8725, -2.6267],
    'dropoff': [1.5625, -1.4849, -1.0785, -0.5782, 2.0861, -3.0],
}


def pose_names():
    """All poses, in cycle order."""
    names = ['home']
    for d in DRAWERS:
        names.append(f'drawer_{d}_approach')
    return names + ['dropoff']


def read_file(path):
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    return {k: [float(v) for v in vals] for k, vals in data.items() if isinstance(vals, list)}


def load(mode, path=None):
    """Poses for a mode: defaults (sim only) updated with the YAML file."""
    poses = dict(DEFAULT_POSES) if mode == 'sim' else {}
    poses.update(read_file(path or POSE_FILES[mode]))
    return poses


def save(path, name, joints):
    """Write one pose to the YAML file (the previous file is kept as .bak)."""
    data = read_file(path)
    if os.path.exists(path):
        shutil.copyfile(path, path + '.bak')
    data[name] = [round(float(v), 4) for v in joints]
    with open(path, 'w') as f:
        f.write('# Drawer cell joint poses (radians, joint1..joint6). Written by TEACH.sh.\n')
        yaml.safe_dump(data, f, sort_keys=False)


def problems(poses):
    """List what is missing or invalid (empty list = ready to run)."""
    found = []
    for name in pose_names():
        joints = poses.get(name)
        if joints is None:
            found.append(f'{name}: missing')
        elif len(joints) != 6:
            found.append(f'{name}: needs 6 joints, has {len(joints)}')
        else:
            for i, (v, (lo, hi)) in enumerate(zip(joints, JOINT_LIMITS)):
                if not lo <= v <= hi:
                    found.append(f'{name}: joint{i + 1}={v:.3f} outside [{lo}, {hi}]')
    return found


BIG_SWING = 1.5   # rad; a free move near the cabinet turning a joint more than this is flagged


def warnings(poses):
    """Free moves near the cabinet (home <-> drawer approach) with a big joint swing."""
    found = []
    home = poses.get('home')
    for d in DRAWERS:
        approach = poses.get(f'drawer_{d}_approach')
        if home and approach:
            swing = max(abs(a - b) for a, b in zip(home, approach))
            if swing > BIG_SWING:
                found.append(f'home -> drawer_{d}_approach turns a joint {swing:.1f} rad: the arm '
                             'may sweep near the cabinet. Teach home and drawer poses with a similar wrist.')
    return found
