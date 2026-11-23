"""Drawer picking state machine. Pure logic: no ROS, easy to test.

Cycle for drawer N. "free" = planner chooses the path, only between poses
clear of the cabinet; "line" = cup in a straight line along its own axis.

  IDLE -> GO_SAFE (free) -> GO_DRAWER_APPROACH (free)
       -> ENTER_DRAWER (line) -> SUCTION_ON -> EXIT_DRAWER (line, back the same way)
       -> BACK_TO_SAFE (free) -> GO_DROPOFF (free) -> RELEASE
       -> RETURN_HOME (free) -> IDLE

On any error, only known-safe paths are used:
  ERROR -> if inside a drawer: straight line back out
        -> if near the cabinet: safe
        -> if the item is held: release it at the dropoff
        -> home -> IDLE

`robot` is any object with:
    move(pose_name, joints)     free move, raises an exception on failure
    linear(pose_name, joints)   straight-line move, raises an exception on failure
    pump(on)
"""
import time

# (state, action, pose or pump value). "{d}" becomes the drawer number.
CYCLE = [
    ('GO_SAFE', 'move', 'safe'),
    ('GO_DRAWER_APPROACH', 'move', 'drawer_{d}_approach'),
    ('ENTER_DRAWER', 'linear', 'drawer_{d}_pick'),
    ('SUCTION_ON', 'pump', True),
    ('EXIT_DRAWER', 'linear', 'drawer_{d}_approach'),
    ('BACK_TO_SAFE', 'move', 'safe'),
    ('GO_DROPOFF', 'move', 'dropoff'),
    ('RELEASE', 'pump', False),
    ('RETURN_HOME', 'move', 'home'),
]

# Where the arm is, for error recovery. Set when a state starts / cleared when it ends.
NEAR_CABINET_FROM, NEAR_CABINET_UNTIL = 'GO_DRAWER_APPROACH', 'BACK_TO_SAFE'
INSIDE = {   # state that goes in -> (state that comes out, pose to back out to)
    'ENTER_DRAWER': ('EXIT_DRAWER', 'drawer_{d}_approach'),
}
OUT_STATES = {out for out, _ in INSIDE.values()}


class DrawerStateMachine:
    def __init__(self, robot, poses, drawers=(1, 2, 3, 4), settle=1.0,
                 on_state=print, sleep=time.sleep):
        self.robot = robot
        self.poses = poses
        self.drawers = drawers
        self.settle = settle          # seconds to wait after switching the pump
        self.on_state = on_state      # called with the state name
        self.sleep = sleep
        self.state = 'IDLE'
        self.holding = False
        self.back_out = None          # pose to return to in a straight line (arm inside)
        self.near_cabinet = False     # between the safe pose and a drawer
        self.cycles_done = 0

    def _set(self, state):
        self.state = state
        self.on_state(state)

    def _move(self, name):
        self.robot.move(name, self.poses[name])

    def _linear(self, name):
        self.robot.linear(name, self.poses[name])

    def _pump(self, on):
        self.robot.pump(on)
        self.sleep(self.settle)
        self.holding = on

    def go_home(self):
        self._set('RETURN_HOME')
        self._move('home')
        self._set('IDLE')

    def run_cycle(self, drawer):
        """Run the full cycle. Returns True on success, False if refused or failed."""
        if self.state != 'IDLE' or drawer not in self.drawers:
            return False
        try:
            for state, action, arg in CYCLE:
                self._set(f'{state} (drawer {drawer})')
                if state == NEAR_CABINET_FROM:
                    self.near_cabinet = True
                if state in INSIDE:
                    self.back_out = INSIDE[state][1].format(d=drawer)
                if action == 'move':
                    self._move(arg.format(d=drawer))
                elif action == 'linear':
                    self._linear(arg.format(d=drawer))
                else:
                    self._pump(arg)
                if state in OUT_STATES:
                    self.back_out = None
                if state == NEAR_CABINET_UNTIL:
                    self.near_cabinet = False
            self.cycles_done += 1
            return True
        except Exception as err:  # noqa: BLE001 - any failure must end in a safe state
            self._recover(err)
            return False
        finally:
            self._set('IDLE')

    def _recover(self, err):
        self._set(f'ERROR: {err}')
        try:
            if self.back_out:                     # same straight line, reversed
                self._set(f'RECOVER: back out to {self.back_out}')
                self._linear(self.back_out)
                self.back_out = None
            if self.near_cabinet:
                self._set('RECOVER: safe')
                self._move('safe')
                self.near_cabinet = False
            if self.holding:
                self._set('RECOVER: release at the dropoff')
                self._move('dropoff')
                self._pump(False)
            self._set('RECOVER: home')
            self._move('home')
        except Exception as err2:  # noqa: BLE001
            self._set(f'ERROR: recovery failed ({err2}). Pump off; check the arm.')
            self.robot.pump(False)
            self.holding = False
            self.back_out = None
            self.near_cabinet = False
