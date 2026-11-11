## Summary

<!-- Briefly describe what this PR changes and why. -->

## Type of Change

- [ ] Bug fix / operational recovery improvement
- [ ] New feature (Control Center backend / frontend / robot routines)
- [ ] Submodule pointer update (`turtlebot4_jazzy`, `cobot`, or `integration_cobot_tb4`)
- [ ] Documentation update (`docs/`)

## Documentation & Safety Checklist

- [ ] All documentation changes in `docs/` are written **100% in English** (`python3 tools/docs/check_english.py`).
- [ ] If any FastAPI routes in `future_lab_control_center/backend/api/` were added or modified, `docs/reference/rest-api.md` has been updated (`python3 tools/docs/check_route_coverage.py`).
- [ ] If any environment variables in `future_lab_control_center/.env.example` were added or modified, `docs/reference/configuration.md` has been updated (`python3 tools/docs/check_env_coverage.py`).
- [ ] `mkdocs build --strict` passes with zero warnings or broken links.
- [ ] **No passwords, SSH keys, or raw tokens** are included in any committed file.
