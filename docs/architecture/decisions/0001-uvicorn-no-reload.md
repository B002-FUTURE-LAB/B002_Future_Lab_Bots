# 0001 Run uvicorn without reload

**Status:** accepted
**Date:** 2026-08-15

## Context

The backend process holds an `rclpy` node and long-lived executor threads.
`uvicorn` with `reload=True` spawns child processes and can leave old DDS
participants and endpoints visible while one process replaces another. On a
Discovery Server graph this shows up as duplicate participants, not as a clean
restart.

## Decision

`backend/main.py` runs `uvicorn.run(app, ..., reload=False)`. Code changes are
picked up by restarting the container (`docker compose restart backend`).

## Consequences

- No stale participants from hot reload.
- A code change needs a manual restart. The backend's `./backend` folder is
  mounted into the container, so a restart is enough and no rebuild is needed.
