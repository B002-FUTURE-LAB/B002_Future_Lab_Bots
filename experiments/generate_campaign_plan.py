#!/usr/bin/env python3
"""Gera 60 ensaios balanceados e aleatorizados de forma reproduzível."""
import argparse
import csv
import random

CONDITIONS = ("no_obstacle", "static_obstacle", "dynamic_obstacle")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="campaign_plan.csv")
    parser.add_argument("--seed", type=int, default=20260815)
    args = parser.parse_args()
    rows = []
    for condition in CONDITIONS:
        for replicate in range(1, 21):
            rows.append({
                "condition": condition,
                "replicate": replicate,
                "can_color": "blue" if replicate % 2 else "red",
            })
    random.Random(args.seed).shuffle(rows)
    with open(args.output, "w", newline="", encoding="utf-8") as stream:
        fields = ["trial", "condition", "replicate", "can_color", "status", "notes"]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for trial, row in enumerate(rows, 1):
            writer.writerow({"trial": trial, **row, "status": "pending", "notes": ""})
    print(f"Plano criado em {args.output}: 60 ensaios, seed={args.seed}")


if __name__ == "__main__":
    main()
