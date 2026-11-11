import types
import unittest
from unittest.mock import patch

from backend.mission_readiness import mission_readiness
from backend.mission_signal_evidence import is_new_evidence, latest_matching_timestamp
from backend.api import cell_routes, cobot_routes, health_routes
from backend.config import settings
from backend.ros2_nodes import cobot_node


def ready_checks(*, undocked):
    return {
        "create3_alive": True,
        "create3_dock_action": True,
        "create3_undock_action": True,
        "undocked": undocked,
        "odom": True,
        "scan": False,
        "map": True,
        "amcl_pose": False,
        "navigate_to_pose": True,
        "global_costmap": True,
        "nav2_paused_standby": False,
        "start_delivery": True,
        "stop_mission": True,
    }


class MissionReadinessTest(unittest.TestCase):
    def test_docked_mission_does_not_require_sleeping_lidar_or_fresh_amcl(self):
        checks = ready_checks(undocked=False)
        # A Create 3 suspende odom->base_link na dock, da mesma forma que o
        # TurtleBot desliga o motor do RPLidar. A missão precisa poder chegar
        # ao seu próprio passo de undock sem falsificar esses sinais.
        checks["odom"] = False
        status = mission_readiness(checks)
        self.assertTrue(status["ready"])
        self.assertEqual("docked", status["start_mode"])
        self.assertNotIn("odom", status["required"])
        self.assertNotIn("scan", status["required"])
        self.assertNotIn("amcl_pose", status["required"])

    def test_undocked_mission_requires_fresh_navigation_inputs(self):
        status = mission_readiness(ready_checks(undocked=True))
        self.assertFalse(status["ready"])
        self.assertEqual("undocked", status["start_mode"])
        self.assertEqual(["scan", "amcl_pose"], status["missing"])

    def test_missing_mission_service_is_reported(self):
        checks = ready_checks(undocked=False)
        checks["start_delivery"] = False
        status = mission_readiness(checks)
        self.assertFalse(status["ready"])
        self.assertIn("start_delivery", status["missing"])

    def test_docked_paused_nav2_is_valid_only_for_a_mission(self):
        checks = ready_checks(undocked=False)
        checks["navigate_to_pose"] = False
        checks["global_costmap"] = False
        checks["nav2_paused_standby"] = True
        status = mission_readiness(checks)
        self.assertTrue(status["ready"])
        self.assertIn("nav2_paused_standby", status["required"])
        self.assertNotIn("navigate_to_pose", status["required"])
        self.assertIn("RESUME", status["hint"])


class MissionSignalEvidenceTest(unittest.TestCase):
    def test_selects_latest_matching_ros_timestamp(self):
        marker = "Tópico /product_class recebido"
        lines = [
            "[INFO] [10.1] [delivery_routine]: Tópico /product_class recebido: blue",
            "[WARN] [11.5] [other]: outra mensagem",
            "[INFO] [12.3] [delivery_routine]: Tópico /product_class recebido: red",
        ]
        self.assertEqual(12.3, latest_matching_timestamp(lines, marker))

    def test_old_matching_line_is_not_new_evidence(self):
        self.assertFalse(is_new_evidence(12.3, 12.3))
        self.assertFalse(is_new_evidence(12.2, 12.3))
        self.assertTrue(is_new_evidence(12.4, 12.3))

    def test_missing_marker_is_not_evidence(self):
        self.assertIsNone(latest_matching_timestamp(["sem marker"], "esperado"))
        self.assertFalse(is_new_evidence(None, None))


class SimulatedSignalPublisherTest(unittest.TestCase):
    def test_product_class_reports_publication(self):
        published = []
        node = types.SimpleNamespace(
            product_class_pub=types.SimpleNamespace(
                publish=lambda msg: published.append(msg.data)
            )
        )
        with patch.object(cobot_node, "String", type("String", (), {})):
            self.assertTrue(cobot_node.CobotNode.publish_product_class(node, "tin_valid_blue"))
        self.assertEqual(["tin_valid_blue"] * 3, published)

    def test_product_class_fails_when_publisher_is_missing(self):
        node = types.SimpleNamespace(product_class_pub=None)
        self.assertFalse(cobot_node.CobotNode.publish_product_class(node, "tin_valid_blue"))

    def test_item_release_reports_publication(self):
        published = []
        node = types.SimpleNamespace(
            item_released_pub=types.SimpleNamespace(
                publish=lambda msg: published.append(msg.data)
            )
        )
        with patch.object(cobot_node, "Bool", type("Bool", (), {})):
            self.assertTrue(cobot_node.CobotNode.publish_item_released(node))
        self.assertEqual([True] * 5, published)


