import json
from datetime import datetime, timezone

from .database import get_db


def _issue(code, message, product=None, severity="high"):
    return {
        "code": code,
        "message": message,
        "product": product,
        "severity": severity,
    }


def match_invoice(invoice_id, price_tolerance_percent=1.0):
    db = get_db()
    invoice = db.execute(
        "SELECT * FROM invoices WHERE id = ?", (invoice_id,)
    ).fetchone()
    if not invoice:
        raise ValueError(f"Invoice {invoice_id} tidak ditemukan")
    if invoice["status"] != "Submitted":
        db.execute("DELETE FROM matching_results WHERE invoice_id=?", (invoice_id,))
        db.commit()
        return "Not Processed", []

    issues = []
    po_id = invoice["purchase_order_id"]
    if po_id is None:
        issues.append(_issue("MISSING_PO", "Invoice belum terhubung dengan PO."))
        status = "Pending Review"
        _save_result(db, invoice_id, None, status, issues, 0, _invoice_total(db, invoice_id))
        return status, issues

    po = db.execute("SELECT * FROM purchase_orders WHERE id = ?", (po_id,)).fetchone()
    if not po:
        issues.append(_issue("INVALID_PO", "PO yang dirujuk tidak ditemukan."))
    elif po["supplier_id"] != invoice["supplier_id"]:
        issues.append(_issue("SUPPLIER_MISMATCH", "Supplier invoice berbeda dari supplier PO."))

    po_items = {
        row["product_id"]: row
        for row in db.execute(
            """SELECT pi.*, p.sku, p.name FROM po_items pi
               JOIN products p ON p.id = pi.product_id
               WHERE pi.purchase_order_id = ?""",
            (po_id,),
        )
    }
    invoice_items = {
        row["product_id"]: row
        for row in db.execute(
            """SELECT ii.*, p.sku, p.name FROM invoice_items ii
               JOIN products p ON p.id = ii.product_id WHERE ii.invoice_id = ?""",
            (invoice_id,),
        )
    }
    received = {
        row["product_id"]: row["received_quantity"]
        for row in db.execute(
            """SELECT ri.product_id, SUM(ri.quantity) AS received_quantity
               FROM receipt_items ri JOIN goods_receipts gr ON gr.id = ri.goods_receipt_id
               WHERE gr.purchase_order_id = ? AND gr.status = 'Submitted' GROUP BY ri.product_id""",
            (po_id,),
        )
    }

    for product_id, inv_item in invoice_items.items():
        po_item = po_items.get(product_id)
        label = f'{inv_item["sku"]} — {inv_item["name"]}'
        if not po_item:
            issues.append(_issue("PRODUCT_NOT_IN_PO", "Produk invoice tidak ditemukan pada PO.", label))
            continue

        if inv_item["quantity"] != po_item["quantity"]:
            issues.append(_issue("INVOICE_QTY_MISMATCH", f'Kuantitas invoice {inv_item["quantity"]:g}, PO {po_item["quantity"]:g}.', label))

        price_diff_pct = 0 if po_item["unit_price"] == 0 else abs(inv_item["unit_price"] - po_item["unit_price"]) / po_item["unit_price"] * 100
        if price_diff_pct > price_tolerance_percent:
            issues.append(_issue("PRICE_MISMATCH", f'Selisih harga {price_diff_pct:.2f}% melebihi toleransi {price_tolerance_percent:.2f}%.', label))

        received_qty = received.get(product_id, 0)
        if received_qty < inv_item["quantity"]:
            issues.append(_issue("UNDER_RECEIVED", f'Baru diterima {received_qty:g} dari {inv_item["quantity"]:g} unit yang ditagihkan.', label, "medium"))
        elif received_qty > po_item["quantity"]:
            issues.append(_issue("OVER_RECEIVED", f'Diterima {received_qty:g}, melebihi pesanan {po_item["quantity"]:g}.', label))

    for product_id, po_item in po_items.items():
        if product_id not in invoice_items:
            issues.append(_issue("MISSING_INVOICE_LINE", "Produk PO tidak terdapat pada invoice.", f'{po_item["sku"]} — {po_item["name"]}', "medium"))

    if not issues:
        status = "Matched"
    elif any(issue["code"] in {"MISSING_PO", "INVALID_PO"} for issue in issues):
        status = "Pending Review"
    elif all(issue["code"] in {"UNDER_RECEIVED", "MISSING_INVOICE_LINE"} for issue in issues):
        status = "Partial Match"
    else:
        status = "Mismatch"

    po_total = sum(row["quantity"] * row["unit_price"] for row in po_items.values())
    invoice_total = sum(row["quantity"] * row["unit_price"] for row in invoice_items.values())
    _save_result(db, invoice_id, po_id, status, issues, po_total, invoice_total)
    return status, issues


def _invoice_total(db, invoice_id):
    row = db.execute("SELECT COALESCE(SUM(quantity * unit_price), 0) FROM invoice_items WHERE invoice_id = ?", (invoice_id,)).fetchone()
    return row[0]


def _save_result(db, invoice_id, po_id, status, issues, po_total, invoice_total):
    now = datetime.now(timezone.utc).isoformat()
    db.execute(
        """INSERT INTO matching_results
           (invoice_id, purchase_order_id, status, discrepancy_count, total_po, total_invoice, details, matched_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(invoice_id) DO UPDATE SET
             purchase_order_id=excluded.purchase_order_id, status=excluded.status,
             discrepancy_count=excluded.discrepancy_count, total_po=excluded.total_po,
             total_invoice=excluded.total_invoice, details=excluded.details, matched_at=excluded.matched_at""",
        (invoice_id, po_id, status, len(issues), po_total, invoice_total, json.dumps(issues, ensure_ascii=False), now),
    )
    db.execute(
        "INSERT INTO transaction_history (entity_type, entity_id, action, details) VALUES ('invoice', ?, 'MATCHED', ?)",
        (invoice_id, f"Status: {status}; {len(issues)} discrepancy"),
    )
    db.commit()


def run_all_matching(price_tolerance_percent=1.0):
    db = get_db()
    invoice_ids = [row[0] for row in db.execute("SELECT id FROM invoices WHERE status='Submitted'")]
    return [match_invoice(invoice_id, price_tolerance_percent) for invoice_id in invoice_ids]
