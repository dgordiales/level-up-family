#!/usr/bin/env python3

import json
import sqlite3
from contextlib import closing
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "champion.db"


def main():
    result = {
        "weeks_count": 0,
        "years_count": 0,
        "weeks": [],
        "years": [],
    }

    try:
        with closing(sqlite3.connect(DB_PATH.resolve().as_uri() + "?mode=ro", uri=True)) as conn:
            conn.row_factory = sqlite3.Row

            weeks = conn.execute(
                """
                SELECT
                    w.id AS week_id,
                    pl.player_key,
                    pl.display_name AS player_name,
                    pl.active AS player_active,
                    w.year,
                    w.iso_week,
                    w.week_start,
                    w.week_end,
                    w.season_number,
                    w.tasks_due,
                    w.tasks_completed,
                    w.completion_pct,
                    w.task_xp,
                    w.perfect_days,
                    w.bonus_xp,
                    w.penalty_xp,
                    w.effective_xp,
                    w.level_start,
                    w.level_end,
                    w.weekly_goal_achieved,
                    w.daily_streak_end,
                    w.weekly_streak_end,
                    w.closed_at
                FROM weeks w
                JOIN players pl ON pl.id = w.player_id
                ORDER BY w.year DESC, w.iso_week DESC, pl.id
                """
            ).fetchall()

            years = conn.execute(
                """
                SELECT
                    y.id AS year_id,
                    pl.player_key,
                    pl.display_name AS player_name,
                    pl.active AS player_active,
                    y.year,
                    y.weeks_played,
                    y.tasks_due,
                    y.tasks_completed,
                    y.completion_pct,
                    y.task_xp,
                    y.bonus_xp,
                    y.penalty_xp,
                    y.effective_xp,
                    y.perfect_days,
                    y.weekly_goals_achieved,
                    y.level_start,
                    y.level_end,
                    y.levels_gained,
                    y.seasons_completed,
                    y.best_daily_streak,
                    y.best_weekly_streak,
                    y.closed_at
                FROM years y
                JOIN players pl ON pl.id = y.player_id
                ORDER BY y.year DESC, pl.id
                """
            ).fetchall()

            result["weeks"] = [dict(row) for row in weeks]
            result["years"] = [dict(row) for row in years]
            result["weeks_count"] = len(result["weeks"])
            result["years_count"] = len(result["years"])

    except Exception as exc:
        result["error"] = str(exc)

    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
