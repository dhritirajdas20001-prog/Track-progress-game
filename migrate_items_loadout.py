"""
Migration: Rename weapons table to items, add slot_type/passive_effect columns,
add equipped_armor_id/equipped_artifact_id/equipped_accessory_id to players,
and seed starter items across all 4 slot types.
Safe to run multiple times.
"""

import sqlite3
import sys

DB_PATH = "game.db"

STARTER_ITEMS = [
    ("Discipline Edge", "Weapon", "strength", 1, "C", "Steady force through repetition"),
    ("Logic Staff", "Weapon", "intelligence", 1, "C", "Structured analytical thinking"),
    ("Reflex Blade", "Weapon", "dexterity", 1, "C", "Precision under pressure"),
    ("Stoic Plate", "Armor", "stamina", 1, "C", "Resist distractions and fatigue"),
    ("Focus Cloak", "Armor", "vitality", 1, "C", "Sustained attention over hours"),
    ("Insight Pendant", "Artifact", "intelligence", 1, "B", "Pattern recognition boost"),
    ("Lucky Coin", "Accessory", "luck", 1, "C", "Serendipitous encounters"),
    ("Sprint Ring", "Accessory", "agility", 1, "C", "Quick task turnaround"),
]


def table_exists(cursor, table):
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return cursor.fetchone() is not None


def get_existing_columns(cursor, table):
    cursor.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cursor.fetchall()}


def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # --- Rename weapons -> items (if weapons exists and items doesn't) ---
        if table_exists(cursor, "weapons") and not table_exists(cursor, "items"):
            cursor.execute("ALTER TABLE weapons RENAME TO items")
            print("  renamed weapons -> items")
        elif not table_exists(cursor, "items"):
            cursor.execute("""
                CREATE TABLE items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    slot_type TEXT NOT NULL DEFAULT 'Weapon',
                    governing_stat TEXT NOT NULL,
                    stat_requirement INTEGER NOT NULL DEFAULT 1,
                    scaling_grade TEXT NOT NULL DEFAULT 'C',
                    passive_effect TEXT
                )
            """)
            print("  items table created fresh")
        else:
            print("  items table already exists")

        # --- Add new columns to items if missing ---
        item_cols = get_existing_columns(cursor, "items")

        if "slot_type" not in item_cols:
            cursor.execute("ALTER TABLE items ADD COLUMN slot_type TEXT NOT NULL DEFAULT 'Weapon'")
            print("  items.slot_type added (existing rows default to 'Weapon')")
        else:
            print("  items.slot_type already exists, skipping")

        if "passive_effect" not in item_cols:
            cursor.execute("ALTER TABLE items ADD COLUMN passive_effect TEXT")
            print("  items.passive_effect added")
        else:
            print("  items.passive_effect already exists, skipping")

        # --- Add new FK columns to players ---
        player_cols = get_existing_columns(cursor, "players")
        for col in ("equipped_armor_id", "equipped_artifact_id", "equipped_accessory_id"):
            if col not in player_cols:
                cursor.execute(f"ALTER TABLE players ADD COLUMN {col} INTEGER REFERENCES items(id)")
                print(f"  players.{col} added")
            else:
                print(f"  players.{col} already exists, skipping")

        # --- Update existing equipped_weapon_id FK to point to items ---
        # SQLite can't ALTER FK, but the data is compatible since we renamed the table

        # --- Seed starter items (skip if items already has rows beyond the originals) ---
        cursor.execute("SELECT COUNT(*) FROM items")
        existing_count = cursor.fetchone()[0]
        if existing_count <= 3:
            for name, slot, stat, req, grade, effect in STARTER_ITEMS:
                cursor.execute("SELECT id FROM items WHERE name = ?", (name,))
                if not cursor.fetchone():
                    cursor.execute(
                        "INSERT INTO items (name, slot_type, governing_stat, stat_requirement, scaling_grade, passive_effect) VALUES (?, ?, ?, ?, ?, ?)",
                        (name, slot, stat, req, grade, effect),
                    )
                    print(f"    seeded: {name} ({slot})")
        else:
            print("  items already has data, skipping seed")

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
