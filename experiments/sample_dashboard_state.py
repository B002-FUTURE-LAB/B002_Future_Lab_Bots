#!/usr/bin/env python3
"""Amostra as leituras HTTP que não devem inundar o tópico de auditoria."""
import argparse
import json
import signal
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

RUNNING = True
ENDPOINTS = (
    "/api/v1/cell/status",
    "/api/v1/turtlebot/status",
    "/api/v1/turtlebot/nav_readiness",
    "/api/v1/turtlebot/processes",
    "/api/v1/health/",
)


def stop(_signum, _frame):
    global RUNNING
    RUNNING = False


def fetch(url):
    try:
        with urllib.request.urlopen(url, timeout=2.5) as response:
            return {"ok": True, "status": response.status,
                    "data": json.loads(response.read().decode("utf-8"))}
    except Exception as exc:
        return {"ok": False, "error": repr(exc)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    parser.add_argument("--output", required=True)
    parser.add_argument("--interval", type=float, default=1.0)
    args = parser.parse_args()
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    with open(args.output, "a", encoding="utf-8", buffering=1) as stream:
        while RUNNING:
            started = time.monotonic()
            sample = {
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "unix_time_s": time.time(),
                "endpoints": {path: fetch(args.api + path) for path in ENDPOINTS},
            }
            stream.write(json.dumps(sample, ensure_ascii=False) + "\n")
            time.sleep(max(0.0, args.interval - (time.monotonic() - started)))


if __name__ == "__main__":
    main()
