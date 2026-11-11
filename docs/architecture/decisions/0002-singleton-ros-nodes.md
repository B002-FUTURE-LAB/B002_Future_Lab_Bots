# 0002 Single locked ROS node per process

**Status:** accepted
**Date:** 2026-08-15

## Context

The dashboard calls several endpoints in parallel on first load. Two threads
could both see that the node did not exist yet and each build one, giving two
nodes with the same name, each with its own service clients.

## Decision

`get_turtlebot_node()` and `get_cobot_node()` create the node under a lock
(double-checked), so each process has exactly one instance. There are
concurrency tests for both (`tests/test_turtlebot_singleton.py`).

## Consequences

- One node, one set of clients, one entry in the ROS graph.
- Node construction must not block for long, because other requests wait on the
  lock during first use.
