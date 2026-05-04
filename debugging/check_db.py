#!/usr/bin/env python
"""
Script to add missing columns to tournament_draw table.
Run: .venv/bin/python check_db.py
"""
from app import create_app
from extensions import db

app = create_app()
with app.app_context():
    conn = db.engine.raw_connection()
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(tournament_draw)")
    cols = cur.fetchall()
    existing_names = [c[1] for c in cols]

    migrations = [
        ("main_draw_match_id", "ALTER TABLE tournament_draw ADD COLUMN main_draw_match_id INTEGER"),
        ("main_draw_slot", "ALTER TABLE tournament_draw ADD COLUMN main_draw_slot VARCHAR(2)"),
        ("qualif_number", "ALTER TABLE tournament_draw ADD COLUMN qualif_number INTEGER"),
    ]

    for col_name, sql in migrations:
        if col_name not in existing_names:
            try:
                cur.execute(sql)
                print(f"Added column: {col_name}")
            except Exception as e:
                print(f"Error adding {col_name}: {e}")
        else:
            print(f"Column already exists: {col_name}")

    conn.commit()
    conn.close()
    print("Done.")
