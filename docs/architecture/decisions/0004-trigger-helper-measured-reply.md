# 0004 Trigger helper needs a measured reply

**Status:** accepted
**Date:** 2026-08-15

## Context

Mission services (`/start_delivery` and the others) are called from the host.
A call that returns without a reply from the server proves nothing: the request
may have been lost, or it may have arrived and been executed.

## Decision

`run_trigger_service` in the host agent calls an allowed `Trigger` exactly once
through a helper process and **requires the server's reply**. A timeout is
returned as HTTP 504 with the state described as indeterminate, and the agent
never retries it automatically. Only four services are allowed:
`start_delivery`, `start_failure`, `start_restock` and `stop_mission`.

## Consequences

- No duplicate missions caused by blind retries.
- The operator, not the system, decides whether to repeat an ambiguous request.
- A service outside the allow-list is rejected before any process runs
  (HTTP 422).
