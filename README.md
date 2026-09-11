# MuMaLab DoorLock

## Schema

```
                      +----+                                        
                      |    |                          +-----------+
                      |    |                          | RFID      | 
                      |    |                       +--+ Reader    | 
                      |    |                       |  +-----------+ 
  +--------------+    |    |    +---------------+  |                
  |              |    |    |    |               |  |  +-----------+ 
  | RaspberryPi  +----(UART)----+  Arduino      +--+--+ Keypad    | 
  |              |    |    |    |   (frontend)  |  |  +-----------+ 
  +------+-------+    |    |    +---------------+  |                
         |            |    |                       |  +-----------+ 
         |            |    |                       +--+ Display   | 
   +-----+------+     |    |                          +-----------+ 
   | Door lock  |     |    |                                        
   +------------+     |    |                                        
                      +----+                                        
```

## Database Management CLI

The backend ships with `backend/manage_db.py`, a small CLI helper around the `doorlock.db` SQLite database. It creates the schema on first run (by executing `doorlock.db.sql`) and offers person/token lifecycle tooling that mirrors the firmware expectations.

### Running the tool

``` bash
python backend/manage_db.py <entity> <action> [arguments]
```

- `entity`: `person` or `token`
- `action`: subcommand listed below
- Output is logged to stdout/stderr; tables leverage `prettytable`

### Person actions

| Action | Arguments | Description |
| --- | --- | --- |
| `create` | `name`, `group_id` | Adds a new member with `disabled=0` after ensuring the name is unique. |
| `remove` | `name` | Deletes the person record (and their tokens via FK constraints if configured). |
| `list` | – | Shows active and inactive members plus token counts using textual tables. |
| `enable` / `disable` | `name` | Toggles the `disabled` flag to allow/deny door access. |
| `rename` | `old_name`, `new_name` | Renames a person once uniqueness is verified. |
| `show` | `name` | Prints status (“ENABLED”/“DISABLED”) and enumerates stored tokens. |

Examples:

``` bash
# Create an active member in group 2
python backend/manage_db.py person create "Ada Lovelace" 2

# Disable temporary access
python backend/manage_db.py person disable "Ada Lovelace"
```

### Token actions

Tokens live on the `dl_tokens` table and are always tied to an existing person. PINs are stored as `sha256("<token>:<pin>")` hashes.

| Action | Arguments | Description |
| --- | --- | --- |
| `add` | `person`, `token`, `pin` | Verifies ownership, checks for duplicates, and inserts a token/PIN pair. |
| `reset` | `person`, `pin` | Re-hashes the stored PIN for the person’s sole token (multi-token reset is intentionally rejected). |
| `remove` | `token` | Removes the token entry after confirming it exists. |

Examples:

``` bash
# Link a RFID tag to Ada with PIN 0420
python backend/manage_db.py token add "Ada Lovelace" 12345678 0420

# Rotate the PIN for the only token Ada owns
python backend/manage_db.py token reset "Ada Lovelace" 8642
```

### Operational notes

- The script logs to the `manage_db` logger; use `--log-level DEBUG` via `PYTHONLOGGING` env if deeper tracing is required.
- Tables are auto-created the first time the script runs if `doorlock.db` is missing the required schema.
- Always run the CLI from the repository root so relative paths to `doorlock.db` and `doorlock.db.sql` resolve correctly.

## Membership Sync CLI

You can export a csv of the existing members by going to the google drive, "Finanzen und Mitglieder" -> "Mitglieder" and make sure you're on the first page of the sheet. Put that csv on the doorlockpi and run the script. The helper [backend/prune_cancelled_members.py](backend/prune_cancelled_members.py) enforces that `doorlock.db` only contains people from this csv, removing stragglers who should no longer have access.

### Usage

``` bash
python backend/prune_cancelled_members.py [--db path/to/doorlock.db] [--csv path/to/members.csv] [--dry-run] [--yes]
```

- Reads the CSV, builds full names (`Vorname` + `Name`), and treats that set as the source of truth.
- Prints members that appear in the CSV but not the database (for awareness) and highlights the active database entries that will be disabled. Already disabled members are ignored so they do not clutter the diff.
- Name matching is case-insensitive and normalizes umlauts/ß (`Söhnen` matches `Soehnen`, `Groß` matches `Gross`).
- When run without `--dry-run` or `--yes`, launches an interactive selector: use the arrow keys to move, `space` to toggle entries, and `Enter` to confirm.
- Use `--yes` to skip the selector and disable all stale members automatically.
- On confirmation it flips `dl_persons.disabled` to `1` for the selected entries (tokens remain but are unusable because the person is disabled).

## Rename Members CLI

For ad-hoc name corrections, use [backend/rename_members.py](backend/rename_members.py).

``` bash
python backend/rename_members.py [--db path/to/doorlock.db]
```

- TTY-only curses UI showing all members with status and token counts.
- Navigate with arrows, press `f` to search by name (case-insensitive), press `space` on a highlighted entry to rename: you will be prompted (outside the UI) for new last name, then first name, then confirmation showing old → new.
- If the name is unchanged or already taken, nothing is updated. Successful renames write directly to `dl_persons` and return you to the list.

Typical workflow:

``` bash
# Inspect differences without deleting
python backend/prune_cancelled_members.py --dry-run

# Apply the deletions after review
python backend/prune_cancelled_members.py --yes
```
