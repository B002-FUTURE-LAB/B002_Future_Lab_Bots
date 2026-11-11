# 0005 Cancel timers, never destroy them in callbacks

**Status:** accepted
**Date:** 2026-08-15

## Context

The mission routines run on a multithreaded executor. Destroying a timer, a
subscription or a transform listener while a callback (or the executor's wait
set) still references it raises `rclpy._rclpy_pybind11.InvalidHandle` and can
take down the whole Mission Manager process.

## Decision

Inside the mission classes, timers are only cancelled (`timer.cancel()`), not
destroyed. Observers such as subscriptions and the transform listener are not
destroyed on completion either; only their timestamps are reset, so the next
mission requires fresh samples. The entities are released when the node shuts
down, at a safe point. A test checks the source for `destroy_timer(` and for
subscription cleanup in the observer reset.

## Consequences

- No `InvalidHandle` crashes during mission completion.
- A few small cancelled timers and observers live until the node exits. They
  are cheap.
