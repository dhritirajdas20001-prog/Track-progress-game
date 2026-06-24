"""
Migration: Create the activity_log table.
Safe to run multiple times.
"""

import sqlite3
import sys

DB_PATH = "game.db"


def table_exists(cursor: sqlite3.Cursor, table: str) -> bool:
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return cursor.fetchone() is not None


def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        if not table_exists(cursor, "activity_log"):
            cursor.execute("""
                CREATE TABLE activity_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL DEFAULT (datetime('now')),
                    task_name TEXT NOT NULL,
                    general_xp_gained INTEGER NOT NULL DEFAULT 0,
                    gold_gained INTEGER NOT NULL DEFAULT 0,
                    stat_type TEXT,
                    stat_xp_gained INTEGER NOT NULL DEFAULT 0
                )
            """)
            print("  activity_log table created")
        else:
            print("  activity_log table already exists, skipping")

        conn.commit()
        print("\nMigration complete.")

    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
