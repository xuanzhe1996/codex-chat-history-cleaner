---
name: codex-chat-history-cleaner
description: Safely inspect and clean local Codex chat history, archived sessions, search-index remnants, and self-referential cleanup traces. Use when a user asks why deleted or archived Codex chats still appear in search, wants to delete local chat records, scrub current-session references to old chats, or prepare a privacy-preserving cleanup workflow for sharing.
---

# Codex Chat History Cleaner

## Core Rule

Treat Codex chat cleanup as destructive local-state maintenance. Start with a dry run, identify every storage surface, explain what will be removed, and request approval before executing any deletion outside the current writable workspace.

Do not print private titles, paths, user names, or full thread IDs into the current conversation when the user's goal is search cleanup. Printing the matching text can make the current session become the new search hit.

## Storage Surfaces

Check these local Codex locations under `CODEX_HOME` or `~/.codex`:

- `state_*.sqlite`: thread metadata; `threads.archived=1` means archived, not deleted.
- `sessions/**/rollout-*.jsonl`: normal chat transcript files.
- `archived_sessions/**/rollout-*.jsonl`: archived transcript files.
- `session_index.jsonl`: lightweight search/list index.
- `generated_images/` and related artifact directories: optional per-thread artifacts.
- `logs_*.sqlite`: diagnostic logs; inspect only if deleted sessions still appear after the primary stores are clean.

## Workflow

1. Locate `CODEX_HOME`.
2. Run `scripts/clean_codex_history.py --dry-run` to inventory databases, session files, archived files, and index records.
3. Choose selectors:
   - Use `--all-archived` for archived sessions.
   - Use `--ids <id-prefix-or-id>` when thread IDs are known.
   - Use `--title-contains <text>` sparingly; avoid echoing sensitive titles in chat.
   - Use `--all-except-current --current-thread-id <id>` only when the user asks to remove all historical search results while preserving the active thread.
4. Run another dry run with the selectors and review counts.
5. Execute only after approval: add `--execute`.
6. Verify with the same dry-run command and a direct SQLite count/list query that avoids printing sensitive strings.
7. Tell the user to restart Codex if UI search still displays stale cached results.

## Self-Referential Search Hits

If old titles still appear after deletion, inspect whether the current cleanup conversation contains command output or assistant text that repeated those old titles. In that case, scrub the current `rollout-*.jsonl` with `--scrub-file <path>` and selectors. Prefer ID selectors or encoded/local-only patterns to avoid reintroducing sensitive terms into chat.

Example:

```bash
python3 scripts/clean_codex_history.py \
  --codex-home "$HOME/.codex" \
  --scrub-file "$HOME/.codex/sessions/YYYY/MM/DD/rollout-THREAD.jsonl" \
  --ids THREAD_PREFIX \
  --dry-run
```

Then execute with `--execute` after approval.

## Bundled Script

Use `scripts/clean_codex_history.py` for deterministic cleanup. It defaults to dry-run mode and creates timestamped backups before changing SQLite databases or index files unless `--no-backup` is passed.

Useful commands:

```bash
# Inventory only
python3 scripts/clean_codex_history.py --codex-home "$HOME/.codex" --dry-run

# Delete archived records and files after approval
python3 scripts/clean_codex_history.py --codex-home "$HOME/.codex" --all-archived --execute

# Delete all non-current threads after approval
python3 scripts/clean_codex_history.py --codex-home "$HOME/.codex" \
  --all-except-current --current-thread-id THREAD_ID --execute
```

## Privacy Before Sharing

Before publishing this skill, read `references/privacy.md`. Do not include real usernames, absolute local paths, conversation titles, thread IDs, screenshots, database rows, generated images, auth files, or logs.
