"""
Migration: Add RPG stat columns to players table and stat_reward_type to tasks table.
Safe to run multiple times — skips columns that already exist.
"""

import sqlite3
import sys

DB_PATH = "game.db"

PLAYER_NEW_COLUMNS = [
    ("strength", "INTEGER NOT NULL DEFAULT 1"),
    ("stamina", "INTEGER NOT NULL DEFAULT 1"),
    ("intelligence", "INTEGER NOT NULL DEFAULT 1"),
    ("agility", "INTEGER NOT NULL DEFAULT 1"),
    ("vitality", "INTEGER NOT NULL DEFAULT 1"),
    ("dexterity", "INTEGER NOT NULL DEFAULT 1"),
    ("faith", "INTEGER NOT NULL DEFAULT 1"),
    ("luck", "INTEGER NOT NULL DEFAULT 1"),
]

TASK_NEW_COLUMNS = [
    ("stat_reward_type", "TEXT DEFAULT NULL"),
]


def get_existing_columns(cursor: sqlite3.Cursor, table: str) -> set[str]:
    cursor.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cursor.fetchall()}


def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        player_cols = get_existing_columns(cursor, "players")
        task_cols = get_existing_columns(cursor, "tasks")

        added = 0

        for col_name, col_def in PLAYER_NEW_COLUMNS:
            if col_name not in player_cols:
                cursor.execute(f"ALTER TABLE players ADD COLUMN {col_name} {col_def}")
                print(f"  players.{col_name} added")
                added += 1
            else:
                print(f"  players.{col_name} already exists, skipping")

        for col_name, col_def in TASK_NEW_COLUMNS:
            if col_name not in task_cols:
                cursor.execute(f"ALTER TABLE tasks ADD COLUMN {col_name} {col_def}")
                print(f"  tasks.{col_name} added")
                added += 1
            else:
                print(f"  tasks.{col_name} already exists, skipping")

        conn.commit()
        print(f"\nMigration complete. {added} column(s) added.")

    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
