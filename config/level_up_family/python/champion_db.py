#!/usr/bin/env python3

import sqlite3
from contextlib import contextmanager
import sys
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

BASE_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = BASE_DIR / "champion.db"


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def connect():
    BASE_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row

    try:
        with conn:
            yield conn
    finally:
        conn.close()


def create_schema(conn):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_key TEXT NOT NULL UNIQUE,
            display_name TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
            created_at TEXT NOT NULL
        );


        CREATE TABLE IF NOT EXISTS weeks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            player_id INTEGER NOT NULL,

            year INTEGER NOT NULL,
            iso_week INTEGER NOT NULL,

            week_start TEXT NOT NULL,
            week_end TEXT NOT NULL,

            season_number INTEGER,

            tasks_due INTEGER NOT NULL DEFAULT 0,
            tasks_completed INTEGER NOT NULL DEFAULT 0,
            completion_pct REAL NOT NULL DEFAULT 0,

            task_xp INTEGER NOT NULL DEFAULT 0,
            perfect_days INTEGER NOT NULL DEFAULT 0,
            bonus_xp INTEGER NOT NULL DEFAULT 0,

            penalty_xp INTEGER NOT NULL DEFAULT 0,
            effective_xp INTEGER NOT NULL DEFAULT 0,

            level_start INTEGER NOT NULL DEFAULT 1,
            level_end INTEGER NOT NULL DEFAULT 1,

            weekly_goal_achieved INTEGER NOT NULL DEFAULT 0
                CHECK (weekly_goal_achieved IN (0, 1)),

            daily_streak_end INTEGER NOT NULL DEFAULT 0,
            weekly_streak_end INTEGER NOT NULL DEFAULT 0,

            closed_at TEXT NOT NULL,

            FOREIGN KEY (player_id)
                REFERENCES players(id)
                ON DELETE CASCADE,

            UNIQUE (player_id, year, iso_week)
        );


        CREATE TABLE IF NOT EXISTS days (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER NOT NULL,
            day_date TEXT NOT NULL,
            year INTEGER NOT NULL,
            iso_week INTEGER NOT NULL,
            iso_weekday INTEGER NOT NULL,
            perfect INTEGER NOT NULL DEFAULT 0 CHECK (perfect IN (0, 1)),
            daily_streak_end INTEGER NOT NULL DEFAULT 0,
            closed_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE,
            UNIQUE (player_id, day_date)
        );

        CREATE TABLE IF NOT EXISTS penalties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            player_id INTEGER NOT NULL,

            penalty_date TEXT NOT NULL,

            year INTEGER NOT NULL,
            iso_week INTEGER NOT NULL,

            amount INTEGER NOT NULL,
            reason TEXT NOT NULL,

            cancelled INTEGER NOT NULL DEFAULT 0
                CHECK (cancelled IN (0, 1)),

            cancelled_at TEXT,

            created_at TEXT NOT NULL,

            FOREIGN KEY (player_id)
                REFERENCES players(id)
                ON DELETE CASCADE
        );


        CREATE TABLE IF NOT EXISTS years (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            player_id INTEGER NOT NULL,
            year INTEGER NOT NULL,

            weeks_played INTEGER NOT NULL DEFAULT 0,

            tasks_due INTEGER NOT NULL DEFAULT 0,
            tasks_completed INTEGER NOT NULL DEFAULT 0,
            completion_pct REAL NOT NULL DEFAULT 0,

            task_xp INTEGER NOT NULL DEFAULT 0,
            bonus_xp INTEGER NOT NULL DEFAULT 0,
            penalty_xp INTEGER NOT NULL DEFAULT 0,
            effective_xp INTEGER NOT NULL DEFAULT 0,

            perfect_days INTEGER NOT NULL DEFAULT 0,
            weekly_goals_achieved INTEGER NOT NULL DEFAULT 0,

            level_start INTEGER NOT NULL DEFAULT 1,
            level_end INTEGER NOT NULL DEFAULT 1,
            levels_gained INTEGER NOT NULL DEFAULT 0,

            seasons_completed INTEGER NOT NULL DEFAULT 0,

            best_daily_streak INTEGER NOT NULL DEFAULT 0,
            best_weekly_streak INTEGER NOT NULL DEFAULT 0,

            closed_at TEXT NOT NULL,

            FOREIGN KEY (player_id)
                REFERENCES players(id)
                ON DELETE CASCADE,

            UNIQUE (player_id, year)
        );


        CREATE INDEX IF NOT EXISTS idx_weeks_player_year
            ON weeks(player_id, year);

        CREATE INDEX IF NOT EXISTS idx_days_player_date
            ON days(player_id, day_date);

        CREATE INDEX IF NOT EXISTS idx_days_player_week
            ON days(player_id, year, iso_week);


        CREATE INDEX IF NOT EXISTS idx_penalties_player_week
            ON penalties(player_id, year, iso_week);


        CREATE INDEX IF NOT EXISTS idx_penalties_cancelled
            ON penalties(cancelled);


        CREATE INDEX IF NOT EXISTS idx_years_player
            ON years(player_id);
        """
    )


def seed_players(conn):
    players = [
        ("player1", "player1"),
        ("player2", "player2"),
    ]

    for player_key, display_name in players:
        conn.execute(
            """
            INSERT INTO players (
                player_key,
                display_name,
                created_at
            )
            VALUES (?, ?, ?)
            ON CONFLICT(player_key) DO NOTHING
            """,
            (
                player_key,
                display_name,
                utc_now(),
            ),
        )


def init_database():
    with connect() as conn:
        create_schema(conn)
        seed_players(conn)
        conn.commit()

    print(f"OK: database initialized at {DB_PATH}")


def show_players():
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, player_key, display_name, active
            FROM players
            ORDER BY id
            """
        ).fetchall()

    for row in rows:
        print(
            f"{row['id']} | "
            f"{row['player_key']} | "
            f"{row['display_name']} | "
            f"active={row['active']}"
        )


