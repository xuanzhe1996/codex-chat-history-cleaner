# Codex Chat History Cleaner

A Codex skill for safely inspecting and cleaning local Codex chat history remnants, including archived sessions, search-index entries, transcript files, and self-referential cleanup traces.

## What It Contains

- `SKILL.md` - the reusable Codex skill workflow and safety guidance.
- `scripts/clean_codex_history.py` - a deterministic cleanup helper. It defaults to dry-run behavior and only mutates files when `--execute` is passed.
- `references/privacy.md` - a privacy checklist for sharing or publishing cleanup workflows.
- `agents/openai.yaml` - UI metadata for Codex skill discovery.
- `.gitignore` - guardrails to avoid committing local Codex state, transcripts, auth files, databases, screenshots, or backups.

## Example

```bash
python3 scripts/clean_codex_history.py --codex-home "$HOME/.codex" --dry-run
```

Delete archived local Codex sessions after reviewing the dry run:

```bash
python3 scripts/clean_codex_history.py --codex-home "$HOME/.codex" --all-archived --execute
```

## Safety Notes

This tool works on local Codex state. Always inspect with `--dry-run` first, make backups unless you intentionally pass `--no-backup`, and avoid printing private chat titles or full thread IDs into a new cleanup conversation.
