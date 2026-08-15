#!/usr/bin/env python3
"""Aguarda uma confirmação real em /turtlebot_at_pickup no grafo do host."""

from __future__ import annotations

import argparse
import json
import sys
import time

import rclpy
from std_msgs.msg import Bool


def emit(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=float, default=8.0)
    args = parser.parse_args()
    timeout = max(1.0, min(15.0, float(args.timeout)))

    rclpy.init()
    node = rclpy.create_node("_future_lab_pickup_waiter")
    received_at = None

    def callback(message: Bool) -> None:
        nonlocal received_at
        if message.data:
            received_at = time.time()

    subscription = node.create_subscription(
        Bool, "/turtlebot_at_pickup", callback, 10
    )
    try:
        deadline = time.monotonic() + timeout
        publisher_count = 0
        while time.monotonic() < deadline and received_at is None:
            rclpy.spin_once(node, timeout_sec=0.1)
            publisher_count = int(node.count_publishers("/turtlebot_at_pickup"))

        result = {
            "received": received_at is not None,
            "topic": "/turtlebot_at_pickup",
            "publisher_count": publisher_count,
            "received_at": received_at,
        }
        if received_at is None:
            result["detail"] = (
                "Nenhuma confirmação True recebida em /turtlebot_at_pickup "
                "dentro da janela medida."
            )
            emit(result)
            return 4
        emit(result)
        return 0
    except Exception as exc:
        emit({
            "received": False,
            "topic": "/turtlebot_at_pickup",
            "error": f"{type(exc).__name__}: {exc}",
        })
        return 5
    finally:
        node.destroy_subscription(subscription)
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    sys.exit(main())
