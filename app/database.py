import sqlite3
from pathlib import Path

from flask import current_app, g


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
    db.executescript(schema)
    _migrate_db(db)
    db.commit()


def _migrate_db(db):
    migrations = {
        "purchase_orders": {
            "version": "INTEGER NOT NULL DEFAULT 1",
            "cancelled_at": "TEXT",
        },
        "goods_receipts": {
            "status": "TEXT NOT NULL DEFAULT 'Submitted'",
            "version": "INTEGER NOT NULL DEFAULT 1",
            "cancelled_at": "TEXT",
        },
        "invoices": {
            "version": "INTEGER NOT NULL DEFAULT 1",
            "cancelled_at": "TEXT",
        },
    }
    for table, columns in migrations.items():
        existing = {row[1] for row in db.execute(f"PRAGMA table_info({table})")}
        for column, definition in columns.items():
            if column not in existing:
                db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
    db.execute("UPDATE purchase_orders SET status='Submitted' WHERE status='Open'")


def seed_demo_data():
    db = get_db()
    if db.execute("SELECT COUNT(*) FROM purchase_orders").fetchone()[0]:
        return False

    db.executescript(
        """
        INSERT INTO suppliers (code, name) VALUES
            ('SUP-001', 'PT Nusantara Elektronik'),
            ('SUP-002', 'CV Prima Packaging'),
            ('SUP-003', 'PT Sumber Industri');

        INSERT INTO products (sku, name) VALUES
            ('PRD-LTP-14', 'Laptop Business 14 inch'),
            ('PRD-BOX-M', 'Karton Kemasan Medium'),
            ('PRD-BRG-08', 'Bearing Industri 8 mm');

        INSERT INTO purchase_orders (po_number, supplier_id, order_date, expected_date, status)
        VALUES
            ('PO-2026-001', 1, '2026-09-15', '2026-09-25', 'Submitted'),
            ('PO-2026-002', 2, '2026-09-18', '2026-09-28', 'Submitted'),
            ('PO-2026-003', 3, '2026-09-20', '2026-10-02', 'Submitted');

        INSERT INTO po_items (purchase_order_id, product_id, quantity, unit_price) VALUES
            (1, 1, 10, 12500000),
            (2, 2, 500, 8500),
            (3, 3, 100, 185000);

        INSERT INTO goods_receipts (receipt_number, purchase_order_id, receipt_date, status) VALUES
            ('GR-2026-001', 1, '2026-09-24', 'Submitted'),
            ('GR-2026-002', 2, '2026-09-27', 'Submitted'),
            ('GR-2026-003', 3, '2026-10-01', 'Submitted');

        INSERT INTO receipt_items (goods_receipt_id, product_id, quantity) VALUES
            (1, 1, 10), (2, 2, 450), (3, 3, 100);

        INSERT INTO invoices (invoice_number, purchase_order_id, supplier_id, invoice_date, status)
        VALUES
            ('INV-NE-1001', 1, 1, '2026-09-25', 'Submitted'),
            ('INV-PP-2044', 2, 2, '2026-09-28', 'Submitted'),
            ('INV-SI-8831', 3, 3, '2026-10-02', 'Submitted');

        INSERT INTO invoice_items (invoice_id, product_id, quantity, unit_price) VALUES
            (1, 1, 10, 12500000),
            (2, 2, 500, 8500),
            (3, 3, 100, 192500);
        """
    )
    db.commit()
    return True