class CobotMeasurementTest(unittest.TestCase):
    def test_joint_error_wraps_at_pi(self):
        error = cobot_node.CobotNode._joint_error(3.13, -3.13)
        self.assertLess(error, 0.03)

    def test_wait_does_not_clear_an_already_received_pickup(self):
        event = __import__("threading").Event()
        event.set()
        node = types.SimpleNamespace(tb4_at_pickup_event=event)
        self.assertTrue(
            cobot_node.CobotNode.wait_for_turtlebot_at_pickup(
                node, timeout_sec=0.01
            )
        )

    def test_verified_pose_retries_once_without_automatic_pump_side_effect(self):
        commands = []
        node = types.SimpleNamespace()
        node.goto_pose = lambda pose, speed, manage_pose_side_effects: commands.append(
            (pose, speed, manage_pose_side_effects)
        ) or True
        node.pose_is_reached = lambda *_args, **_kwargs: (True, 0.02, [0.0] * 6)
        moments = iter([0.0, 2.0, 3.0, 3.1, 3.2])
        with patch.object(cobot_node.time, "monotonic", side_effect=lambda: next(moments)), \
             patch.object(cobot_node.time, "sleep", return_value=None):
            reached = cobot_node.CobotNode.goto_pose_verified(
                node,
                "pick",
                velocity_scaling=0.15,
                timeout_sec=0.01,
                max_attempts=2,
            )

        self.assertTrue(reached)
        self.assertEqual(
            [("pick", 0.15, False), ("pick", 0.15, False)],
            commands,
        )


class HandshakeRollbackTest(unittest.TestCase):
    def test_failed_handshake_recovers_turtle_only_after_measured_dock(self):
        turtle = types.SimpleNamespace(is_docked=False)
        turtle.telemetry_fresh = lambda: True
        stops = []

        def dock():
            turtle.is_docked = True
            return {"status": "success"}

        evidence = cell_routes._recover_turtlebot_after_handshake_failure(
            turtle,
            lambda: stops.append(True) or {"status": "success"},
            dock,
            dock_confirm_sec=0.0,
        )

        self.assertEqual([True], stops)
        self.assertTrue(evidence["turtlebot_recovery"]["dock_status_measured"])
        self.assertEqual("docked", evidence["turtlebot_recovery"]["status"])


