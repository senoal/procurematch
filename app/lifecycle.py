import json
from datetime import datetime, timezone

from .database import get_db


CONFIG = {
    "po": {
        "table": "purchase_orders",
        "label": "Purchase Order",
        "number": "po_number",
        "items": "po_items",
        "foreign_key": "purchase_order_id",
    },
    "receipt": {
        "table": "goods_receipts",
        "label": "Goods Receipt",
        "number": "receipt_number",
        "items": "receipt_items",
        "foreign_key": "goods_receipt_id",
    },
    "invoice": {
        "table": "invoices",
        "label": "Invoice",
        "number": "invoice_number",
        "items": "invoice_items",
        "foreign_key": "invoice_id",
    },
}

FIELD_LABELS = {
    "po_number": "PO number",
    "receipt_number": "Receipt number",
    "invoice_number": "Invoice number",
    "supplier_id": "Supplier",
    "purchase_order_id": "Purchase order",
    "order_date": "Order date",
    "expected_date": "Expected date",
    "receipt_date": "Receipt date",
    "invoice_date": "Invoice date",
    "quantity": "Quantity",
    "unit_price": "Unit price",
}

DOCUMENT_FIELDS = {
    "po": ["po_number", "supplier_id", "order_date", "expected_date"],
    "receipt": ["receipt_number", "purchase_order_id", "receipt_date"],
    "invoice": ["invoice_number", "purchase_order_id", "supplier_id", "invoice_date"],
}


def config_for(entity):
    if entity not in CONFIG:
        raise ValueError("Jenis dokumen tidak dikenali.")
    return CONFIG[entity]


def snapshot_document(entity, document_id):
    db = get_db()
    config = config_for(entity)
    document = db.execute(
        f"SELECT * FROM {config['table']} WHERE id=?", (document_id,)
    ).fetchone()
    if not document:
        raise ValueError(f"{config['label']} tidak ditemukan.")
    items = db.execute(
        f"SELECT * FROM {config['items']} WHERE {config['foreign_key']}=? ORDER BY id",
        (document_id,),
    ).fetchall()
    return {"document": dict(document), "items": [dict(item) for item in items]}


def record_history(entity, document_id, action, details):
    get_db().execute(
        """INSERT INTO transaction_history (entity_type, entity_id, action, details)
           VALUES (?, ?, ?, ?)""",
        (entity, document_id, action, details),
    )


def present_history(db, rows, entity):
    """Turn stored audit payloads into concise, user-facing change descriptions."""
    presented = []
    for row in rows:
        entry = dict(row)
        entry["summary"] = entry.get("details") or "Tidak ada keterangan tambahan."
        entry["changes"] = []
        if entry["action"] == "DRAFT_UPDATED":
            try:
                payload = json.loads(entry["details"])
                entry["changes"] = _snapshot_changes(
                    db, entity, payload["before"], payload["after"]
                )
                entry["summary"] = (
                    f"{len(entry['changes'])} perubahan disimpan pada draft."
                    if entry["changes"] else "Draft disimpan tanpa perubahan nilai."
                )
            except (TypeError, ValueError, KeyError, json.JSONDecodeError):
                entry["summary"] = "Draft diperbarui. Detail perubahan lama tidak dapat dibaca."
        presented.append(entry)
    return presented


def _snapshot_changes(db, entity, before, after):
    changes = []
    before_document = before.get("document", {})
    after_document = after.get("document", {})
    for field in DOCUMENT_FIELDS[entity]:
        old, new = before_document.get(field), after_document.get(field)
        if old != new:
            changes.append({
                "label": FIELD_LABELS[field],
                "before": _display_value(db, field, old),
                "after": _display_value(db, field, new),
            })

    before_items = {str(item["product_id"]): item for item in before.get("items", [])}
    after_items = {str(item["product_id"]): item for item in after.get("items", [])}
    for product_id in sorted(set(before_items) | set(after_items), key=int):
        old_item, new_item = before_items.get(product_id), after_items.get(product_id)
        product = _product_name(db, product_id)
        if old_item is None:
            changes.append({
                "label": f"Product added · {product}", "before": "—",
                "after": _item_summary(new_item),
            })
            continue
        if new_item is None:
            changes.append({
                "label": f"Product removed · {product}", "before": _item_summary(old_item),
                "after": "—",
            })
            continue
        for field in ("quantity", "unit_price"):
            if field not in old_item and field not in new_item:
                continue
            if old_item.get(field) != new_item.get(field):
                changes.append({
                    "label": f"{product} · {FIELD_LABELS[field]}",
                    "before": _display_value(db, field, old_item.get(field)),
                    "after": _display_value(db, field, new_item.get(field)),
                })
    return changes


def _display_value(db, field, value):
    if value in (None, ""):
        return "—"
    if field == "supplier_id":
        row = db.execute("SELECT code, name FROM suppliers WHERE id=?", (value,)).fetchone()
        return f"{row['code']} · {row['name']}" if row else f"Supplier #{value}"
    if field == "purchase_order_id":
        row = db.execute("SELECT po_number FROM purchase_orders WHERE id=?", (value,)).fetchone()
        return row["po_number"] if row else f"PO #{value}"
    if field == "unit_price":
        return "Rp {:,.0f}".format(float(value)).replace(",", ".")
    if field == "quantity":
        return f"{float(value):g}"
    return str(value)


