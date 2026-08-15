"""Trilha de auditoria do experimento: JSONL local + tópico ROS 2."""
from __future__ import annotations

import json
import os
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_write_lock = threading.Lock()
_default_path = Path(__file__).resolve().parent / "runtime" / "events.jsonl"


def _json_safe(value: Any) -> Any:
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return repr(value)


def build_event(kind: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "schema": "future_lab.event.v1",
        "event_id": str(uuid.uuid4()),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "unix_time_s": time.time(),
        "monotonic_ns": time.monotonic_ns(),
        "kind": str(kind),
        "payload": _json_safe(payload or {}),
    }


def emit_event(kind: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Persiste e publica um evento sem impedir a operação em caso de falha."""
    event = build_event(kind, payload)
    serialized = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
    path = Path(os.getenv("FUTURE_LAB_EVENT_LOG", str(_default_path)))
    try:
        with _write_lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as stream:
                stream.write(serialized + "\n")
                stream.flush()
    except Exception as exc:
        print(f"[WARN] Falha ao persistir evento experimental: {exc}")
    try:
        from backend.ros2_nodes.cobot_node import get_cobot_node
        get_cobot_node().publish_experiment_event(serialized)
    except Exception as exc:
        print(f"[WARN] Falha ao publicar evento experimental no ROS 2: {exc}")
    return event
