#!/usr/bin/env python3
"""Replica o JSONL de auditoria no ROS 2 dentro do processo de aquisição."""
import argparse
import json
import os
import signal
import time
import uuid
from datetime import datetime, timezone

import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import String

RUNNING = True


def stop(_signum, _frame):
    global RUNNING
    RUNNING = False


def marker(kind, payload=None):
    return json.dumps({
        "schema": "future_lab.event.v1",
        "event_id": str(uuid.uuid4()),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "unix_time_s": time.time(),
        "monotonic_ns": time.monotonic_ns(),
        "kind": kind,
        "payload": payload or {},
    }, ensure_ascii=False, separators=(",", ":"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--trial-id", required=True)
    args = parser.parse_args()
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    if not os.path.isfile(args.input):
        raise SystemExit(f"JSONL de auditoria ausente: {args.input}")
    rclpy.init()
    node = Node("future_lab_experiment_event_relay")
    qos = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=100,
                     reliability=ReliabilityPolicy.RELIABLE,
                     durability=DurabilityPolicy.TRANSIENT_LOCAL)
    publisher = node.create_publisher(String, "/future_lab/events", qos)

    with open(args.input, "r", encoding="utf-8") as stream:
        stream.seek(0, os.SEEK_END)
        last_heartbeat = 0.0
        while RUNNING and rclpy.ok():
            line = stream.readline()
            now = time.monotonic()
            payload = None
            if line:
                payload = line.strip()
            elif now - last_heartbeat >= 5.0:
                payload = marker("recorder_heartbeat", {"trial_id": args.trial_id})
                last_heartbeat = now
            if payload:
                msg = String()
                msg.data = payload
                publisher.publish(msg)
            rclpy.spin_once(node, timeout_sec=0.05)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
