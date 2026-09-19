#!/usr/bin/env python3
"""Interactive CLI to rename members stored in doorlock.db."""

import argparse
import curses
import logging
import sqlite3
import sys
from pathlib import Path
from typing import Tuple

DEFAULT_DB = Path("doorlock.db")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Interactively rename members in doorlock.db")
    parser.add_argument(
        "--db",
        default=str(DEFAULT_DB),
        help="Path to doorlock.db (default: %(default)s)",
    )
    return parser.parse_args()


def split_name(full: str) -> Tuple[str, str]:
    parts = (full or "").strip().split()
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    first = " ".join(parts[:-1])
    last = parts[-1]
    return first, last


def fetch_all_persons(conn: sqlite3.Connection):
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


def prompt_rename(conn: sqlite3.Connection, person_id: int, current_name: str, logger: logging.Logger) -> None:
    old_first, old_last = split_name(current_name)

    try:
        new_last = input(f"New last name [{old_last}]: ").strip() or old_last
        new_first = input(f"New first name [{old_first}]: ").strip() or old_first
    except EOFError:
        logger.info("Input aborted; no changes")
        return

    new_name = f"{new_first} {new_last}".strip()
    if new_name == current_name:
        logger.info("No change requested")
        return

    try:
        confirm = input(f"Rename '{current_name}' -> '{new_name}'? [y/N] ").strip().lower()
    except EOFError:
        logger.info("Confirmation aborted; no changes")
        return

    if confirm not in {"y", "yes"}:
        logger.info("Rename cancelled")
        return

    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM dl_persons WHERE name = ? AND id != ?", (new_name, person_id))
    if cursor.fetchone():
        logger.error("A person named '%s' already exists; aborting rename", new_name)
        return

    cursor.execute("UPDATE dl_persons SET name = ? WHERE id = ?", (new_name, person_id))
    conn.commit()
    logger.info("Renamed '%s' -> '%s'", current_name, new_name)


def list_ui(stdscr, conn: sqlite3.Connection, logger: logging.Logger):
    curses.curs_set(0)
    stdscr.keypad(True)
    current = 0

    while True:
        persons = fetch_all_persons(conn)
        if not persons:
            stdscr.erase()
            stdscr.addstr(0, 0, "No members in database. Press q to quit.")
            stdscr.refresh()
            if stdscr.getch() in (ord('q'), 27):
                return
            continue

        current = max(0, min(current, len(persons) - 1))

        stdscr.erase()
        height, width = stdscr.getmaxyx()
        list_space = max(1, height - 4)
        start = min(max(0, current - list_space + 1), max(0, len(persons) - list_space))
        end = min(len(persons), start + list_space)

        stdscr.addstr(0, 0, "Select member to rename (space=edit, arrows=move, q=quit)"[:width])

        for idx in range(start, end):
            person_id, name, token_count, disabled = persons[idx]
            status = "DISABLED" if disabled else "ACTIVE"
            line = f" {name} (tokens: {token_count}, {status})"
            if idx == current:
                stdscr.addnstr(idx - start + 1, 0, line, width, curses.A_REVERSE)
            else:
                stdscr.addnstr(idx - start + 1, 0, line, width)

        stdscr.addstr(height - 1, 0, "Press space to rename highlighted member"[:width])
        stdscr.refresh()

        key = stdscr.getch()

        if key in (curses.KEY_UP, ord('k')):
            current = max(0, current - 1)
        elif key in (curses.KEY_DOWN, ord('j')):
            current = min(len(persons) - 1, current + 1)
        elif key in (curses.KEY_PPAGE, ord('b')):
            current = max(0, current - list_space)
        elif key in (ord('f'),):
            curses.endwin()
            try:
                query = input("Search name (case-insensitive): ").strip().lower()
            except EOFError:
                query = ""
            if query:
                for idx, (_, name, _tc, _dis) in enumerate(persons):
                    if query in name.lower():
                        current = idx
                        break
            stdscr.clear()
            curses.reset_prog_mode()
            curses.curs_set(0)
            stdscr.keypad(True)
        elif key in (ord('q'), 27):
            return
        elif key in (ord(' '),):
            person_id, name, _token_count, _disabled = persons[current]
            # Temporarily suspend curses to collect interactive input
            curses.endwin()
            prompt_rename(conn, person_id, name, logger)
            stdscr.clear()
            curses.reset_prog_mode()
            curses.curs_set(0)
            stdscr.keypad(True)


def main() -> int:
    args = parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger("rename_members")

    db_path = Path(args.db).expanduser()
    if not db_path.exists():
        logger.error("Database file %s not found", db_path)
        return 1

    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        logger.error("Interactive UI requires a TTY")
        return 1

    with sqlite3.connect(str(db_path)) as conn:
        curses.wrapper(list_ui, conn, logger)

    return 0


if __name__ == "__main__":
    sys.exit(main())