def add_penalty(player_key, amount, reason):
    now = datetime.now()
    iso = now.isocalendar()

    year = iso.year
    iso_week = iso.week
    penalty_date = now.date().isoformat()

    with connect() as conn:
        player = conn.execute(
            """
            SELECT id
            FROM players
            WHERE player_key = ?
              AND active = 1
            """,
            (player_key,),
        ).fetchone()

        if player is None:
            print(f"ERROR: player not found or inactive: {player_key}")
            sys.exit(1)

        cursor = conn.execute(
            """
            INSERT INTO penalties (
                player_id,
                penalty_date,
                year,
                iso_week,
                amount,
                reason,
                cancelled,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, 0, ?)
            """,
            (
                player["id"],
                penalty_date,
                year,
                iso_week,
                amount,
                reason,
                utc_now(),
            ),
        )

        penalty_id = cursor.lastrowid

        conn.commit()

    print(
        f"OK: penalty #{penalty_id} added | "
        f"{player_key} | -{amount} XP | {reason}"
    )


def show_penalties():
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                p.id,
                pl.display_name,
                p.penalty_date,
                p.year,
                p.iso_week,
                p.amount,
                p.reason,
                p.cancelled
            FROM penalties p
            JOIN players pl
                ON pl.id = p.player_id
            ORDER BY p.id DESC
            """
        ).fetchall()

    if not rows:
        print("No penalties registered.")
        return

    for row in rows:
        status = "CANCELLED" if row["cancelled"] else "ACTIVE"

        print(
            f"#{row['id']} | "
            f"{row['display_name']} | "
            f"{row['penalty_date']} | "
            f"{row['year']}-W{row['iso_week']:02d} | "
            f"-{row['amount']} XP | "
            f"{row['reason']} | "
            f"{status}"
        )

def cancel_penalty(penalty_id):
    with connect() as conn:
        
        penalty = conn.execute(
            """
            SELECT
                p.id,
                p.amount,
                p.cancelled,
                pl.player_key,
                pl.display_name
            FROM penalties p
            JOIN players pl
                ON pl.id = p.player_id
            WHERE p.id = ?
            """,
            (penalty_id,),
        ).fetchone()

        if penalty is None:
            print(f"ERROR: penalty #{penalty_id} not found.")
            sys.exit(1)

        if penalty["cancelled"]:
            print(f"ERROR: penalty #{penalty_id} is already cancelled.")
            sys.exit(1)

        conn.execute(
            """
            UPDATE penalties
            SET cancelled = 1,
                cancelled_at = ?
            WHERE id = ?
            """,
            (
                utc_now(),
                penalty_id,
            ),
        )

        conn.commit()

    print(
        '{"penalty_id": %d, "player_key": "%s", "amount": %d}'
        % (
            penalty_id,
            penalty["player_key"],
            penalty["amount"],
        )
    )

def close_week(
    player_key,
    year,
    iso_week,
    week_start,
    week_end,
    season_number,
    tasks_due,
    tasks_completed,
    task_xp,
    perfect_days,
    bonus_xp,
    penalty_xp,
    effective_xp,
    level_start,
    level_end,
    weekly_goal_achieved,
    daily_streak_end,
    weekly_streak_end,
):
    # Normalizamos los valores recibidos
    year = int(year)
    iso_week = int(iso_week)
    season_number = int(season_number)

    tasks_due = int(tasks_due)
    tasks_completed = int(tasks_completed)

    task_xp = int(task_xp)
    perfect_days = int(perfect_days)
    bonus_xp = int(bonus_xp)
    penalty_xp = int(penalty_xp)
    effective_xp = int(effective_xp)

    level_start = int(level_start)
    level_end = int(level_end)

    weekly_goal_achieved = int(weekly_goal_achieved)
    daily_streak_end = int(daily_streak_end)
    weekly_streak_end = int(weekly_streak_end)

    if tasks_due > 0:
        completion_pct = round(
            (tasks_completed / tasks_due) * 100,
            2,
        )
    else:
        completion_pct = 0

    with connect() as conn:
        # ==================================================
        # 1. LOCALIZAR JUGADOR
        # ==================================================

        player = conn.execute(
            """
            SELECT id, display_name
            FROM players
            WHERE player_key = ?
              AND active = 1
            """,
            (player_key,),
        ).fetchone()

        if not player:
            print(json.dumps({
                "ok": False,
                "error": "player_not_found",
                "player_key": player_key,
            }))
            raise SystemExit(1)

        player_id = player["id"]

        # ==================================================
        # 2. COMPROBAR SI LA SEMANA YA EXISTE
        # ==================================================

        existing = conn.execute(
            """
            SELECT *
            FROM weeks
            WHERE player_id = ?
              AND year = ?
              AND iso_week = ?
            """,
            (
                player_id,
                year,
                iso_week,
            ),
        ).fetchone()

        if existing:
            # El XP histórico se calcula siempre desde SQLite.
            lifetime_xp = conn.execute(
                """
                SELECT COALESCE(SUM(effective_xp), 0)
                FROM weeks
                WHERE player_id = ?
                """,
                (player_id,),
            ).fetchone()[0]

            print(json.dumps({
                "ok": True,
                "already_closed": True,
                "player_key": player_key,
                "year": year,
                "iso_week": iso_week,
                "week_id": existing["id"],
                "tasks_due": existing["tasks_due"],
                "tasks_completed": existing["tasks_completed"],
                "completion_pct": existing["completion_pct"],
                "task_xp": existing["task_xp"],
                "perfect_days": existing["perfect_days"],
                "bonus_xp": existing["bonus_xp"],
                "penalty_xp": existing["penalty_xp"],
                "effective_xp": existing["effective_xp"],
                "lifetime_xp": lifetime_xp,
                "level_start": existing["level_start"],
                "level_end": existing["level_end"],
                "weekly_goal_achieved":
                    existing["weekly_goal_achieved"],
                "daily_streak_end":
                    existing["daily_streak_end"],
                "weekly_streak_end":
                    existing["weekly_streak_end"],
                "closed_at": existing["closed_at"],
            }))
            return

        # ==================================================
        # 3. SEMANA NUEVA: GUARDARLA
        # ==================================================

        closed_at = utc_now()

        cursor = conn.execute(
            """
            INSERT INTO weeks (
                player_id,
                year,
                iso_week,
                week_start,
                week_end,
                season_number,
                tasks_due,
                tasks_completed,
                completion_pct,
                task_xp,
                perfect_days,
                bonus_xp,
                penalty_xp,
                effective_xp,
                level_start,
                level_end,
                weekly_goal_achieved,
                daily_streak_end,
                weekly_streak_end,
                closed_at
            )
            VALUES (
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?,
                ?, ?
            )
            """,
            (
                player_id,
                year,
                iso_week,
                week_start,
                week_end,
                season_number,
                tasks_due,
                tasks_completed,
                completion_pct,
                task_xp,
                perfect_days,
                bonus_xp,
                penalty_xp,
                effective_xp,
                level_start,
                level_end,
                weekly_goal_achieved,
                daily_streak_end,
                weekly_streak_end,
                closed_at,
            ),
        )

        week_id = cursor.lastrowid

        # ==================================================
        # 4. ACTUALIZAR RESUMEN ANUAL
        # ==================================================
        rebuild_year_summary(conn, player_id, year)

        # ==================================================
        # 5. XP HISTÓRICO DESPUÉS DEL CIERRE
        # ==================================================

        lifetime_xp = conn.execute(
            """
            SELECT COALESCE(SUM(effective_xp), 0)
            FROM weeks
            WHERE player_id = ?
            """,
            (player_id,),
        ).fetchone()[0]

        # ==================================================
        # 5. RESPUESTA
        # ==================================================

        print(json.dumps({
            "ok": True,
            "already_closed": False,
            "player_key": player_key,
            "year": year,
            "iso_week": iso_week,
            "week_id": week_id,
            "tasks_due": tasks_due,
            "tasks_completed": tasks_completed,
            "completion_pct": completion_pct,
            "task_xp": task_xp,
            "perfect_days": perfect_days,
            "bonus_xp": bonus_xp,
            "penalty_xp": penalty_xp,
            "effective_xp": effective_xp,
            "lifetime_xp": lifetime_xp,
            "level_start": level_start,
            "level_end": level_end,
            "weekly_goal_achieved": weekly_goal_achieved,
            "daily_streak_end": daily_streak_end,
            "weekly_streak_end": weekly_streak_end,
            "closed_at": closed_at,
        }))




def _active_player(conn, player_key):
    row = conn.execute(
        "SELECT id, player_key, display_name FROM players WHERE player_key=? AND active=1",
        (player_key,),
    ).fetchone()
    if row is None:
        print(json.dumps({"ok": False, "error": "player_not_found", "player_key": player_key}))
        raise SystemExit(1)
    return row


def _parse_day(day_date):
    try:
        return datetime.strptime(day_date, "%Y-%m-%d").date()
    except ValueError:
        print(json.dumps({"ok": False, "error": "invalid_date", "day_date": day_date}))
        raise SystemExit(1)


def _daily_baseline(conn, player_id):
    first = conn.execute(
        "SELECT day_date FROM days WHERE player_id=? ORDER BY day_date LIMIT 1",
        (player_id,),
    ).fetchone()

    if first is None:
        row = conn.execute(
            """SELECT daily_streak_end FROM weeks
               WHERE player_id=?
               ORDER BY year DESC, iso_week DESC LIMIT 1""",
            (player_id,),
        ).fetchone()
    else:
        row = conn.execute(
            """SELECT daily_streak_end FROM weeks
               WHERE player_id=? AND week_end = ?
               ORDER BY year DESC, iso_week DESC LIMIT 1""",
            (player_id, (datetime.strptime(first["day_date"], "%Y-%m-%d").date() - timedelta(days=1)).isoformat()),
        ).fetchone()

    return int(row["daily_streak_end"]) if row else 0


def recalculate_daily_streaks(conn, player_id):
    streak = _daily_baseline(conn, player_id)
    rows = conn.execute(
        "SELECT id, day_date, perfect FROM days WHERE player_id=? ORDER BY day_date",
        (player_id,),
    ).fetchall()

    previous_day = None
    for row in rows:
        day = datetime.strptime(row["day_date"], "%Y-%m-%d").date()
        if previous_day is not None and day != previous_day + timedelta(days=1):
            streak = 0
        streak = streak + 1 if int(row["perfect"]) == 1 else 0
        previous_day = day
        conn.execute(
            "UPDATE days SET daily_streak_end=?, updated_at=? WHERE id=?",
            (streak, utc_now(), row["id"]),
        )
    return streak


def close_day(player_key, day_date, perfect):
    day = _parse_day(day_date)
    try:
        perfect = int(perfect)
    except ValueError:
        perfect = -1
    if perfect not in (0, 1):
        print(json.dumps({"ok": False, "error": "invalid_perfect", "expected": "0 or 1"}))
        raise SystemExit(1)

    iso = day.isocalendar()
    now = utc_now()

    with connect() as conn:
        player = _active_player(conn, player_key)
        existing = conn.execute(
            "SELECT id, perfect FROM days WHERE player_id=? AND day_date=?",
            (player["id"], day.isoformat()),
        ).fetchone()

        if existing is None:
            conn.execute(
                """INSERT INTO days
                   (player_id, day_date, year, iso_week, iso_weekday, perfect,
                    daily_streak_end, closed_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)""",
                (player["id"], day.isoformat(), iso.year, iso.week, iso.weekday,
                 perfect, now, now),
            )
            already_closed = False
            corrected = False
        else:
            old = int(existing["perfect"])
            conn.execute(
                """UPDATE days SET year=?, iso_week=?, iso_weekday=?, perfect=?,
                   updated_at=? WHERE id=?""",
                (iso.year, iso.week, iso.weekday, perfect, now, existing["id"]),
            )
            already_closed = old == perfect
            corrected = old != perfect

        current_streak = recalculate_daily_streaks(conn, player["id"])
        row = conn.execute(
            "SELECT * FROM days WHERE player_id=? AND day_date=?",
            (player["id"], day.isoformat()),
        ).fetchone()
        conn.commit()

    print(json.dumps({
        "ok": True, "player_key": player_key, "day_date": row["day_date"],
        "perfect": row["perfect"], "daily_streak_end": row["daily_streak_end"],
        "current_streak": current_streak, "already_closed": already_closed,
        "corrected": corrected
    }))


def show_days(player_key=None):
    with connect() as conn:
        if player_key:
            player = _active_player(conn, player_key)
            rows = conn.execute(
                """SELECT d.*, p.display_name FROM days d JOIN players p ON p.id=d.player_id
                   WHERE d.player_id=? ORDER BY d.day_date DESC""",
                (player["id"],),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT d.*, p.display_name FROM days d JOIN players p ON p.id=d.player_id
                   ORDER BY d.day_date DESC, p.id"""
            ).fetchall()

    if not rows:
        print("No closed days.")
        return

    for r in rows:
        print(
            f"#{r['id']} | {r['display_name']} | {r['day_date']} | "
            f"{r['year']}-W{r['iso_week']:02d} D{r['iso_weekday']} | "
            f"perfect={'YES' if r['perfect'] else 'NO'} | streak={r['daily_streak_end']}"
        )


