# 0006 Documentation toolchain

**Status:** accepted, to be revisited
**Date:** 2026-10-24

## Context

The documentation must be easy for a newcomer to edit, versioned with the code,
written in English and published on GitHub Pages. Python is already part of the
project, and the team prefers plain Markdown.

## Decision

Use **MkDocs with the Material theme**, with versions pinned in
`docs/requirements.txt`. Build and deploy with GitHub Actions to GitHub Pages.
Structure the content with the Diataxis model. The build runs in strict mode,
so a broken link fails it.

## Consequences

- Pages are plain Markdown plus one `mkdocs.yml`, so the content is portable.
- **Risk:** Material for MkDocs is reported to be in maintenance mode, and its
  successor, Zensical (from the same authors), was still pre-1.0 when this was
  written. Pinned versions keep working. Review this decision when a Zensical
  1.0 release exists, or when the pinned versions stop installing. Moving to
  Zensical is expected to be cheap, because it reads `mkdocs.yml`.
- Python docstrings in the code are in Portuguese, so they are **not**
  rendered automatically. Reference pages are written by hand in English.
