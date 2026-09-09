#!/usr/bin/env python3
"""Espera evidência estável do TF map->odom antes de iniciar o Nav2."""

import argparse
import json
import os
import time

import rclpy
from rclpy.duration import Duration
from rclpy.node import Node
from tf2_ros import Buffer, TransformListener


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--samples", type=int, default=2)
    args = parser.parse_args()
    if args.timeout <= 0 or args.samples < 1:
        print(json.dumps({"ok": False, "error": "timeout e samples precisam ser positivos."}))
        return 2

    rclpy.init()
    node = Node(f"future_lab_wait_map_tf_{os.getpid()}")
    buffer = Buffer()
    listener = TransformListener(buffer, node, spin_thread=False)
    deadline = time.monotonic() + args.timeout
    consecutive = 0
    last_error = "TF map->odom ainda indisponível"
    try:
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.15)
            try:
                transform = buffer.lookup_transform(
                    "map", "odom", rclpy.time.Time(), timeout=Duration(seconds=0.1)
                )
                consecutive += 1
                if consecutive >= args.samples:
                    stamp = transform.header.stamp
                    print(json.dumps({
                        "ok": True,
                        "samples": consecutive,
                        "frame": "map->odom",
                        "stamp_ns": int(stamp.sec) * 1_000_000_000 + int(stamp.nanosec),
                    }))
                    return 0
            except Exception as exc:
                consecutive = 0
                last_error = str(exc)
            time.sleep(0.15)
        print(json.dumps({"ok": False, "error": last_error}))
        return 1
    finally:
        del listener
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
