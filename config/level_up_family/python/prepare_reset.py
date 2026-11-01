#!/usr/bin/env python3
"""Plan or perform an offline, backed-up activity reset. Does not call HA.

Stop Home Assistant and other database writers before applying, and separately
save/reset HA helpers. A database reset alone is NOT a production launch.
"""

import argparse
from contextlib import closing
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
import sys
import uuid


ACTIVITY_TABLES = ("days", "weeks", "years", "penalties")
EXPECTED_COLUMNS = {
    "players": "id player_key display_name active created_at",
    "days": "id player_id day_date year iso_week iso_weekday perfect daily_streak_end closed_at updated_at",
    "weeks": "id player_id year iso_week week_start week_end season_number tasks_due tasks_completed completion_pct task_xp perfect_days bonus_xp penalty_xp effective_xp level_start level_end weekly_goal_achieved daily_streak_end weekly_streak_end closed_at",
    "years": "id player_id year weeks_played tasks_due tasks_completed completion_pct task_xp bonus_xp penalty_xp effective_xp perfect_days weekly_goals_achieved level_start level_end levels_gained seasons_completed best_daily_streak best_weekly_streak closed_at",
    "penalties": "id player_id penalty_date year iso_week amount reason cancelled cancelled_at created_at",
}
NOTICE = (
    "Database activity only: Home Assistant helpers have NOT been reset. "
    "This operation does NOT start a season or put the app into production. "
    "Stop HA and other writers before applying; reset and verify helpers separately."
)


def parse_start_date(value):
    try:
        parsed = date.fromisoformat(value)
        if parsed.isoformat() != value:
            raise ValueError()
        # Validate the end boundary before any files can be touched.
        parsed + timedelta(days=28)
        return parsed
    except (ValueError, OverflowError) as exc:
        raise ValueError("start-date must be a valid YYYY-MM-DD with room for 28 days") from exc


def open_existing(path, mode):
    conn = sqlite3.connect(path.as_uri() + "?mode=" + mode, uri=True, timeout=5)
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def validate_schema(conn):
    tables = {row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )}
    if tables != set(EXPECTED_COLUMNS):
        raise ValueError("Unrecognized database tables; refusing reset")
    if conn.execute("SELECT 1 FROM sqlite_master WHERE type='trigger' LIMIT 1").fetchone():
        raise ValueError("Database contains triggers; refusing reset")
    for table, expected in EXPECTED_COLUMNS.items():
        actual = [row[1] for row in conn.execute('PRAGMA table_info("' + table + '")')]
        if actual != expected.split():
            raise ValueError("Unrecognized columns in " + table + "; refusing reset")
        foreign_keys = list(conn.execute('PRAGMA foreign_key_list("' + table + '")'))
        if table == "players":
            if foreign_keys:
                raise ValueError("Unexpected players foreign keys; refusing reset")
        elif len(foreign_keys) != 1 or foreign_keys[0][2:5] != ("players", "player_id", "id"):
            raise ValueError("Unexpected foreign keys in " + table + "; refusing reset")
    if conn.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
        raise ValueError("Database integrity check failed")
    if conn.execute("PRAGMA foreign_key_check").fetchone():
        raise ValueError("Database foreign key check failed")


def make_plan(conn, database, start):
    return {
        "ok": True,
        "mode": "simulation",
        "database": str(database),
        "delete_counts": {
            table: conn.execute('SELECT COUNT(*) FROM "' + table + '"').fetchone()[0]
            for table in ACTIVITY_TABLES
        },
        "players_preserved": conn.execute("SELECT COUNT(*) FROM players").fetchone()[0],
        "preserve_player_ids": True,
        "preserve_id_sequences": True,
        "proposed_season": {
            "start_date": start.isoformat(),
            "duration_days": 28,
            "last_active_date": (start + timedelta(days=27)).isoformat(),
            "end_exclusive": (start + timedelta(days=28)).isoformat(),
        },
        "ha_helpers_reset": False,
        "production_launched": False,
        "notice": NOTICE,
    }


def create_backup(database, directory):
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup = directory / ("activity_before_reset_" + stamp + "_" + uuid.uuid4().hex[:8] + ".db")
    # A second read connection can read while the caller holds BEGIN IMMEDIATE.
    # Calling backup() on the write-transaction connection itself can deadlock.
    try:
        with closing(open_existing(database, "ro")) as source:
            with closing(sqlite3.connect(backup)) as target:
                source.backup(target)
                validate_schema(target)
        return backup
    except BaseException:
        if backup.exists():
            backup.unlink()
        raise


def prepare_reset(database, start_date, apply=False, backup_directory=None):
    start = parse_start_date(start_date)
    database = Path(database).expanduser().resolve(strict=True)
    if not database.is_file():
        raise ValueError("Database must be an existing file")
    if apply and not backup_directory:
        raise ValueError("--apply requires --backup-directory")
    with closing(open_existing(database, "rw" if apply else "ro")) as conn:
        if not apply:
            # One consistent snapshot for schema, counts and integrity.
            conn.execute("BEGIN")
            try:
                validate_schema(conn)
                return make_plan(conn, database, start)
            finally:
                conn.rollback()
        conn.execute("BEGIN IMMEDIATE")
        try:
            validate_schema(conn)
            plan = make_plan(conn, database, start)
            players = conn.execute("SELECT * FROM players ORDER BY id").fetchall()
            sequences = conn.execute("SELECT * FROM sqlite_sequence ORDER BY name").fetchall()
            backup = create_backup(database, Path(backup_directory).expanduser().resolve())
            for table in ACTIVITY_TABLES:
                conn.execute('DELETE FROM "' + table + '"')
            if conn.execute("SELECT * FROM players ORDER BY id").fetchall() != players:
                raise RuntimeError("Player preservation verification failed")
            if conn.execute("SELECT * FROM sqlite_sequence ORDER BY name").fetchall() != sequences:
                raise RuntimeError("ID sequence preservation verification failed")
            validate_schema(conn)
            conn.commit()
            plan.update(mode="applied_database_only", backup=str(backup))
            return plan
        except BaseException:
            conn.rollback()
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True, help="Existing SQLite database; never auto-created")
    parser.add_argument("--start-date", required=True, help="Proposed YYYY-MM-DD; no HA date is changed")
    parser.add_argument("--apply", action="store_true", help="Delete activity only after verified backup")
    parser.add_argument("--backup-directory", help="Required with --apply")
    args = parser.parse_args()
    try:
        result = prepare_reset(args.database, args.start_date, args.apply, args.backup_directory)
    except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
        print(json.dumps({"ok": False, "error": str(exc), "ha_helpers_reset": False,
                          "production_launched": False}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
