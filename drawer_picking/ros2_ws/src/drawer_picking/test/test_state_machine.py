"""State machine logic with a fake robot (no ROS needed).

Run: cd drawer_picking/ros2_ws/src/drawer_picking && python3 -m pytest test -q
"""
import pytest

from drawer_picking.poses import DEFAULT_POSES
from drawer_picking.state_machine import DrawerStateMachine


class FakeRobot:
    """Logs moves as 'name' (free), '~name' (straight line to a pose) or '>label 8cm'
    (straight line forward). Fails once at `fail_on`.

    fail_on: a log entry ('dropoff', '>drawer_2_item 8cm', 'pump_on'...);
    nth: fail at its nth occurrence (1 = first).
    """

    def __init__(self, fail_on=None, nth=1):
        self.log = []
        self.fail_on, self.nth = fail_on, nth

    def _do(self, entry):
        if entry == self.fail_on:
            self.nth -= 1
            if self.nth == 0:
                self.fail_on = None
                raise RuntimeError(f'simulated failure at {entry}')
        self.log.append(entry)

    def move(self, name, joints):
        self._do(name)

    def linear(self, name, joints):
        self._do('~' + name)

    def forward(self, label, distance):
        self._do(f'>{label} {distance * 100:.0f}cm')

    def pump(self, on):
        self._do('pump_on' if on else 'pump_off')


def make(robot=None):
    states = []
    sm = DrawerStateMachine(robot or FakeRobot(), DEFAULT_POSES, settle=0,
                            on_state=states.append, sleep=lambda s: None)
    return sm, states


def test_cycle_order():
    sm, states = make()
    assert sm.run_cycle(2)
    assert sm.robot.log == [
        'home', 'drawer_2_approach', '>drawer_2_item 8cm', 'pump_on', '~drawer_2_approach', 'home',
        'dropoff', 'pump_off', 'home']
    assert states[0] == 'GO_HOME (drawer 2)' and states[-1] == 'IDLE'


def test_drawer_in_and_out_are_straight_lines():
    sm, _ = make()
    sm.run_cycle(1)
    log = sm.robot.log
    i = log.index('>drawer_1_item 8cm')
    assert log[i - 1] == 'drawer_1_approach' and log[i + 2] == '~drawer_1_approach'
    assert log[i - 2] == 'home' and log[i + 3] == 'home', 'goes through home both ways'


@pytest.mark.parametrize('drawer', [1, 2, 3, 4])
def test_each_drawer_uses_its_own_poses(drawer):
    sm, _ = make()
    assert sm.run_cycle(drawer)
    assert f'>drawer_{drawer}_item 8cm' in sm.robot.log
    assert f'~drawer_{drawer}_approach' in sm.robot.log, 'back to the same single pose'


def test_reach_distance_is_configurable():
    sm, _ = make()
    sm.reach = 0.05
    assert sm.run_cycle(3)
    assert '>drawer_3_item 5cm' in sm.robot.log


def test_repeated_cycles():
    sm, _ = make()
    for d in (1, 3, 1, 4, 2):
        assert sm.run_cycle(d)
    assert sm.cycles_done == 5 and sm.robot.log.count('pump_on') == 5


def test_refuses_invalid_drawer_or_busy():
    sm, _ = make()
    assert not sm.run_cycle(5)
    sm.state = 'APPROACH (drawer 1)'
    assert not sm.run_cycle(1)
    assert sm.robot.log == []


def test_failure_entering_drawer_backs_out_straight_then_home():
    sm, states = make(FakeRobot(fail_on='>drawer_3_item 8cm'))
    assert not sm.run_cycle(3)
    assert any(s.startswith('ERROR') for s in states)
    assert 'pump_on' not in sm.robot.log
    assert sm.robot.log[-2:] == ['~drawer_3_approach', 'home']
    assert sm.back_out is None and not sm.near_cabinet and sm.state == 'IDLE'


def test_failure_leaving_drawer_with_item_backs_out_then_drops():
    sm, _ = make(FakeRobot(fail_on='~drawer_2_approach'))
    assert not sm.run_cycle(2)
    assert sm.robot.log[-5:] == ['~drawer_2_approach', 'home', 'dropoff', 'pump_off', 'home']
    assert not sm.holding
    assert sm.run_cycle(2), 'accepts a new cycle after recovering'


def test_failure_on_suction_backs_out_of_drawer():
    sm, _ = make(FakeRobot(fail_on='pump_on'))
    assert not sm.run_cycle(4)
    assert sm.robot.log[-2:] == ['~drawer_4_approach', 'home']


def test_failure_near_cabinet_goes_home():
    sm, _ = make(FakeRobot(fail_on='drawer_1_approach'))
    assert not sm.run_cycle(1)
    assert sm.robot.log == ['home', 'home']


def test_dropoff_is_a_free_move():
    sm, _ = make()
    sm.run_cycle(1)
    assert 'dropoff' in sm.robot.log and '~dropoff' not in sm.robot.log


def test_failure_on_release_retries_at_the_dropoff():
    sm, _ = make(FakeRobot(fail_on='pump_off'))
    assert not sm.run_cycle(1)
    tail = sm.robot.log[sm.robot.log.index('dropoff') + 1:]
    assert tail == ['dropoff', 'pump_off', 'home']
    assert tail.count('home') == 1, 'the dropoff is not near the cabinet'


def test_failed_recovery_turns_pump_off():
    class Broken(FakeRobot):
        def move(self, name, joints):
            if name == 'dropoff':
                raise RuntimeError('stuck')
            super().move(name, joints)

    sm, states = make(Broken())
    assert not sm.run_cycle(1)
    assert 'recovery failed' in states[-2] and sm.robot.log[-1] == 'pump_off'
    assert not sm.holding and sm.state == 'IDLE'
