#!/usr/bin/env python3
"""Valida integridade e cobertura mínima de um ensaio gravado."""
import argparse
import json
from pathlib import Path
import sys
import yaml

CORE = ["/future_lab/events", "/odom", "/tf", "/joint_states", "/dock_status"]
REAL = ["/scan", "/battery_state", "/product_class", "/turtlebot_at_pickup",
        "/item_released_on_tb4", "/amcl_pose"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("trial_dir")
    parser.add_argument("--mode", choices=("smoke", "real"), default="real")
    args = parser.parse_args()
    trial = Path(args.trial_dir)
    metadata_path = trial / "rosbag" / "metadata.yaml"
    failures = []
    if not metadata_path.exists():
        failures.append("metadata.yaml do rosbag ausente")
        info = {}
    else:
        info = yaml.safe_load(metadata_path.read_text(encoding="utf-8"))["rosbag2_bagfile_information"]
    topics = {
        item["topic_metadata"]["name"]: int(item.get("message_count", 0))
        for item in info.get("topics_with_message_count", [])
    }
    duration_ns = int((info.get("duration") or {}).get("nanoseconds", 0))
    if duration_ns < (2 if args.mode == "smoke" else 30) * 1_000_000_000:
        failures.append("duração gravada abaixo do mínimo")
    required = CORE + (REAL if args.mode == "real" else [])
    for topic in required:
        if topics.get(topic, 0) < 1:
            failures.append(f"tópico obrigatório sem mensagens: {topic}")
    if not (trial / "dashboard_state.jsonl").exists():
        failures.append("dashboard_state.jsonl ausente")
    result = {
        "valid": not failures,
        "mode": args.mode,
        "duration_s": duration_ns / 1e9,
        "message_count": int(info.get("message_count", 0)),
        "required_topic_counts": {topic: topics.get(topic, 0) for topic in required},
        "failures": failures,
    }
    (trial / "validation.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
