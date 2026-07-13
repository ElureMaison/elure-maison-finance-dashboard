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
            sheet_row INTEGER
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
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print("finances.db ready")