def rebuild_year_summary(conn, player_id, year):
    """Recalcula el resumen anual a partir de las semanas cerradas."""
    rows = conn.execute(
        """
        SELECT *
        FROM weeks
        WHERE player_id = ? AND year = ?
        ORDER BY iso_week
        """,
        (player_id, year),
    ).fetchall()

    if not rows:
        conn.execute(
            "DELETE FROM years WHERE player_id = ? AND year = ?",
            (player_id, year),
        )
        return

    weeks_played = len(rows)
    tasks_due = sum(int(r["tasks_due"]) for r in rows)
    tasks_completed = sum(int(r["tasks_completed"]) for r in rows)
    completion_pct = round(
        (tasks_completed / tasks_due) * 100, 2
    ) if tasks_due else 0

    task_xp = sum(int(r["task_xp"]) for r in rows)
    bonus_xp = sum(int(r["bonus_xp"]) for r in rows)
    penalty_xp = sum(int(r["penalty_xp"]) for r in rows)
    effective_xp = sum(int(r["effective_xp"]) for r in rows)
    perfect_days = sum(int(r["perfect_days"]) for r in rows)
    weekly_goals_achieved = sum(int(r["weekly_goal_achieved"]) for r in rows)

    level_start = int(rows[0]["level_start"])
    level_end = int(rows[-1]["level_end"])
    levels_gained = max(level_end - level_start, 0)

    seasons_completed = len({
        int(r["season_number"])
        for r in rows
        if r["season_number"] is not None
    })

    best_daily_streak = max(
        (int(r["daily_streak_end"]) for r in rows), default=0
    )
    best_weekly_streak = max(
        (int(r["weekly_streak_end"]) for r in rows), default=0
    )

    conn.execute(
        """
        INSERT INTO years (
            player_id, year, weeks_played, tasks_due, tasks_completed,
            completion_pct, task_xp, bonus_xp, penalty_xp, effective_xp,
            perfect_days, weekly_goals_achieved, level_start, level_end,
            levels_gained, seasons_completed, best_daily_streak,
            best_weekly_streak, closed_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(player_id, year) DO UPDATE SET
            weeks_played=excluded.weeks_played,
            tasks_due=excluded.tasks_due,
            tasks_completed=excluded.tasks_completed,
            completion_pct=excluded.completion_pct,
            task_xp=excluded.task_xp,
            bonus_xp=excluded.bonus_xp,
            penalty_xp=excluded.penalty_xp,
            effective_xp=excluded.effective_xp,
            perfect_days=excluded.perfect_days,
            weekly_goals_achieved=excluded.weekly_goals_achieved,
            level_start=excluded.level_start,
            level_end=excluded.level_end,
            levels_gained=excluded.levels_gained,
            seasons_completed=excluded.seasons_completed,
            best_daily_streak=excluded.best_daily_streak,
            best_weekly_streak=excluded.best_weekly_streak,
            closed_at=excluded.closed_at
        """,
        (
            player_id, year, weeks_played, tasks_due, tasks_completed,
            completion_pct, task_xp, bonus_xp, penalty_xp, effective_xp,
            perfect_days, weekly_goals_achieved, level_start, level_end,
            levels_gained, seasons_completed, best_daily_streak,
            best_weekly_streak, utc_now(),
        ),
    )


