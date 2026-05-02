#!/usr/bin/env python3
"""Safely inspect and clean local Codex chat history stores."""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class ThreadRow:
    id: str
    title: str
    archived: int
    rollout_path: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex-home", default=str(Path.home() / ".codex"))
    parser.add_argument("--dry-run", action="store_true", help="Inspect only. This is the default unless --execute is passed.")
    parser.add_argument("--execute", action="store_true", help="Actually delete or scrub matched records.")
    parser.add_argument("--all-archived", action="store_true", help="Select all archived threads.")
    parser.add_argument("--all-except-current", action="store_true", help="Select all threads except --current-thread-id.")
    parser.add_argument("--current-thread-id", help="Thread ID to preserve when using --all-except-current.")
    parser.add_argument("--ids", nargs="*", default=[], help="Thread IDs or unique prefixes to select.")
    parser.add_argument("--title-contains", nargs="*", default=[], help="Case-insensitive title substrings to select.")
    parser.add_argument("--scrub-file", help="Remove lines matching selected IDs or title substrings from this rollout JSONL file.")
    parser.add_argument("--no-backup", action="store_true", help="Do not create .bak backups before writes.")
    return parser.parse_args()


def state_dbs(codex_home: Path) -> list[Path]:
    return sorted(codex_home.glob("state_*.sqlite"))


def fetch_threads(db_path: Path) -> list[ThreadRow]:
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "select id, title, archived, rollout_path from threads order by updated_at_ms desc, updated_at desc"
        ).fetchall()
    return [ThreadRow(str(row[0]), str(row[1]), int(row[2]), str(row[3])) for row in rows]


def select_threads(rows: list[ThreadRow], args: argparse.Namespace) -> list[ThreadRow]:
    selected: list[ThreadRow] = []
    id_terms = [term.lower() for term in args.ids]
    title_terms = [term.lower() for term in args.title_contains]
    current_id = (args.current_thread_id or "").lower()

    for row in rows:
        row_id = row.id.lower()
        title = row.title.lower()
        match = False
        if args.all_archived and row.archived:
            match = True
        if args.all_except_current and row_id != current_id:
            match = True
        if id_terms and any(row_id.startswith(term) or row_id == term for term in id_terms):
            match = True
        if title_terms and any(term in title for term in title_terms):
            match = True
        if match:
            selected.append(row)
    return selected


def backup(path: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dst = path.with_name(f"{path.name}.bak-{stamp}")
    shutil.copy2(path, dst)
    return dst


def delete_threads(db_path: Path, rows: list[ThreadRow]) -> int:
    ids = [row.id for row in rows]
    if not ids:
        return 0
    placeholders = ",".join("?" for _ in ids)
    with sqlite3.connect(db_path) as conn:
        conn.execute(f"delete from threads where id in ({placeholders})", ids)
        conn.commit()
    return len(ids)


def remove_file(path_text: str) -> bool:
    path = Path(path_text).expanduser()
    if path.exists() and path.is_file():
        path.unlink()
        return True
    return False


def clean_session_index(codex_home: Path, selected: list[ThreadRow], execute: bool) -> tuple[int, int]:
    index_path = codex_home / "session_index.jsonl"
    if not index_path.exists():
        return (0, 0)
    ids = {row.id for row in selected}
    kept: list[str] = []
    removed = 0
    total = 0
    for line in index_path.read_text(encoding="utf-8", errors="replace").splitlines(True):
        total += 1
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            kept.append(line)
            continue
        if str(payload.get("id", "")) in ids or str(payload.get("thread_id", "")) in ids:
            removed += 1
        else:
            kept.append(line)
    if execute and removed:
        index_path.write_text("".join(kept), encoding="utf-8")
    return (total, removed)


def scrub_file(path: Path, rows: list[ThreadRow], title_terms: list[str], execute: bool) -> tuple[int, int]:
    if not path.exists():
        raise FileNotFoundError(path)
    needles = {row.id for row in rows}
    needles.update(term for term in title_terms if term)
    kept: list[str] = []
    removed = 0
    total = 0
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines(True):
        total += 1
        hay = line.lower()
        if any(needle.lower() in hay for needle in needles):
            removed += 1
        else:
            kept.append(line)
    if execute and removed:
        path.write_text("".join(kept), encoding="utf-8")
    return (total, removed)


def main() -> int:
    args = parse_args()
    execute = bool(args.execute)
    if args.dry_run and args.execute:
        raise SystemExit("Use either --dry-run or --execute, not both.")
    if args.all_except_current and not args.current_thread_id:
        raise SystemExit("--all-except-current requires --current-thread-id.")

    codex_home = Path(args.codex_home).expanduser()
    dbs = state_dbs(codex_home)
    if not dbs:
        raise SystemExit(f"No state_*.sqlite databases found in {codex_home}")

    selectors_used = args.all_archived or args.all_except_current or args.ids or args.title_contains
    if not selectors_used and not args.scrub_file:
        print(json.dumps({"mode": "dry-run", "codex_home": str(codex_home), "state_dbs": [str(db) for db in dbs]}, indent=2))
        return 0

    summary: dict[str, object] = {"mode": "execute" if execute else "dry-run", "codex_home": str(codex_home), "databases": []}

    for db_path in dbs:
        rows = fetch_threads(db_path)
        selected = select_threads(rows, args)
        db_report: dict[str, object] = {
            "db": str(db_path),
            "thread_count": len(rows),
            "selected_count": len(selected),
            "selected_ids": [row.id for row in selected],
        }
        if execute and selected and not args.no_backup:
            db_report["backup"] = str(backup(db_path))
        if execute and selected:
            removed_files = sum(1 for row in selected if remove_file(row.rollout_path))
            db_report["removed_session_files"] = removed_files
            db_report["removed_thread_rows"] = delete_threads(db_path, selected)
        index_total, index_removed = clean_session_index(codex_home, selected, execute)
        db_report["session_index_lines"] = index_total
        db_report["session_index_removed"] = index_removed
        if args.scrub_file:
            scrub_path = Path(args.scrub_file).expanduser()
            if execute and not args.no_backup:
                db_report["scrub_backup"] = str(backup(scrub_path))
            scrub_total, scrub_removed = scrub_file(scrub_path, selected, args.title_contains, execute)
            db_report["scrub_file_lines"] = scrub_total
            db_report["scrub_file_removed"] = scrub_removed
        summary["databases"].append(db_report)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