def _product_name(db, product_id):
    row = db.execute("SELECT sku, name FROM products WHERE id=?", (product_id,)).fetchone()
    return f"{row['sku']} · {row['name']}" if row else f"Product #{product_id}"


def _item_summary(item):
    quantity = f"{float(item.get('quantity', 0)):g} unit"
    if "unit_price" in item:
        price = "Rp {:,.0f}".format(float(item.get("unit_price", 0))).replace(",", ".")
        return f"{quantity} @ {price}"
    return quantity


def transition_document(entity, document_id, action, reason=""):
    db = get_db()
    config = config_for(entity)
    document = db.execute(
        f"SELECT * FROM {config['table']} WHERE id=?", (document_id,)
    ).fetchone()
    if not document:
        raise ValueError(f"{config['label']} tidak ditemukan.")
    status = document["status"]
    now = datetime.now(timezone.utc).isoformat()

    with db:
        if action == "submit":
            if status != "Draft":
                raise ValueError("Hanya dokumen Draft yang dapat disubmit.")
            db.execute(
                f"UPDATE {config['table']} SET status='Submitted' WHERE id=?", (document_id,)
            )
            record_history(entity, document_id, "SUBMITTED", "Dokumen disubmit untuk diproses.")
            return "Submitted"

        if action == "revise":
            if status != "Submitted":
                raise ValueError("Hanya dokumen Submitted yang dapat direvisi.")
            if not reason.strip():
                raise ValueError("Alasan revisi wajib diisi.")
            _store_revision(entity, document_id, document["version"], reason)
            db.execute(
                f"UPDATE {config['table']} SET status='Draft', version=version+1 WHERE id=?",
                (document_id,),
            )
            _clear_current_match(entity, document_id)
            record_history(entity, document_id, "REVISION_OPENED", f"Alasan: {reason.strip()}")
            return "Draft"

        if action == "cancel":
            if status == "Cancelled":
                raise ValueError("Dokumen sudah dibatalkan.")
            if not reason.strip():
                raise ValueError("Alasan pembatalan wajib diisi.")
            if entity == "po":
                active_invoices = db.execute(
                    "SELECT COUNT(*) FROM invoices WHERE purchase_order_id=? AND status!='Cancelled'",
                    (document_id,),
                ).fetchone()[0]
                active_receipts = db.execute(
                    "SELECT COUNT(*) FROM goods_receipts WHERE purchase_order_id=? AND status!='Cancelled'",
                    (document_id,),
                ).fetchone()[0]
                if active_invoices or active_receipts:
                    raise ValueError("Batalkan invoice dan goods receipt aktif sebelum membatalkan PO.")
            _store_revision(entity, document_id, document["version"], reason)
            db.execute(
                f"UPDATE {config['table']} SET status='Cancelled', cancelled_at=? WHERE id=?",
                (now, document_id),
            )
            _clear_current_match(entity, document_id)
            record_history(entity, document_id, "CANCELLED", f"Alasan: {reason.strip()}")
            return "Cancelled"

    raise ValueError("Tindakan lifecycle tidak dikenali.")


def delete_draft(entity, document_id):
    db = get_db()
    config = config_for(entity)
    document = db.execute(
        f"SELECT status, version FROM {config['table']} WHERE id=?", (document_id,)
    ).fetchone()
    if not document:
        raise ValueError(f"{config['label']} tidak ditemukan.")
    if document["status"] != "Draft":
        raise ValueError("Hanya Draft yang belum diproses yang dapat dihapus.")
    if document["version"] != 1:
        raise ValueError("Draft revisi memiliki riwayat proses dan tidak dapat dihapus; gunakan Cancel/Void.")
    if entity == "po":
        dependencies = db.execute(
            """SELECT
                 (SELECT COUNT(*) FROM invoices WHERE purchase_order_id=?) +
                 (SELECT COUNT(*) FROM goods_receipts WHERE purchase_order_id=?)""",
            (document_id, document_id),
        ).fetchone()[0]
        if dependencies:
            raise ValueError("PO memiliki dokumen turunan dan tidak dapat dihapus.")
    with db:
        _clear_current_match(entity, document_id)
        db.execute(f"DELETE FROM {config['table']} WHERE id=?", (document_id,))


def _store_revision(entity, document_id, version, reason):
    snapshot = snapshot_document(entity, document_id)
    get_db().execute(
        """INSERT INTO document_revisions
           (entity_type, entity_id, version, reason, snapshot)
           VALUES (?, ?, ?, ?, ?)""",
        (entity, document_id, version, reason.strip(), json.dumps(snapshot, ensure_ascii=False)),
    )


def _clear_current_match(entity, document_id):
    db = get_db()
    if entity == "invoice":
        db.execute("DELETE FROM matching_results WHERE invoice_id=?", (document_id,))
    elif entity in {"po", "receipt"}:
        config = config_for(entity)
        if entity == "po":
            po_id = document_id
        else:
            row = db.execute(
                f"SELECT purchase_order_id FROM {config['table']} WHERE id=?", (document_id,)
            ).fetchone()
            po_id = row[0] if row else None
        if po_id:
            db.execute(
                "DELETE FROM matching_results WHERE purchase_order_id=?", (po_id,)
            )
