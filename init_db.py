"""init_db.py - creates finances.db schema. Safe to re-run (CREATE TABLE IF NOT EXISTS)."""

import sqlite3
from finance_common import DEFAULT_PAYMENT_METHODS

DB_FILE = "finances.db"


def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            category TEXT NOT NULL,
            vendor TEXT,
            description TEXT,
            amount REAL NOT NULL,
            payment_method TEXT,
            notes TEXT,
            unpaid INTEGER NOT NULL DEFAULT 0,
            due_date TEXT,
            type TEXT NOT NULL,
            sheet_row INTEGER,
            receipt_drive_link TEXT,
            reference_number TEXT,
            original_currency TEXT,
            original_amount REAL,
            fx_rate REAL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS payment_methods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            sort_order INTEGER NOT NULL
        )
    """)
    for i, name in enumerate(DEFAULT_PAYMENT_METHODS):
        c.execute("INSERT OR IGNORE INTO payment_methods (name, sort_order) VALUES (?, ?)", (name, i))

    # Migrations for DBs created before these columns existed - simple ALTER
    # TABLE ADD COLUMN, no CHECK constraint involved so no full rebuild needed.
    existing_cols = {row[1] for row in c.execute("PRAGMA table_info(transactions)").fetchall()}
    if "receipt_drive_link" not in existing_cols:
        c.execute("ALTER TABLE transactions ADD COLUMN receipt_drive_link TEXT")
    if "reference_number" not in existing_cols:
        c.execute("ALTER TABLE transactions ADD COLUMN reference_number TEXT")
    if "original_currency" not in existing_cols:
        c.execute("ALTER TABLE transactions ADD COLUMN original_currency TEXT")
    if "original_amount" not in existing_cols:
        c.execute("ALTER TABLE transactions ADD COLUMN original_amount REAL")
    if "fx_rate" not in existing_cols:
        c.execute("ALTER TABLE transactions ADD COLUMN fx_rate REAL")

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print("finances.db ready")
