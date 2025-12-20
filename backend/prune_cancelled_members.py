#!/usr/bin/env python3
"""CLI to remove database members missing from the official membership CSV."""

import argparse
import curses
import csv
import logging
import sqlite3
import sys
import unicodedata
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

DEFAULT_DB = Path("doorlock.db")
DEFAULT_CSV = Path(__file__).resolve().parent / "Mitglieder - Members.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Remove database members that no longer appear in the membership CSV"
    )
    parser.add_argument(
        "--db",
        default=str(DEFAULT_DB),
        help="Path to doorlock.db (default: %(default)s)",
    )
    parser.add_argument(
        "--csv",
        default=str(DEFAULT_CSV),
        help="Path to the CSV export listing current members",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only show pending removals without modifying the database",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip the interactive confirmation prompt",
    )
    return parser.parse_args()


def normalize_name(value: str) -> str:
    """Return a lower-cased ASCII equivalent for matching (handles umlauts, ß, etc.)."""
    replacements = {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "Ä": "Ae",
        "Ö": "Oe",
        "Ü": "Ue",
        "ß": "ss",
    }
    result = value or ""
    for src, repl in replacements.items():
        result = result.replace(src, repl)
    result = unicodedata.normalize("NFKD", result)
    result = result.encode("ascii", "ignore").decode("ascii")
    result = " ".join(result.split())
    return result.lower()


def load_active_names(csv_path: Path) -> Dict[str, str]:
    required_fields = {"Vorname", "Name"}
    names: Dict[str, str] = {}

    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = required_fields.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"CSV missing required columns: {sorted(missing)}")
        for row in reader:
            firstname = (row.get("Vorname") or "").strip()
            lastname = (row.get("Name") or "").strip()
            full_name = f"{firstname} {lastname}".strip()
            key = normalize_name(full_name)
            if key:
                names.setdefault(key, full_name)
    return names


def fetch_all_persons(conn: sqlite3.Connection) -> List[Tuple[int, str, int, int]]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT p.id, p.name, COUNT(t.id) AS tokens, p.disabled
        FROM dl_persons p
        LEFT JOIN dl_tokens t ON t.person_id = p.id
        GROUP BY p.id, p.name, p.disabled
        ORDER BY p.name
        """
    )
    return cursor.fetchall()


def confirm(prompt: str) -> bool:
    try:
        answer = input(prompt).strip().lower()
    except EOFError:
        return False
    return answer in {"y", "yes"}


def disable_people(conn: sqlite3.Connection, targets: Sequence[Tuple[int, str, int, int]]) -> None:
    cursor = conn.cursor()
    for person_id, _name, _token_count, _disabled in targets:
        cursor.execute("UPDATE dl_persons SET disabled = 1 WHERE id = ?", (person_id,))
    conn.commit()


def _selection_ui(stdscr, candidates: Sequence[Tuple[int, str, int, int]]):
    curses.curs_set(0)
    stdscr.keypad(True)
    current = 0
    selected = set()

    while True:
        stdscr.erase()
        height, width = stdscr.getmaxyx()
        list_space = max(1, height - 4)
        start = min(max(0, current - list_space + 1), max(0, len(candidates) - list_space))
        end = min(len(candidates), start + list_space)

        stdscr.addstr(0, 0, "Select members to remove (space=toggle, arrows=move, Enter=confirm, q=abort)"[:width])

        for idx in range(start, end):
            person_id, name, token_count, _disabled = candidates[idx]
            marker = "[x]" if idx in selected else "[ ]"
            line = f" {marker} {name} (tokens: {token_count})"
            if idx == current:
                stdscr.addnstr(idx - start + 1, 0, line, width, curses.A_REVERSE)
            else:
                stdscr.addnstr(idx - start + 1, 0, line, width)

        stdscr.addstr(height - 2, 0, f"Selected: {len(selected)} / {len(candidates)}"[:width])
        stdscr.addstr(height - 1, 0, "Press Enter to delete selected entries"[:width])
        stdscr.refresh()

        key = stdscr.getch()

        if key in (curses.KEY_UP, ord('k')):
            current = max(0, current - 1)
        elif key in (curses.KEY_DOWN, ord('j')):
            current = min(len(candidates) - 1, current + 1)
        elif key in (curses.KEY_NPAGE, ord('f')):
            current = min(len(candidates) - 1, current + list_space)
        elif key in (curses.KEY_PPAGE, ord('b')):
            current = max(0, current - list_space)
        elif key in (ord(' '),):
            if current in selected:
                selected.remove(current)
            else:
                selected.add(current)
        elif key in (curses.KEY_ENTER, 10, 13):
            return [candidates[idx] for idx in sorted(selected)]
        elif key in (ord('q'), 27):
            raise KeyboardInterrupt


def interactive_select(candidates: Sequence[Tuple[int, str, int, int]]) -> List[Tuple[int, str, int, int]]:
    if not candidates:
        return []

    try:
        return curses.wrapper(_selection_ui, candidates)
    except KeyboardInterrupt:
        return None


def main() -> int:
    args = parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger("prune_cancelled_members")

    csv_path = Path(args.csv).expanduser()
    db_path = Path(args.db).expanduser()

    if not csv_path.exists():
        logger.error("CSV file %s not found", csv_path)
        return 1
    if not db_path.exists():
        logger.error("Database file %s not found", db_path)
        return 1

    try:
        active_names = load_active_names(csv_path)
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("Failed to read CSV: %s", exc)
        return 1

    if not active_names:
        logger.info("CSV did not contain any names")
        return 0

    with sqlite3.connect(str(db_path)) as conn:
        db_persons = fetch_all_persons(conn)
        db_name_keys = {normalize_name(name) for _, name, _, _ in db_persons}
        to_remove = [
            person
            for person in db_persons
            if person[3] == 0 and normalize_name(person[1]) not in active_names
        ]
        missing_in_db = sorted(
            active_names[key]
            for key in active_names.keys()
            if key not in db_name_keys
        )

        if missing_in_db:
            logger.info(
                "Names present in CSV but absent from database: %s",
                ", ".join(missing_in_db),
            )

        if not to_remove:
            logger.info("Database already matches membership CSV; nothing to disable")
            return 0

        logger.info("Members missing from CSV (will be disabled):")
        for _, name, token_count, _ in to_remove:
            logger.info("  %s (tokens: %s)", name, token_count)

        if args.dry_run:
            logger.info("Dry run enabled; no records deleted")
            return 0

        if args.yes:
            selected = to_remove
        else:
            if not (sys.stdin.isatty() and sys.stdout.isatty()):
                logger.error(
                    "Interactive selection requires a TTY. Rerun with --yes or --dry-run in non-interactive environments."
                )
                return 1

            selected = interactive_select(to_remove)
            if selected is None:
                logger.info("Aborted by user")
                return 0
            if not selected:
                logger.info("No members selected; nothing deleted")
                return 0

        disable_people(conn, selected)
        removed_count = len(selected)

    logger.info("Disabled %d members", removed_count)
    return 0


if __name__ == "__main__":
    sys.exit(main())
