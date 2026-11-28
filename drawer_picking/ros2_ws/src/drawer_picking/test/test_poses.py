from drawer_picking import poses


def test_default_poses_are_complete_and_within_limits():
    assert poses.problems(poses.DEFAULT_POSES) == []


def test_pose_names_follow_the_cycle():
    names = poses.pose_names()
    assert names == ['home', 'drawer_1_approach', 'drawer_2_approach',
                     'drawer_3_approach', 'drawer_4_approach', 'dropoff']


def test_real_mode_uses_only_taught_poses(tmp_path):
    path = str(tmp_path / 'real.yaml')
    assert len(poses.problems(poses.load('real', path))) == 6       # nothing taught yet
    for name in poses.pose_names():
        poses.save(path, name, poses.DEFAULT_POSES[name])
    assert poses.problems(poses.load('real', path)) == []
    assert (tmp_path / 'real.yaml.bak').exists()


def test_sim_mode_file_overrides_defaults(tmp_path):
    path = str(tmp_path / 'sim.yaml')
    poses.save(path, 'drawer_1_approach', [0.1] * 6)
    loaded = poses.load('sim', path)
    assert loaded['drawer_1_approach'] == [0.1] * 6
    assert loaded['drawer_2_approach'] == poses.DEFAULT_POSES['drawer_2_approach']


def test_out_of_range_joint_is_reported():
    bad = dict(poses.DEFAULT_POSES, home=[0, 0, 0, 0, 0, 3.5])
    assert any('home: joint6' in p for p in poses.problems(bad))


def test_big_swing_near_cabinet_is_warned():
    p = dict(poses.DEFAULT_POSES)
    p['home'] = list(p['drawer_1_approach'])
    assert not any('drawer_1' in w for w in poses.warnings(p))
    p['home'][4] += 2.0
    assert any('drawer_1_approach' in w for w in poses.warnings(p))
