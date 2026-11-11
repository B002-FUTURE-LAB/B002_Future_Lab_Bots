# Style guide

## Language

- **Everything is in English.** CI rejects Portuguese-specific letters.
- Write short sentences. Prefer the active voice: "Run the script", not "The
  script should be run".
- Spell out an acronym the first time on a page.

## One page, one kind

Each page is one of four kinds. Do not mix them.

| Kind | Starts with | Example |
|---|---|---|
| Tutorial | What the reader will have at the end | Install and first run |
| How-to guide | The problem, in the reader's words | Recover TurtleBot telemetry |
| Reference | A table of exact facts | REST API |
| Explanation | The question it answers | Safety model |

## Guides must be verifiable

A guide says how to **check** each step worked, not only what to type. Give
the command and the healthy result.

## Mark what you did not verify

If you are not sure a statement is true on the real hardware, say so in an
admonition, and remove it when you confirm:

```markdown
!!! note "Not verified"
    This was not tested on the real robot.
```

## Rules

- **No secrets.** No passwords, tokens or `.env` contents. Variable names only.
- **Use relative links** between pages, such as `../reference/rest-api.md`.
- **Put exact values in tables**, and explanations in prose.
- **Name the source.** For a fact taken from code, name the file.
- **Show the lesson.** When a page comes from a real incident, state what
  looked right but was wrong, as in "Ping is not proof".

## Admonitions

| Use | For |
|---|---|
| `note` | Context that helps but is not required |
| `tip` | A faster or safer way |
| `warning` | Something that can break the setup |
| `danger` | Something that can hurt people or hardware |
