"""
Migration: Convert flat stat columns to dual-track (level + xp) per stat,
and add stat_xp_reward to tasks.
Safe to run multiple times — skips columns that already exist.
Preserves existing stat values as the starting level.
"""

import sqlite3
import sys

DB_PATH = "game.db"

STATS = ("strength", "stamina", "intelligence", "agility", "vitality", "dexterity", "faith", "luck")


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

        # --- PLAYERS TABLE ---
        for stat in STATS:
            level_col = f"{stat}_level"
            xp_col = f"{stat}_xp"

            if level_col not in player_cols:
                cursor.execute(f"ALTER TABLE players ADD COLUMN {level_col} INTEGER NOT NULL DEFAULT 1")
                print(f"  players.{level_col} added")
                added += 1

                # Migrate existing flat value into the new _level column
                if stat in player_cols:
                    cursor.execute(f"UPDATE players SET {level_col} = {stat}")
                    print(f"    -> copied players.{stat} -> {level_col}")
            else:
                print(f"  players.{level_col} already exists, skipping")

            if xp_col not in player_cols:
                cursor.execute(f"ALTER TABLE players ADD COLUMN {xp_col} INTEGER NOT NULL DEFAULT 0")
                print(f"  players.{xp_col} added")
                added += 1
            else:
                print(f"  players.{xp_col} already exists, skipping")

        # --- TASKS TABLE ---
        if "stat_xp_reward" not in task_cols:
            cursor.execute("ALTER TABLE tasks ADD COLUMN stat_xp_reward INTEGER NOT NULL DEFAULT 10")
            print(f"  tasks.stat_xp_reward added")
            added += 1
        else:
            print(f"  tasks.stat_xp_reward already exists, skipping")

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
