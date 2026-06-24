"""
Migration: Create the weapons table, add equipped_weapon_id to players,
and insert three starter weapons.
Safe to run multiple times.
"""

import sqlite3
import sys

DB_PATH = "game.db"

STARTER_WEAPONS = [
    ("Discipline Edge", "strength", 1, "C"),
    ("Logic Staff", "intelligence", 1, "C"),
    ("Reflex Blade", "dexterity", 1, "C"),
]


def table_exists(cursor: sqlite3.Cursor, table: str) -> bool:
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return cursor.fetchone() is not None


def get_existing_columns(cursor: sqlite3.Cursor, table: str) -> set[str]:
    cursor.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cursor.fetchall()}


def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # --- WEAPONS TABLE ---
        if not table_exists(cursor, "weapons"):
            cursor.execute("""
                CREATE TABLE weapons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    governing_stat TEXT NOT NULL,
                    stat_requirement INTEGER NOT NULL DEFAULT 1,
                    scaling_grade TEXT NOT NULL DEFAULT 'C'
                )
            """)
            print("  weapons table created")

            for name, stat, req, grade in STARTER_WEAPONS:
                cursor.execute(
                    "INSERT INTO weapons (name, governing_stat, stat_requirement, scaling_grade) VALUES (?, ?, ?, ?)",
                    (name, stat, req, grade),
                )
                print(f"    inserted starter weapon: {name}")
        else:
            print("  weapons table already exists, skipping")

        # --- EQUIPPED WEAPON FK ON PLAYERS ---
        player_cols = get_existing_columns(cursor, "players")
        if "equipped_weapon_id" not in player_cols:
            cursor.execute("ALTER TABLE players ADD COLUMN equipped_weapon_id INTEGER REFERENCES weapons(id)")
            print("  players.equipped_weapon_id added")
        else:
            print("  players.equipped_weapon_id already exists, skipping")

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
