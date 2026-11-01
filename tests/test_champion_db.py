"""Regression checks run only against isolated, disposable SQLite databases.

Usage: python test_champion_db.py [path/to/champion_db.py]
Or set CHAMPION_MODULE to select a prepared copy.
"""

import contextlib
import gc
import importlib.util
import io
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest


PACKAGED_MODULE = Path(__file__).resolve().parent.parent / "config/level_up_family/python/champion_db.py"
MODULE_PATH = Path(os.environ.get("CHAMPION_MODULE", str(PACKAGED_MODULE)))
if len(sys.argv) > 1 and sys.argv[1].endswith(".py"):
    MODULE_PATH = Path(sys.argv.pop(1))
spec = importlib.util.spec_from_file_location("champion_under_test", MODULE_PATH)
champion = importlib.util.module_from_spec(spec)
spec.loader.exec_module(champion)


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(
            prefix="level-up-family-test-", dir=Path(__file__).resolve().parent)
        self.addCleanup(self.temp.cleanup)
        # sqlite3's context manager commits but does not close the connection.
        # Collect released connection cycles before deleting fixtures on Windows.
        self.addCleanup(gc.collect)
        champion.BASE_DIR = Path(self.temp.name)
        champion.DB_PATH = champion.BASE_DIR / "test.db"
        self.call(champion.init_database)

    def call(self, function, *args, **kwargs):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            function(*args, **kwargs)
        return output.getvalue().strip()

    def json_call(self, function, *args, **kwargs):
        return json.loads(self.call(function, *args, **kwargs))

    def rows(self, query, params=()):
        with contextlib.closing(sqlite3.connect(champion.DB_PATH)) as conn:
            conn.row_factory = sqlite3.Row
            return [dict(row) for row in conn.execute(query, params)]

    def close_week(self, **changes):
        values = dict(player_key="player1", year=2026, iso_week=45,
                      week_start="2026-11-02", week_end="2026-11-08",
                      season_number=1, tasks_due=20, tasks_completed=18,
                      task_xp=180, perfect_days=4, bonus_xp=100,
                      penalty_xp=10, effective_xp=270, level_start=1,
                      level_end=2, weekly_goal_achieved=1,
                      daily_streak_end=2, weekly_streak_end=1)
        values.update(changes)
        return self.json_call(champion.close_week, **values)

    def test_init_seeds_players_without_duplicates(self):
        self.call(champion.init_database)
        rows = self.rows("SELECT player_key,display_name,active FROM players ORDER BY id")
        self.assertEqual(rows, [
            dict(player_key="player1", display_name="player1", active=1),
            dict(player_key="player2", display_name="player2", active=1)])

    def test_penalty_cancel_preserves_audit_record(self):
        self.call(champion.add_penalty, "player1", 25, 'Prueba "comillas" y ñ')
        row = self.rows("SELECT * FROM penalties")[0]
        self.assertEqual(row["amount"], 25)
        self.assertEqual(row["reason"], 'Prueba "comillas" y ñ')
        answer = self.json_call(champion.cancel_penalty, row["id"])
        self.assertEqual(answer["amount"], 25)
        row = self.rows("SELECT * FROM penalties")[0]
        self.assertEqual(row["cancelled"], 1)
        self.assertTrue(row["cancelled_at"])
        with self.assertRaises(SystemExit):
            self.call(champion.cancel_penalty, row["id"])
        self.assertEqual(len(self.rows("SELECT * FROM penalties")), 1)

    def test_unknown_or_inactive_player_does_not_write(self):
        with self.assertRaises(SystemExit):
            self.call(champion.add_penalty, "missing", 10, "test")
        with contextlib.closing(sqlite3.connect(champion.DB_PATH)) as conn:
            conn.execute("UPDATE players SET active=0 WHERE player_key='player2'")
            conn.commit()
        with self.assertRaises(SystemExit):
            self.call(champion.close_day, "player2", "2026-11-02", 1)
        self.assertFalse(self.rows("SELECT * FROM penalties"))
        self.assertFalse(self.rows("SELECT * FROM days"))

    def test_day_duplicate_is_idempotent(self):
        first = self.json_call(champion.close_day, "player1", "2026-11-02", 1)
        second = self.json_call(champion.close_day, "player1", "2026-11-02", 1)
        self.assertFalse(first["already_closed"])
        self.assertTrue(second["already_closed"])
        self.assertEqual(second["current_streak"], 1)
        self.assertEqual(len(self.rows("SELECT * FROM days")), 1)

    def test_daily_correction_recalculates_later_days(self):
        for day, perfect in [("2026-11-02", 1), ("2026-11-03", 0), ("2026-11-04", 1)]:
            self.json_call(champion.close_day, "player1", day, perfect)
        answer = self.json_call(champion.close_day, "player1", "2026-11-03", 1)
        self.assertTrue(answer["corrected"])
        self.assertEqual(answer["daily_streak_end"], 2)
        self.assertEqual(answer["current_streak"], 3)
        self.assertEqual([r["daily_streak_end"] for r in self.rows(
            "SELECT daily_streak_end FROM days ORDER BY day_date")], [1, 2, 3])

    def test_days_reject_invalid_date_and_flag_without_writes(self):
        for day, perfect in [("2026-02-30", 1), ("2026-11-02", 2), ("2026-11-02", "bad")]:
            with self.subTest(day=day, perfect=perfect), self.assertRaises(SystemExit):
                self.call(champion.close_day, "player1", day, perfect)
        self.assertFalse(self.rows("SELECT * FROM days"))

    def test_player_streaks_remain_independent(self):
        self.json_call(champion.close_day, "player1", "2026-11-02", 1)
        self.json_call(champion.close_day, "player2", "2026-11-02", 0)
        one = self.json_call(champion.close_day, "player1", "2026-11-03", 1)
        two = self.json_call(champion.close_day, "player2", "2026-11-03", 1)
        self.assertEqual((one["current_streak"], two["current_streak"]), (2, 1))

    def test_missing_calendar_day_breaks_streak(self):
        self.json_call(champion.close_day, "player1", "2026-11-02", 1)
        after_gap = self.json_call(champion.close_day, "player1", "2026-11-04", 1)
        consecutive = self.json_call(champion.close_day, "player1", "2026-11-05", 1)
        self.assertEqual(after_gap["current_streak"], 1)
        self.assertEqual(consecutive["current_streak"], 2)

    def test_week_baseline_requires_adjacent_calendar_day(self):
        self.close_week(player_key="player1", daily_streak_end=4)
        self.close_week(player_key="player2", daily_streak_end=4)
        adjacent = self.json_call(champion.close_day, "player1", "2026-11-09", 1)
        stale = self.json_call(champion.close_day, "player2", "2026-11-11", 1)
        self.assertEqual(adjacent["current_streak"], 5)
        self.assertEqual(stale["current_streak"], 1)

    def test_week_duplicate_never_double_counts_xp(self):
        first = self.close_week()
        second = self.close_week(effective_xp=999, tasks_completed=0)
        self.assertFalse(first["already_closed"])
        self.assertTrue(second["already_closed"])
        self.assertEqual(second["lifetime_xp"], 270)
        self.assertEqual(second["tasks_completed"], 18)
        self.assertEqual(len(self.rows("SELECT * FROM weeks")), 1)
        self.assertEqual(self.rows("SELECT effective_xp FROM years")[0]["effective_xp"], 270)

    def test_year_summary_aggregates_weeks_per_player(self):
        self.close_week()
        result = self.close_week(iso_week=46, week_start="2026-11-09",
                                 week_end="2026-11-15", tasks_completed=12,
                                 effective_xp=180, level_start=2, level_end=3,
                                 daily_streak_end=5, weekly_streak_end=2)
        self.close_week(player_key="player2", effective_xp=100)
        self.assertEqual(result["lifetime_xp"], 450)
        summary = self.rows("SELECT * FROM years WHERE player_id=1")[0]
        self.assertEqual(summary["weeks_played"], 2)
        self.assertEqual(summary["tasks_due"], 40)
        self.assertEqual(summary["tasks_completed"], 30)
        self.assertEqual(summary["completion_pct"], 75)
        self.assertEqual(summary["effective_xp"], 450)
        self.assertEqual((summary["level_start"], summary["level_end"]), (1, 3))
        self.assertEqual((summary["best_daily_streak"], summary["best_weekly_streak"]), (5, 2))

    def test_empty_week_avoids_division_by_zero(self):
        answer = self.close_week(tasks_due=0, tasks_completed=0)
        self.assertEqual(answer["completion_pct"], 0)
        self.assertEqual(self.rows("SELECT completion_pct FROM years")[0]["completion_pct"], 0)

    def test_delete_test_weeks_is_not_a_full_reset(self):
        self.close_week()
        self.close_week(year=2099, week_start="2099-11-02", week_end="2099-11-08")
        self.call(champion.add_penalty, "player1", 15, "test remains")
        self.json_call(champion.close_day, "player1", "2099-11-02", 1)
        answer = self.json_call(champion.delete_test_weeks)
        self.assertEqual((answer["deleted_weeks"], answer["deleted_years"]), (1, 1))
        self.assertEqual([r["year"] for r in self.rows("SELECT year FROM weeks")], [2026])
        self.assertEqual([r["year"] for r in self.rows("SELECT year FROM years")], [2026])
        self.assertEqual(len(self.rows("SELECT * FROM players")), 2)
        self.assertEqual(len(self.rows("SELECT * FROM penalties")), 1)
        self.assertEqual(len(self.rows("SELECT * FROM days")), 1)
        again = self.json_call(champion.delete_test_weeks)
        self.assertEqual((again["deleted_weeks"], again["deleted_years"]), (0, 0))


if __name__ == "__main__":
    unittest.main(verbosity=2)
