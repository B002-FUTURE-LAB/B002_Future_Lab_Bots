# Decision records

A decision record explains **one** choice: the situation, the decision and its
consequences. Add a new one whenever you make a choice a future maintainer
might otherwise undo by mistake.

| Number | Decision |
|---|---|
| [0001](0001-uvicorn-no-reload.md) | Run uvicorn without reload |
| [0002](0002-singleton-ros-nodes.md) | Single locked ROS node per process |
| [0003](0003-cancel-goal-service.md) | Cancel goals through the `CancelGoal` service |
| [0004](0004-trigger-helper-measured-reply.md) | Trigger helper needs a measured reply |
| [0005](0005-no-destroy-in-callbacks.md) | Cancel timers, never destroy them in callbacks |
| [0006](0006-documentation-toolchain.md) | Documentation toolchain |

## Template

```markdown
# 000N Short title

**Status:** accepted | superseded by 000M
**Date:** YYYY-MM-DD

## Context
What situation forced a choice?

## Decision
What was decided?

## Consequences
What gets easier, what gets harder, what to watch.
```
