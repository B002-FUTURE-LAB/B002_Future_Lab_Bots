# How to edit these docs

The documentation lives in the `docs/` folder of the repository, as Markdown
files. You edit them like code: change a file, commit, open a pull request.

## Quick edit in the browser

Every page has a pencil icon (**Edit this page**) that opens the file on GitHub.
Edit, then choose **Propose changes**.

## Edit locally and preview

```bash
python3 -m venv .venv-docs
source .venv-docs/bin/activate
pip install -r docs/requirements.txt

mkdocs serve        # live preview at http://127.0.0.1:8000
```

!!! note "Port 8000"
    `mkdocs serve` also uses port 8000, which the backend uses. Stop the backend
    first, or run `mkdocs serve -a 127.0.0.1:8001`.

## Before you open a pull request

Run the same checks as CI:

```bash
python3 tools/docs/check_english.py
python3 tools/docs/check_route_coverage.py
mkdocs build --strict
```

| Check | Fails when |
|---|---|
| `check_english.py` | A page contains Portuguese-specific letters. |
| `check_route_coverage.py` | A REST route exists in the code but not in [REST API](../reference/rest-api.md). |
| `mkdocs build --strict` | A link is broken or a page is missing from the menu. |

## Adding a page

1. Create the `.md` file in the matching folder.
2. Add it to `nav` in `mkdocs.yml`.
3. Link to it from at least one other page.

## When you change the code

If your change adds or changes a route, a topic, a port, a setting or a
procedure, update the matching page **in the same pull request**.

Never put passwords, tokens or the contents of `.env` in the docs. Write only
the **names** of variables.
