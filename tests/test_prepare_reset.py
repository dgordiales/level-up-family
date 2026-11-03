"""Meaningful reset checks against disposable SQLite fixtures only."""

from contextlib import closing
import importlib.util
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


reset = load("prepare_reset", HERE.parent / "config/level_up_family/python/prepare_reset.py")
luf = load("schema_source", Path(os.environ.get(
    "LUF_MODULE", str(HERE.parent / "config/level_up_family/python/luf_db.py"))))


class ResetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="reset-check-", dir=HERE)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.database = self.root / "fixture.db"
        self.backups = self.root / "backups"
        with closing(sqlite3.connect(self.database)) as conn:
            luf.create_schema(conn)
            luf.seed_players(conn)
            for player_id in (1, 2):
                conn.execute("INSERT INTO days(player_id,day_date,year,iso_week,iso_weekday,perfect,closed_at,updated_at) VALUES(?,'2026-10-26',2026,44,1,1,'test','test')", (player_id,))
                conn.execute("INSERT INTO weeks(player_id,year,iso_week,week_start,week_end,effective_xp,closed_at) VALUES(?,2026,44,'2026-10-26','2026-11-01',230,'test')", (player_id,))
                conn.execute("INSERT INTO years(player_id,year,effective_xp,closed_at) VALUES(?,2026,230,'test')", (player_id,))
                conn.execute("INSERT INTO penalties(player_id,penalty_date,year,iso_week,amount,reason,created_at) VALUES(?,'2026-10-26',2026,44,10,'test','test')", (player_id,))
            conn.commit()

    def dump(self, path=None):
        with closing(sqlite3.connect(path or self.database)) as conn:
            return list(conn.iterdump())

    def run_reset(self, **kwargs):
        return reset.prepare_reset(self.database, "2026-11-02", **kwargs)

    def test_missing_database_does_not_create_database_or_directory(self):
        missing = self.root / "absent" / "missing.db"
        with self.assertRaises(FileNotFoundError):
            reset.prepare_reset(missing, "2026-11-02")
        self.assertFalse(missing.parent.exists())

    def test_simulation_preserves_bytes_and_creates_no_backup(self):
        before = self.database.read_bytes()
        plan = self.run_reset(backup_directory=self.backups)
        self.assertEqual(plan["mode"], "simulation")
        self.assertEqual(plan["delete_counts"], {table: 2 for table in reset.ACTIVITY_TABLES})
        self.assertEqual(plan["players_preserved"], 2)
        self.assertEqual(self.database.read_bytes(), before)
        self.assertFalse(self.backups.exists())

    def test_season_end_is_inclusive_28_days(self):
        season = self.run_reset()["proposed_season"]
        self.assertEqual(season, {"start_date": "2026-11-02", "duration_days": 28,
                                  "last_active_date": "2026-11-29", "end_exclusive": "2026-11-30"})

    def test_apply_requires_backup_directory_and_does_not_mutate(self):
        before = self.dump()
        with self.assertRaisesRegex(ValueError, "backup-directory"):
            self.run_reset(apply=True)
        self.assertEqual(self.dump(), before)

    def test_apply_clears_activity_preserves_players_ids_and_sequences_and_backup(self):
        before = self.dump()
        with closing(sqlite3.connect(self.database)) as conn:
            players = conn.execute("SELECT * FROM players ORDER BY id").fetchall()
            sequences = conn.execute("SELECT * FROM sqlite_sequence ORDER BY name").fetchall()
        result = self.run_reset(apply=True, backup_directory=self.backups)
        self.assertEqual(self.dump(Path(result["backup"])), before)
        with closing(sqlite3.connect(self.database)) as conn:
            for table in reset.ACTIVITY_TABLES:
                self.assertEqual(conn.execute('SELECT COUNT(*) FROM "' + table + '"').fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT * FROM players ORDER BY id").fetchall(), players)
            self.assertEqual(conn.execute("SELECT * FROM sqlite_sequence ORDER BY name").fetchall(), sequences)
            self.assertEqual(conn.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            # Penalty identities are never recycled into old UI selections.
            conn.execute("INSERT INTO penalties(player_id,penalty_date,year,iso_week,amount,reason,created_at) VALUES(1,'2026-11-02',2026,45,10,'new','test')")
            self.assertEqual(conn.execute("SELECT id FROM penalties").fetchone()[0], 3)
        self.assertFalse(result["ha_helpers_reset"])
        self.assertFalse(result["production_launched"])

    def test_backup_failure_leaves_database_intact(self):
        before = self.dump()
        self.backups.write_text("not a directory")
        with self.assertRaises(OSError):
            self.run_reset(apply=True, backup_directory=self.backups)
        self.assertEqual(self.dump(), before)

    def test_failed_backup_validation_leaves_database_intact(self):
        before = self.dump()
        real_validate = reset.validate_schema
        calls = []
        def validate(conn):
            calls.append(1)
            if len(calls) == 2:
                raise ValueError("simulated backup validation failure")
            return real_validate(conn)
        with patch.object(reset, "validate_schema", side_effect=validate):
            with self.assertRaisesRegex(ValueError, "backup validation"):
                self.run_reset(apply=True, backup_directory=self.backups)
        self.assertEqual(self.dump(), before)
        self.assertEqual(list(self.backups.iterdir()), [])

    def test_invalid_dates_fail_without_mutation_or_backup_directory(self):
        before = self.dump()
        for invalid in ("2026-02-30", "20261102", "2026-W45-1", "9999-12-31", "tomorrow"):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                reset.prepare_reset(self.database, invalid, True, self.backups)
        self.assertEqual(self.dump(), before)
        self.assertFalse(self.backups.exists())

    def test_post_delete_failure_rolls_back_all_activity(self):
        before = self.dump()
        real_validate = reset.validate_schema
        calls = []
        def validate(conn):
            calls.append(1)
            if len(calls) == 3:
                raise ValueError("simulated post-delete failure")
            return real_validate(conn)
        with patch.object(reset, "validate_schema", side_effect=validate):
            with self.assertRaisesRegex(ValueError, "post-delete failure"):
                self.run_reset(apply=True, backup_directory=self.backups)
        self.assertEqual(self.dump(), before)
        backup_files = list(self.backups.iterdir())
        self.assertEqual(len(backup_files), 1)
        self.assertEqual(self.dump(backup_files[0]), before)

    def test_unknown_schema_refused_before_backup(self):
        with closing(sqlite3.connect(self.database)) as conn:
            conn.execute("CREATE TABLE unknown_data (id INTEGER)")
            conn.commit()
        before = self.dump()
        with self.assertRaisesRegex(ValueError, "Unrecognized database tables"):
            self.run_reset(apply=True, backup_directory=self.backups)
        self.assertEqual(self.dump(), before)
        self.assertFalse(self.backups.exists())

    def test_triggers_refused_before_backup(self):
        with closing(sqlite3.connect(self.database)) as conn:
            conn.execute("CREATE TRIGGER surprise AFTER DELETE ON penalties BEGIN DELETE FROM players; END")
            conn.commit()
        before = self.dump()
        with self.assertRaisesRegex(ValueError, "triggers"):
            self.run_reset(apply=True, backup_directory=self.backups)
        self.assertEqual(self.dump(), before)

    def test_backup_obtained_under_write_lock_including_wal(self):
        with closing(sqlite3.connect(self.database)) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
        real_backup = reset.create_backup
        def guarded_backup(database, directory):
            with closing(sqlite3.connect(database, timeout=0)) as competing_writer:
                with self.assertRaisesRegex(sqlite3.OperationalError, "locked"):
                    competing_writer.execute("DELETE FROM days")
            return real_backup(database, directory)
        with patch.object(reset, "create_backup", side_effect=guarded_backup):
            result = self.run_reset(apply=True, backup_directory=self.backups)
        self.assertTrue(Path(result["backup"]).is_file())


if __name__ == "__main__":
    unittest.main(verbosity=2)
