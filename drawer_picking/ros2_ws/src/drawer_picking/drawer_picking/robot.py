"""The arm, through MoveIt 2 and the services of cobot's mycobot_bridge.

The same code drives the simulation (bridge with mock:=true on the PC) and
the real robot (bridge on the Jetson Nano).
  /move_action              MoveGroup action: free joint-space move to a pose
  /compute_cartesian_path   straight-line path of the suction cup (pump_tcp)
  /execute_trajectory       runs that straight-line path
  /compute_fk               cup position/orientation of a joint pose
  /check_state_validity     is a joint pose in collision (teach error messages)
  /pump_on, /pump_off       suction pump (std_srvs/Trigger)
  /release_servos, /lock_servos   hand-guiding for teaching

Two kinds of motion:
  move()    free move (planner chooses the path). Only between poses that are
            clear of the cabinet: home, safe, the approach poses, dropoff.
  linear()  the cup tip goes in a straight line along its own axis, the axis
            keeps pointing the same way (only roll about it may change), at
            low speed. Used to go in and out of a drawer.
            The path is checked before moving; if it
            is not a straight line along the cup axis, nothing moves.
"""
import math
import threading
import time

from geometry_msgs.msg import Pose
from moveit_msgs.action import ExecuteTrajectory, MoveGroup
from moveit_msgs.msg import Constraints, JointConstraint, RobotState
from moveit_msgs.srv import GetCartesianPath, GetPositionFK, GetStateValidity
from rclpy.action import ActionClient
from rclpy.executors import MultiThreadedExecutor
from sensor_msgs.msg import JointState
from std_srvs.srv import Trigger

from drawer_picking.poses import JOINT_NAMES

GROUP = 'mycobot_arm'
BASE = 'mycobot_base_link'
TCP = 'pump_tcp'                # suction cup tip; its +z axis comes out of the cup
AXIS_TOLERANCE_DEG = 5.0        # straight-line move must be this close to the cup axis
TILT_TOLERANCE_DEG = 5.0        # and keep the cup pointing the same way (roll about it is free)
MAX_JOINT_STEP = 0.2            # rad between path points; more = IK flip, refuse


def wait(future, timeout):
    """Wait for a future (filled by the background executor). None on timeout."""
    end = time.time() + timeout
    while not future.done():
        if time.time() > end:
            return None
        time.sleep(0.02)
    return future.result()


# --- small vector / quaternion helpers (x, y, z, w) -------------------------

def cup_axis(q):
    """+z axis of a frame with orientation q, i.e. the direction the cup points."""
    x, y, z, w = q
    return (2 * (x * z + w * y), 2 * (y * z - w * x), 1 - 2 * (x * x + y * y))


def tilt_deg(q1, q2):
    """Angle between the cup axes of two orientations, degrees (roll about the axis ignored)."""
    dot = sum(a * b for a, b in zip(cup_axis(q1), cup_axis(q2)))
    return math.degrees(math.acos(max(-1.0, min(1.0, dot))))


def angle_to_axis_deg(vector, axis):
    """Angle between a vector and the line of an axis (either direction), degrees."""
    norm = math.sqrt(sum(v * v for v in vector))
    cos = abs(sum(v * a for v, a in zip(vector, axis))) / norm
    return math.degrees(math.acos(min(1.0, cos)))


def check_straight(start, goal):
    """Raise if start -> goal is not a straight move along the cup axis.

    start, goal: (position, quaternion) of the cup. Returns the distance (m).
    """
    (p0, q0), (p1, q1) = start, goal
    delta = [b - a for a, b in zip(p0, p1)]
    dist = math.sqrt(sum(d * d for d in delta))
    tilt = tilt_deg(q0, q1)
    if tilt > TILT_TOLERANCE_DEG:
        raise RuntimeError(f'cup axis tilts {tilt:.1f} deg on the way (max {TILT_TOLERANCE_DEG})')
    if dist > 0.005:
        off = angle_to_axis_deg(delta, cup_axis(q0))
        if off > AXIS_TOLERANCE_DEG:
            raise RuntimeError(f'path is {off:.1f} deg off the cup axis (max {AXIS_TOLERANCE_DEG})')
    return dist