def show_years():
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT y.*, pl.display_name
            FROM years y
            JOIN players pl ON pl.id = y.player_id
            ORDER BY y.year DESC, pl.id
            """
        ).fetchall()

    if not rows:
        print("No yearly summaries.")
        return

    for r in rows:
        print(
            f"#{r['id']} | {r['display_name']} | {r['year']} | "
            f"weeks {r['weeks_played']} | "
            f"missions {r['tasks_completed']}/{r['tasks_due']} "
            f"({r['completion_pct']:.2f}%) | task XP {r['task_xp']} | "
            f"bonus {r['bonus_xp']} | penalties {r['penalty_xp']} | "
            f"effective {r['effective_xp']} | perfect {r['perfect_days']} | "
            f"goals {r['weekly_goals_achieved']} | "
            f"level {r['level_start']} -> {r['level_end']} | "
            f"levels gained {r['levels_gained']} | "
            f"seasons {r['seasons_completed']} | "
            f"best streak D{r['best_daily_streak']}/W{r['best_weekly_streak']}"
        )


def show_weeks():
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                w.id,
                pl.display_name,
                w.year,
                w.iso_week,
                w.week_start,
                w.week_end,
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
                w.season_number,
                w.weekly_goal_achieved
            FROM weeks w
            JOIN players pl
            ON pl.id = w.player_id
            ORDER BY
                w.year DESC,
                w.iso_week DESC,
                pl.id
            """
        ).fetchall()

    if not rows:
        print("No closed weeks.")
        return

    for row in rows:
        print(
            "#%s | %s | %s-W%02d | %s -> %s | "
            "missions %s/%s (%.2f%%) | "
            "task XP %s | perfect %s | bonus %s | "
            "penalties %s | effective %s | "
            "level %s -> %s | season %s | goal %s"
            % (
                row["id"],
                row["display_name"],
                row["year"],
                row["iso_week"],
                row["week_start"],
                row["week_end"],
                row["tasks_completed"],
                row["tasks_due"],
                row["completion_pct"],
                row["task_xp"],
                row["perfect_days"],
                row["bonus_xp"],
                row["penalty_xp"],
                row["effective_xp"],
                row["level_start"],
                row["level_end"],
                row["season_number"],
                "YES" if row["weekly_goal_achieved"] else "NO",
            )
        )


