import json
import os
import tempfile
import queue
import unittest
from pathlib import Path
from unittest.mock import patch

from backend import experiment_audit
from backend.ros2_nodes import cobot_node


class ExperimentAuditTest(unittest.TestCase):
    def test_event_is_appended_as_jsonl_and_published(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "events.jsonl"
            fake_node = type("Node", (), {"publish_experiment_event": lambda self, data: True})()
            with patch.dict(os.environ, {"FUTURE_LAB_EVENT_LOG": str(target)}), \
                 patch.object(cobot_node, "get_cobot_node", return_value=fake_node):
                event = experiment_audit.emit_event("test_event", {"measured": True})
            persisted = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual("future_lab.event.v1", persisted["schema"])
            self.assertEqual("test_event", persisted["kind"])
            self.assertTrue(persisted["payload"]["measured"])
            self.assertEqual(event["event_id"], persisted["event_id"])

    def test_ros_publisher_reports_real_publish(self):
        published = []
        node = type("Node", (), {
            "experiment_event_queue": queue.SimpleQueue(),
            "experiment_event_pub": type("Publisher", (), {
                "publish": lambda self, msg: published.append(msg.data)
            })()
        })()
        with patch.object(cobot_node, "HAS_RCLPY", True), \
             patch.object(cobot_node, "String", type("String", (), {})):
            self.assertTrue(cobot_node.CobotNode.publish_experiment_event(node, '{"ok":true}'))
            cobot_node.CobotNode._flush_experiment_events(node)
        self.assertEqual(['{"ok":true}'], published)


if __name__ == "__main__":
    unittest.main()
