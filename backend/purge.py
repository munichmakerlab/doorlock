#!/usr/bin/env python3
"""
Sync members CSV with sqlite DB (Vorname+Name -> dl_persons.name).

Improved matching:
- Unicode normalized (NFKD), accents removed.
- All whitespace collapsed, NBSP and similar handled.
- Common punctuation removed.
- Comparison done by token set (order-insensitive).

Usage:
    python3 sync_members.py members.csv members.db
    python3 sync_members.py members.csv members.db --dry-run
    python3 sync_members.py members.csv members.db --backup
"""
import argparse
import csv
import shutil
import sqlite3
import sys
import unicodedata
import re
from pathlib import Path
from typing import Set, Tuple

# Pattern to remove punctuation (keep letters, digits and spaces)
_PUNCT_RE = re.compile(r"[^\w\s]", flags=re.UNICODE)
# Pattern to collapse any whitespace (including NBSP) to single space
_WHITESPACE_RE = re.compile(r"\s+", flags=re.UNICODE)


def normalize_to_tokens(s: str) -> Tuple[str, ...]:
    """
    Turn a name string into a sorted tuple of normalized tokens.
    Steps:
    - None -> empty tuple
    - Unicode NFKD normalize and remove diacritics
    - replace non-breaking and unusual spaces via \s, collapse runs to single space
    - remove punctuation (commas, dots, etc.)
    - lowercase (casefold)
    - split into tokens, drop empty tokens, sort and return tuple
    """
    if s is None:
        return tuple()
    s = str(s)
    # Normalize and remove combining marks (accents)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    # Remove punctuation (keeps letters, digits and whitespace)
    s = _PUNCT_RE.sub(" ", s)
    # Collapse whitespace
    s = _WHITESPACE_RE.sub(" ", s).strip()
    # casefold for aggressive lowercasing
    s = s.casefold()
    # Split into tokens
    tokens = [t for t in s.split(" ") if t]
    tokens.sort()
    return tuple(tokens)


def read_csv_names(csv_path: Path) -> Set[Tuple[str, ...]]:
    names = set()
    with csv_path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames:
            raise SystemExit("CSV has no header row.")
        headers = {k.strip().casefold(): k for k in reader.fieldnames}
        key_v = headers.get("vorname")
        key_n = headers.get("name")
        if not key_v or not key_n:
            raise SystemExit(
                f"CSV headers must include 'Vorname' and 'Name' (found: {list(headers.keys())})"
            )
        for row in reader:
            first = (row.get(key_v) or "").strip()
            last = (row.get(key_n) or "").strip()
            if not first and not last:
                continue
            full = f"{first} {last}".strip()
            names.add(normalize_to_tokens(full))
    return names


def read_db_names(db_path: Path) -> Tuple[Set[Tuple[str, ...]], sqlite3.Connection]:
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='dl_persons';"
    )
    if not cur.fetchone():
        conn.close()
        raise SystemExit("Table 'dl_persons' not found in the database.")
    try:
        cur.execute("SELECT rowid, name FROM dl_persons;")
    except sqlite3.OperationalError as e:
        conn.close()
        raise SystemExit(f"Error querying dl_persons.name: {e}")
    names = set()
    # We'll also return a mapping (rowid -> token tuple) later if needed for deletion
    # but here we just collect tokenized names
    for rowid, name_val in cur.fetchall():
        if name_val is None:
            continue
        names.add(normalize_to_tokens(name_val))
    return names, conn


def confirm(prompt: str) -> bool:
    ans = input(prompt + " [y/N]: ").strip().lower()
    return ans in ("y", "yes")


def delete_names_from_db(conn: sqlite3.Connection, tokens_to_delete: Set[Tuple[str, ...]]) -> int:
    """
    Delete rows from dl_persons whose normalized token tuple is in tokens_to_delete.
    We select all rows, normalize each name, compare, and delete matched rowids.
    """
    cur = conn.cursor()
    cur.execute("SELECT rowid, name FROM dl_persons;")
    to_delete_rowids = []
    for rowid, name_val in cur.fetchall():
        if name_val is None:
            continue
        if normalize_to_tokens(name_val) in tokens_to_delete:
            to_delete_rowids.append(rowid)