def delete_test_weeks():
    with connect() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM weeks WHERE year = 2099")
        deleted_weeks = cur.rowcount
        cur.execute("DELETE FROM years WHERE year = 2099")
        deleted_years = cur.rowcount

    print(json.dumps({
        "ok": True,
        "deleted_weeks": deleted_weeks,
        "deleted_years": deleted_years
    }))


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  champion_db.py init")
        print("  champion_db.py players")
        print("  champion_db.py add_penalty <player_key> <amount> <reason>")
        print("  champion_db.py penalties")
        print("  champion_db.py cancel_penalty <penalty_id>")
        print("  champion_db.py close_week <player_key> <year> <iso_week> <week_start> <week_end> <season_number> <tasks_due> <tasks_completed> <task_xp> <perfect_days> <bonus_xp> <penalty_xp> <effective_xp> <level_start> <level_end> <weekly_goal_achieved> <daily_streak_end> <weekly_streak_end>")
        print("  champion_db.py close_day <player_key> <YYYY-MM-DD> <perfect:0|1>")
        print("  champion_db.py days [player_key]")
        print("  champion_db.py weeks")
        print("  champion_db.py years")
        print("  champion_db.py delete_test_weeks")
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "init":
        init_database()

    elif command == "players":
        show_players()

    elif command == "add_penalty":
        if len(sys.argv) < 5:
            print(
                "Usage: champion_db.py add_penalty "
                "<player_key> <amount> <reason>"
            )
            sys.exit(1)

        player_key = sys.argv[2]

        try:
            amount = int(sys.argv[3])
        except ValueError:
            print("ERROR: amount must be an integer.")
            sys.exit(1)

        if amount <= 0:
            print("ERROR: amount must be greater than 0.")
            sys.exit(1)

        reason = " ".join(sys.argv[4:]).strip()

        if not reason:
            print("ERROR: reason cannot be empty.")
            sys.exit(1)

        add_penalty(
            player_key=player_key,
            amount=amount,
            reason=reason,
        )

    elif command == "penalties":
        show_penalties()

    elif command == "cancel_penalty":
        if len(sys.argv) != 3:
            print("Usage: champion_db.py cancel_penalty <penalty_id>")
            sys.exit(1)

        try:
            penalty_id = int(sys.argv[2])
        except ValueError:
            print("ERROR: penalty_id must be an integer.")
            sys.exit(1)

        cancel_penalty(penalty_id)
    
    elif command == "close_week":
        if len(sys.argv) != 20:
            print(
                "Usage: champion_db.py close_week "
                "<player_key> "
                "<year> "
                "<iso_week> "
                "<week_start> "
                "<week_end> "
                "<season_number> "
                "<tasks_due> "
                "<tasks_completed> "
                "<task_xp> "
                "<perfect_days> "
                "<bonus_xp> "
                "<penalty_xp> "
                "<effective_xp> "
                "<level_start> "
                "<level_end> "
                "<weekly_goal_achieved> "
                "<daily_streak_end> "
                "<weekly_streak_end>"
            )
            raise SystemExit(1)

        close_week(
            sys.argv[2],
            sys.argv[3],
            sys.argv[4],
            sys.argv[5],
            sys.argv[6],
            sys.argv[7],
            sys.argv[8],
            sys.argv[9],
            sys.argv[10],
            sys.argv[11],
            sys.argv[12],
            sys.argv[13],
            sys.argv[14],
            sys.argv[15],
            sys.argv[16],
            sys.argv[17],
            sys.argv[18],
            sys.argv[19],
        )

    elif command == "close_day":
        if len(sys.argv) != 5:
            print("Usage: champion_db.py close_day <player_key> <YYYY-MM-DD> <perfect:0|1>")
            raise SystemExit(1)
        close_day(sys.argv[2], sys.argv[3], sys.argv[4])

    elif command == "days":
        if len(sys.argv) > 3:
            print("Usage: champion_db.py days [player_key]")
            raise SystemExit(1)
        show_days(sys.argv[2] if len(sys.argv) == 3 else None)

    elif command == "weeks":
        show_weeks()

    elif command == "years":
        show_years()

    elif command == "delete_test_weeks":
        delete_test_weeks()

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()