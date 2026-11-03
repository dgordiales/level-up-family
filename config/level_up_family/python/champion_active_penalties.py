#!/usr/bin/env python3
"""Level Up Family - Multas activas para Home Assistant."""

import json
import sqlite3
from pathlib import Path
from contextlib import closing

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "champion.db"


def main():
    try:
        with closing(sqlite3.connect(DB_PATH.resolve().as_uri() + "?mode=ro", uri=True)) as conn:
            conn.row_factory = sqlite3.Row

            rows = conn.execute(
                """
                SELECT
                    p.id AS penalty_id,
                    pl.player_key AS player_key,
                    pl.display_name AS player_name,
                    p.penalty_date AS penalty_date,
                    p.year AS year,
                    p.iso_week AS iso_week,
                    p.amount AS amount,
                    p.reason AS reason
                FROM penalties AS p
                INNER JOIN players AS pl
                    ON pl.id = p.player_id
                WHERE p.cancelled = 0
                ORDER BY p.id DESC
                """
            ).fetchall()

            items = []

            for row in rows:
                items.append(
                    {
                        "penalty_id": int(row["penalty_id"]),
                        "player_key": str(row["player_key"]),
                        "player_name": str(row["player_name"]),
                        "penalty_date": str(row["penalty_date"]),
                        "year": int(row["year"]),
                        "iso_week": int(row["iso_week"]),
                        "amount": int(row["amount"]),
                        "reason": str(row["reason"] or ""),
                    }
                )

        print(
            json.dumps(
                {
                    "count": len(items),
                    "items": items,
                },
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "count": 0,
                    "items": [],
                    "error": str(exc),
                },
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )


if __name__ == "__main__":
    main()
