# Contributing to B002 Future Lab Bots

Welcome to the **B002 Future Lab Bots** repository! This guide summarizes how new maintainers and researchers should work with the codebase, its three Git submodules, and the MkDocs documentation site.

---

## 1. Cloning with Submodules

This repository tracks three robot submodules (`turtlebot4_jazzy`, `cobot`, and `integration_cobot_tb4`). Always initialize them after cloning:

```bash
git clone git@github.com:B002-FUTURE-LAB/B002_Future_Lab_Bots.git
cd B002_Future_Lab_Bots
git submodule update --init --recursive
```

---

## 2. Keeping Documentation Up to Date ("Docs-as-Code")

All documentation lives under [`docs/`](docs/) and is built into a static site using **MkDocs Material** (`mkdocs.yml`).

- **Language Policy**: Every published file under `docs/` must be written **100% in English**.
- **No Secrets Policy**: Never include real passwords, tokens, or private SSH keys in documentation or commit messages. Refer only to environment variable names (e.g., `HOST_AGENT_TOKEN`, `NANO_IP`, `TB4_IP`).
- **Guides for Contributors**:
  - [How to Edit These Docs](docs/contributing/how-to-edit-these-docs.md)
  - [Documentation Style Guide](docs/contributing/style-guide.md)

---

## 3. Running Local Verification Before Opening a PR

Before pushing changes or opening a Pull Request, run the automated documentation and coverage checks from the repository root:

```bash
# 1. Verify 100% English in published docs
python3 tools/docs/check_english.py

# 2. Verify 100% FastAPI REST route coverage in docs/reference/rest-api.md
python3 tools/docs/check_route_coverage.py

# 3. Verify 100% .env.example variable coverage in docs/reference/configuration.md
python3 tools/docs/check_env_coverage.py

# 4. Build the MkDocs site in strict mode (fails on any broken link or warning)
mkdocs build --strict
```

---

## 4. Running Backend Unit Tests

To run the Control Center unit test suite (`future_lab_control_center/tests/`):

```bash
cd future_lab_control_center
pytest
```