def retime(traj, duration):
    """Stretch a JointTrajectory so it lasts at least `duration` seconds."""
    if not traj.points:
        return traj
    last = traj.points[-1].time_from_start
    t0 = last.sec + last.nanosec * 1e-9
    if t0 <= 0.0:                                   # no timing: spread evenly
        n = len(traj.points)
        times = [duration * (i + 1) / n for i in range(n)]
        for point, t in zip(traj.points, times):
            point.time_from_start.sec, point.time_from_start.nanosec = int(t), int((t % 1) * 1e9)
            point.velocities, point.accelerations = [], []
        return traj
    k = max(1.0, duration / t0)
    for point in traj.points:
        t = (point.time_from_start.sec + point.time_from_start.nanosec * 1e-9) * k
        point.time_from_start.sec, point.time_from_start.nanosec = int(t), int((t % 1) * 1e9)
        point.velocities = [v / k for v in point.velocities]
        point.accelerations = [a / (k * k) for a in point.accelerations]
    return traj


class Robot:
    def __init__(self, node, speed=0.2, linear_speed=0.02):
        self.node = node
        self.speed = speed                  # MoveIt velocity/acceleration scaling, 0-1
        self.linear_speed = linear_speed    # cup speed in straight-line moves, m/s
        self.joints = None                  # latest /joint_states, in JOINT_NAMES order
        self.move_client = ActionClient(node, MoveGroup, '/move_action')
        self.exec_client = ActionClient(node, ExecuteTrajectory, '/execute_trajectory')
        self.cartesian = node.create_client(GetCartesianPath, '/compute_cartesian_path')
        self.fk_client = node.create_client(GetPositionFK, '/compute_fk')
        self.validity = node.create_client(GetStateValidity, '/check_state_validity')
        self.services = {name: node.create_client(Trigger, '/' + name)
                         for name in ('pump_on', 'pump_off', 'release_servos', 'lock_servos')}
        node.create_subscription(JointState, '/joint_states', self._on_joints, 10)
        # Spin in the background so the main thread can block on user input.
        self.executor = MultiThreadedExecutor()
        self.executor.add_node(node)
        self.thread = threading.Thread(target=self.executor.spin, daemon=True)
        self.thread.start()

    def _on_joints(self, msg):
        if set(JOINT_NAMES) <= set(msg.name):
            self.joints = [msg.position[msg.name.index(n)] for n in JOINT_NAMES]

    def wait_ready(self, timeout=20.0):
        end = time.time() + timeout
        for client, what in ((self.move_client, '/move_action'), (self.exec_client, '/execute_trajectory')):
            while not client.wait_for_server(timeout_sec=1.0):
                if time.time() > end:
                    raise RuntimeError(f'MoveIt ({what}) not found. Is RUN_SIM.sh / RUN_REAL.sh running?')
        for client in (self.cartesian, self.fk_client):
            if not client.wait_for_service(timeout_sec=max(1.0, end - time.time())):
                raise RuntimeError(f'MoveIt ({client.srv_name}) not found. Is RUN_SIM.sh / RUN_REAL.sh running?')
        while self.joints is None:
            if time.time() > end:
                raise RuntimeError('No /joint_states. Is mycobot_bridge (mock or Nano) running?')
            time.sleep(0.1)

    def shutdown(self):
        self.executor.shutdown(timeout_sec=1.0)   # stop spinning before destroying clients
        self.thread.join(timeout=2.0)
        self.move_client.destroy()
        self.exec_client.destroy()

    # --- free move ---------------------------------------------------------

    def move(self, name, joints, timeout=60.0):
        """Free joint-space move (planner chooses the path). Raises RuntimeError on failure."""
        self.node.get_logger().info(f'-> {name}')
        goal = MoveGroup.Goal()
        req = goal.request
        req.group_name = GROUP
        req.allowed_planning_time = 5.0
        req.num_planning_attempts = 5
        req.max_velocity_scaling_factor = self.speed
        req.max_acceleration_scaling_factor = self.speed
        req.start_state.is_diff = True
        target = Constraints()
        for joint_name, position in zip(JOINT_NAMES, joints):
            target.joint_constraints.append(JointConstraint(
                joint_name=joint_name, position=float(position),
                tolerance_above=0.01, tolerance_below=0.01, weight=1.0))
        req.goal_constraints = [target]
        goal.planning_options.plan_only = False

        handle = wait(self.move_client.send_goal_async(goal), 10.0)
        if handle is None or not handle.accepted:
            raise RuntimeError(f'MoveIt rejected the goal {name}')
        result = wait(handle.get_result_async(), timeout)
        if result is None:
            raise RuntimeError(f'timeout moving to {name}')
        if result.result.error_code.val != 1:
            raise RuntimeError(f'could not reach {name} (MoveIt error {result.result.error_code.val})')
        self.wait_arrival(name, joints)

    # --- straight-line move ------------------------------------------------

    def fk(self, joints):
        """(position, quaternion) of the cup for a joint pose."""
        req = GetPositionFK.Request()
        req.header.frame_id = BASE
        req.fk_link_names = [TCP]
        req.robot_state.joint_state = JointState(name=JOINT_NAMES, position=[float(v) for v in joints])
        res = wait(self.fk_client.call_async(req), 5.0)
        if res is None or res.error_code.val != 1 or not res.pose_stamped:
            raise RuntimeError('forward kinematics failed (/compute_fk)')
        p = res.pose_stamped[0].pose
        return ((p.position.x, p.position.y, p.position.z),
                (p.orientation.x, p.orientation.y, p.orientation.z, p.orientation.w))

    def straight_path(self, start_joints, position, quaternion, min_fraction=0.999):
        """Straight cup path from start_joints to a cup pose.

        Returns (solution, end joints, reachable fraction). Raises if less than
        min_fraction of the line is reachable or if it needs a joint flip.
        """
        req = GetCartesianPath.Request()
        req.header.frame_id = BASE
        req.group_name = GROUP
        req.link_name = TCP
        req.start_state = RobotState(joint_state=JointState(
            name=JOINT_NAMES, position=[float(v) for v in start_joints]))
        target = Pose()
        target.position.x, target.position.y, target.position.z = position
        (target.orientation.x, target.orientation.y,
         target.orientation.z, target.orientation.w) = quaternion
        req.waypoints = [target]
        req.max_step = 0.005                  # one IK point every 5 mm
        req.jump_threshold = 0.0
        req.revolute_jump_threshold = MAX_JOINT_STEP
        req.avoid_collisions = True
        res = wait(self.cartesian.call_async(req), 10.0)
        if res is None or res.error_code.val != 1:
            raise RuntimeError('straight-line planning failed (/compute_cartesian_path)')
        if res.fraction < min_fraction:
            raise RuntimeError(f'only {res.fraction * 100:.0f}% of the straight line is reachable')
        traj = res.solution.joint_trajectory
        order = [traj.joint_names.index(n) for n in JOINT_NAMES]
        prev = list(start_joints)
        for point in traj.points:
            now = [point.positions[i] for i in order]
            if max(abs(a - b) for a, b in zip(now, prev)) > MAX_JOINT_STEP:
                raise RuntimeError('straight line needs a joint flip (near a singularity)')
            prev = now
        return res.solution, prev, res.fraction

    def linear(self, name, joints, timeout=60.0):
        """Straight-line cup move from the current position to a joint pose.

        The line must follow the cup axis, without tilting it (checked
        before moving). Speed: self.linear_speed m/s. Raises RuntimeError.
        """
        start = list(self.joints)
        position, quaternion = goal_pose = self.fk(joints)
        dist = check_straight(self.fk(start), goal_pose)
        if dist < 0.001:
            return                            # already there
        self.node.get_logger().info(f'-> {name} (straight line, {dist * 100:.1f} cm)')
        solution, end, _ = self.straight_path(start, position, quaternion)
        retime(solution.joint_trajectory, dist / self.linear_speed)

        goal = ExecuteTrajectory.Goal(trajectory=solution)
        handle = wait(self.exec_client.send_goal_async(goal), 10.0)
        if handle is None or not handle.accepted:
            raise RuntimeError(f'MoveIt rejected the straight line to {name}')
        result = wait(handle.get_result_async(), timeout)
        if result is None:
            raise RuntimeError(f'timeout on the straight line to {name}')
        if result.result.error_code.val != 1:
            raise RuntimeError(f'straight line to {name} failed (MoveIt error {result.result.error_code.val})')
        self.wait_arrival(name, end)      # end of the line (same cup pose as `joints`)

    def retreat(self, joints, distance, minimum=0.0):
        """Joint pose straight back from `joints` along the cup axis.

        Used by the teach wizard: the approach pose of a drawer pick.
        Goes back `distance` m, or as far as reachable if that is at least
        `minimum` m. Returns (joints, distance used). Raises RuntimeError if
        less than `minimum` (or, with minimum=0, less than all of it) is reachable.
        """
        position, quaternion = self.fk(joints)
        axis = cup_axis(quaternion)
        back = tuple(p - distance * a for p, a in zip(position, axis))
        need = minimum / distance if minimum else 0.999
        try:
            _, end, fraction = self.straight_path(joints, back, quaternion, min_fraction=need)
        except RuntimeError as err:
            contact = self.collision(joints)
            why = f'the pose is in collision: {contact}' if contact else str(err)
            raise RuntimeError(f'cannot back out {minimum * 100 if minimum else distance * 100:.0f} cm in a '
                               f'straight line along the cup axis ({why})') from None
        return end, distance * min(1.0, fraction)

    def collision(self, joints):
        """'link_a touches link_b' if the joint pose is in collision, else None."""
        if not self.validity.wait_for_service(timeout_sec=2.0):
            return None
        req = GetStateValidity.Request()
        req.group_name = GROUP
        req.robot_state = RobotState(joint_state=JointState(name=JOINT_NAMES, position=[float(v) for v in joints]))
        res = wait(self.validity.call_async(req), 5.0)
        if res is None or res.valid:
            return None
        if res.contacts:
            return f'{res.contacts[0].contact_body_1} touches {res.contacts[0].contact_body_2}'
        return 'invalid state'

    # --- arrival, services ---------------------------------------------------

    def wait_arrival(self, name, joints, tol=0.05, timeout=10.0):
        """Wait until /joint_states reaches the target.

        cobot's mycobot_bridge reports success as soon as it has sent the last
        trajectory point, while the real arm is still moving. Without this the
        pump could switch before the arm arrives, and the next plan could start
        from a stale state.
        """
        end = time.time() + timeout
        err = float('inf')
        while time.time() < end:
            if self.joints is not None:
                err = max(abs(a - float(b)) for a, b in zip(self.joints, joints))
                if err <= tol:
                    return
            time.sleep(0.1)
        self.node.get_logger().warn(f'{name}: arm still {err:.3f} rad from the target after {timeout:.0f} s')

    def call(self, service, timeout=5.0):
        """Call a Trigger service of the bridge. Raises RuntimeError on failure."""
        client = self.services[service]
        if not client.wait_for_service(timeout_sec=2.0):
            raise RuntimeError(f'/{service} not available. Is mycobot_bridge running?')
        res = wait(client.call_async(Trigger.Request()), timeout)
        if res is None or not res.success:
            raise RuntimeError(f'/{service} failed: {res.message if res else "timeout"}')
        self.node.get_logger().info(f'/{service}: {res.message}')

    def pump(self, on):
        self.call('pump_on' if on else 'pump_off')