class RealIntegratedYoloTest(unittest.TestCase):
    def test_real_model_suffix_is_normalized_by_color(self):
        samples = [
            {"class": "tin_valid_red_triangle", "timestamp": 10.0 + index * 0.25}
            for index in range(5)
        ]
        self.assertEqual(
            ("tin_valid_red", "delivery_red"),
            cell_routes._stable_real_yolo_class(samples),
        )

    def test_duplicate_frame_timestamp_is_not_stable_evidence(self):
        samples = [
            {"class": "tin_valid_blue_square", "timestamp": 10.0},
            {"class": "tin_valid_blue_square", "timestamp": 10.0},
            {"class": "tin_valid_blue_square", "timestamp": 10.2},
            {"class": "tin_valid_blue_square", "timestamp": 10.4},
            {"class": "tin_valid_blue_square", "timestamp": 10.6},
        ]
        self.assertEqual((None, None), cell_routes._stable_real_yolo_class(samples))

    def test_mixed_colors_are_not_stable_evidence(self):
        samples = [
            {"class": "tin_valid_blue_square", "timestamp": 10.0},
            {"class": "tin_valid_red_triangle", "timestamp": 10.2},
            {"class": "tin_valid_blue_square", "timestamp": 10.4},
            {"class": "tin_valid_blue_square", "timestamp": 10.6},
            {"class": "tin_valid_blue_square", "timestamp": 10.8},
        ]
        self.assertEqual((None, None), cell_routes._stable_real_yolo_class(samples))

    def test_burst_too_short_is_not_temporal_evidence(self):
        samples = [
            {"class": "tin_valid_blue_square", "timestamp": 10.0 + index * 0.05}
            for index in range(5)
        ]
        self.assertEqual((None, None), cell_routes._stable_real_yolo_class(samples))

    def test_high_frame_rate_can_accumulate_the_required_time_span(self):
        samples = [
            {"class": "tin_valid_blue_square", "timestamp": 10.0 + index * 0.05}
            for index in range(19)
        ]
        self.assertEqual(
            ("tin_valid_blue", "delivery_blue"),
            cell_routes._stable_real_yolo_class(samples),
        )

    def test_invalid_class_is_rejected(self):
        with self.assertRaises(Exception):
            cell_routes._normalize_handshake_class("tin_invalid_red")

    def test_gui_yolo_keeps_requested_confidence_and_opens_window(self):
        fake_process = types.SimpleNamespace(pid=4242)
        fake_settings = types.SimpleNamespace(CAMERA_STREAM_URL="http://camera.test/stream")
        with patch.object(cobot_routes, "stop_yolo_test_process"), \
             patch.object(cobot_routes.Path, "exists", return_value=True), \
             patch.object(cobot_routes.subprocess, "run") as run_mock, \
             patch.object(cobot_routes.subprocess, "Popen", return_value=fake_process) as popen_mock, \
             patch.object(settings, "get_settings", return_value=fake_settings):
            self.assertTrue(cobot_routes.start_yolo_test_process(0.60, headless=False))

        shell_command = popen_mock.call_args.args[0][2]
        self.assertNotIn("--headless", shell_command)
        self.assertIn("--conf 0.6", shell_command)
        self.assertIn("export DISPLAY=", shell_command)
        run_mock.assert_called_once()
        if cobot_routes._yolo_log_file is not None:
            cobot_routes._yolo_log_file.close()
            cobot_routes._yolo_log_file = None
        cobot_routes.yolo_process = None
        cobot_routes.yolo_test_active = False

    def test_headless_yolo_keeps_requested_confidence_without_xhost(self):
        fake_process = types.SimpleNamespace(pid=4343)
        fake_settings = types.SimpleNamespace(CAMERA_STREAM_URL="http://camera.test/stream")
        with patch.object(cobot_routes, "stop_yolo_test_process"), \
             patch.object(cobot_routes.Path, "exists", return_value=True), \
             patch.object(cobot_routes.subprocess, "run") as run_mock, \
             patch.object(cobot_routes.subprocess, "Popen", return_value=fake_process) as popen_mock, \
             patch.object(settings, "get_settings", return_value=fake_settings):
            self.assertTrue(cobot_routes.start_yolo_test_process(0.72, headless=True))

        shell_command = popen_mock.call_args.args[0][2]
        self.assertIn("--headless", shell_command)
        self.assertIn("--conf 0.72", shell_command)
        run_mock.assert_not_called()
        if cobot_routes._yolo_log_file is not None:
            cobot_routes._yolo_log_file.close()
            cobot_routes._yolo_log_file = None
        cobot_routes.yolo_process = None
        cobot_routes.yolo_test_active = False

    def test_operator_confirmation_only_sets_worker_gate(self):
        previous = dict(cell_routes.cell_state["integrated_real"])
        cell_routes._real_detection_confirm_event.clear()
        try:
            cell_routes.cell_state["integrated_real"] = {
                "active": True,
                "phase": "waiting_detection_confirmation",
                "candidate": {
                    "class": "tin_valid_blue",
                    "target": "delivery_blue",
                    "confidence": 0.8,
                },
            }
            response = cell_routes.confirm_integrated_real_detection()
            self.assertEqual("confirmation_requested", response["status"])
            self.assertFalse(response["movement_commanded"])
            self.assertTrue(cell_routes._real_detection_confirm_event.is_set())
        finally:
            cell_routes._real_detection_confirm_event.clear()
            cell_routes.cell_state["integrated_real"] = previous

    def test_confirmation_is_rejected_without_a_waiting_candidate(self):
        previous = dict(cell_routes.cell_state["integrated_real"])
        try:
            cell_routes.cell_state["integrated_real"] = {
                "active": True,
                "phase": "waiting_real_yolo",
                "candidate": None,
            }
            with self.assertRaises(Exception):
                cell_routes.confirm_integrated_real_detection()
            self.assertFalse(cell_routes._real_detection_confirm_event.is_set())
        finally:
            cell_routes.cell_state["integrated_real"] = previous


class PlanningPcGenerationTest(unittest.TestCase):
    def test_launch_is_not_ready_until_the_measured_generation_completes(self):
        class ImmediateThread:
            def __init__(self, target, daemon):
                self.target = target

            def start(self):
                self.target()

        completed = types.SimpleNamespace(returncode=0, stdout="planning ok", stderr="")
        with health_routes._rviz_launch_lock:
            health_routes._rviz_launch_state["active"] = False
        with patch.object(health_routes.Path, "exists", return_value=True), \
             patch.object(health_routes.subprocess, "run", return_value=completed), \
             patch.object(health_routes.threading, "Thread", ImmediateThread):
            response = health_routes.launch_rviz()

        self.assertEqual("starting", response["status"])
        self.assertFalse(response["ready"])
        measured = health_routes.get_rviz_launch_status(response["run_id"])
        self.assertTrue(measured["completed"])
        self.assertTrue(measured["success"])

    def test_old_generation_is_never_reported_as_current_success(self):
        with health_routes._rviz_launch_lock:
            health_routes._rviz_launch_state.update(
                {"run_id": "new", "active": False, "completed": True, "success": True}
            )
        measured = health_routes.get_rviz_launch_status("old")
        self.assertFalse(measured["success"])
        self.assertIn("substituída", measured["error"])


if __name__ == "__main__":
    unittest.main()
