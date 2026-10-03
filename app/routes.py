import json

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for

from .database import get_db, seed_demo_data
from .matching import match_invoice, run_all_matching
from .importer import ImportValidationError, import_workbook
from .lifecycle import (
    config_for, delete_draft, present_history, record_history, snapshot_document,
    transition_document,
)


bp = Blueprint("main", __name__)


@bp.app_template_filter("currency")
def currency(value):
    return "Rp {:,.0f}".format(value or 0).replace(",", ".")


@bp.route("/")
def dashboard():
    db = get_db()
    metrics = {
        "po": db.execute("SELECT COUNT(*) FROM purchase_orders").fetchone()[0],
        "invoices": db.execute("SELECT COUNT(*) FROM invoices").fetchone()[0],
        "matched": db.execute("SELECT COUNT(*) FROM matching_results WHERE status = 'Matched'").fetchone()[0],
        "exceptions": db.execute("SELECT COUNT(*) FROM matching_results WHERE status != 'Matched'").fetchone()[0],
    }
    statuses = db.execute("SELECT status, COUNT(*) AS total FROM matching_results GROUP BY status ORDER BY total DESC").fetchall()
    recent = db.execute(
        """SELECT i.invoice_number, po.po_number, s.name AS supplier, mr.status,
                  mr.discrepancy_count, mr.total_invoice, mr.matched_at
           FROM invoices i
           JOIN suppliers s ON s.id = i.supplier_id
           LEFT JOIN purchase_orders po ON po.id = i.purchase_order_id
           LEFT JOIN matching_results mr ON mr.invoice_id = i.id
           ORDER BY i.id DESC LIMIT 8"""
    ).fetchall()
    return render_template("dashboard.html", metrics=metrics, statuses=statuses, recent=recent)


@bp.route("/documents")
def documents():
    db = get_db()
    purchase_orders = db.execute(
        """SELECT po.*, s.name AS supplier, COALESCE(SUM(pi.quantity*pi.unit_price), 0) AS total
           FROM purchase_orders po JOIN suppliers s ON s.id=po.supplier_id
           LEFT JOIN po_items pi ON pi.purchase_order_id=po.id GROUP BY po.id ORDER BY po.id DESC"""
    ).fetchall()
    invoices = db.execute(
        """SELECT i.*, s.name AS supplier, po.po_number, mr.status AS match_status,
                  COALESCE(SUM(ii.quantity*ii.unit_price), 0) AS total
           FROM invoices i JOIN suppliers s ON s.id=i.supplier_id
           LEFT JOIN purchase_orders po ON po.id=i.purchase_order_id
           LEFT JOIN matching_results mr ON mr.invoice_id=i.id
           LEFT JOIN invoice_items ii ON ii.invoice_id=i.id GROUP BY i.id ORDER BY i.id DESC"""
    ).fetchall()
    receipts = db.execute(
        """SELECT gr.*, po.po_number, COUNT(ri.id) AS line_count, COALESCE(SUM(ri.quantity),0) AS quantity
           FROM goods_receipts gr JOIN purchase_orders po ON po.id=gr.purchase_order_id
           LEFT JOIN receipt_items ri ON ri.goods_receipt_id=gr.id GROUP BY gr.id ORDER BY gr.id DESC"""
    ).fetchall()
    return render_template("documents.html", purchase_orders=purchase_orders, invoices=invoices, receipts=receipts)


@bp.route("/documents/<entity>/<int:document_id>")
def document_detail(entity, document_id):
    db = get_db()
    config = config_for(entity)
    if entity == "po":
        document = db.execute(
            """SELECT po.*, s.code AS supplier_code, s.name AS supplier
               FROM purchase_orders po JOIN suppliers s ON s.id=po.supplier_id
               WHERE po.id=?""", (document_id,),
        ).fetchone()
    elif entity == "receipt":
        document = db.execute(
            """SELECT gr.*, po.po_number, s.name AS supplier
               FROM goods_receipts gr JOIN purchase_orders po ON po.id=gr.purchase_order_id
               JOIN suppliers s ON s.id=po.supplier_id WHERE gr.id=?""", (document_id,),
        ).fetchone()
    else:
        document = db.execute(
            """SELECT i.*, po.po_number, s.name AS supplier, mr.status AS match_status
               FROM invoices i LEFT JOIN purchase_orders po ON po.id=i.purchase_order_id
               JOIN suppliers s ON s.id=i.supplier_id
               LEFT JOIN matching_results mr ON mr.invoice_id=i.id WHERE i.id=?""", (document_id,),
        ).fetchone()
    if not document:
        flash(f"{config['label']} tidak ditemukan.", "error")
        return redirect(url_for("main.documents"))
    price_column = ", line.unit_price" if entity in {"po", "invoice"} else ""
    items = db.execute(
        f"""SELECT line.id, line.product_id, line.quantity{price_column}, p.sku, p.name
            FROM {config['items']} line JOIN products p ON p.id=line.product_id
            WHERE line.{config['foreign_key']}=? ORDER BY line.id""",
        (document_id,),
    ).fetchall()
    history_rows = db.execute(
        """SELECT * FROM transaction_history WHERE entity_type=? AND entity_id=?
           ORDER BY created_at DESC, id DESC""", (entity, document_id),
    ).fetchall()
    history = present_history(db, history_rows, entity)
    revisions = db.execute(
        """SELECT id, version, reason, created_at FROM document_revisions
           WHERE entity_type=? AND entity_id=? ORDER BY version DESC""",
        (entity, document_id),
    ).fetchall()
    suppliers = db.execute("SELECT id, code, name FROM suppliers ORDER BY name").fetchall()
    products = db.execute("SELECT id, sku, name FROM products ORDER BY name").fetchall()
    purchase_orders = db.execute(
        """SELECT po.id, po.po_number, po.supplier_id, s.name AS supplier
           FROM purchase_orders po JOIN suppliers s ON s.id=po.supplier_id
           WHERE po.status='Submitted' OR po.id=? ORDER BY po.po_number""",
        (document["purchase_order_id"] if entity != "po" else document_id,),
    ).fetchall()
    return render_template(
        "document_detail.html", entity=entity, config=config, document=document,
        items=items, history=history, revisions=revisions, suppliers=suppliers,
        products=products, purchase_orders=purchase_orders,
    )


@bp.post("/documents/<entity>/<int:document_id>/edit")
def edit_document(entity, document_id):
    db = get_db()
    config = config_for(entity)
    try:
        before = snapshot_document(entity, document_id)
        if before["document"]["status"] != "Draft":
            raise ValueError("Hanya dokumen Draft yang dapat diedit.")
        items = _document_items(entity)
        with db:
            if entity == "po":
                db.execute(
                    """UPDATE purchase_orders SET po_number=?, supplier_id=?, order_date=?, expected_date=?
                       WHERE id=?""",
                    (_required("document_number"), _required("supplier_id"), _required("document_date"),
                     request.form.get("expected_date") or None, document_id),
                )
            elif entity == "receipt":
                po_id = _required("purchase_order_id")
                for item in items:
                    _validate_po_product(db, po_id, item[0])
                db.execute(
                    "UPDATE goods_receipts SET receipt_number=?, purchase_order_id=?, receipt_date=? WHERE id=?",
                    (_required("document_number"), po_id, _required("document_date"), document_id),
                )
            elif entity == "invoice":
                po_id = _required("purchase_order_id")
                po = db.execute("SELECT supplier_id FROM purchase_orders WHERE id=?", (po_id,)).fetchone()
                if not po:
                    raise ValueError("PO tidak ditemukan.")
                for item in items:
                    _validate_po_product(db, po_id, item[0])
                db.execute(
                    """UPDATE invoices SET invoice_number=?, purchase_order_id=?, supplier_id=?, invoice_date=?
                       WHERE id=?""",
                    (_required("document_number"), po_id, po[0], _required("document_date"), document_id),
                )
            else:
                raise ValueError("Jenis dokumen tidak dikenali.")
            db.execute(
                f"DELETE FROM {config['items']} WHERE {config['foreign_key']}=?", (document_id,)
            )
            for product_id, quantity, unit_price in items:
                if entity == "po":
                    db.execute(
                        "INSERT INTO po_items (purchase_order_id, product_id, quantity, unit_price) VALUES (?, ?, ?, ?)",
                        (document_id, product_id, quantity, unit_price),
                    )
                elif entity == "receipt":
                    db.execute(
                        "INSERT INTO receipt_items (goods_receipt_id, product_id, quantity) VALUES (?, ?, ?)",
                        (document_id, product_id, quantity),
                    )
                else:
                    db.execute(
                        "INSERT INTO invoice_items (invoice_id, product_id, quantity, unit_price) VALUES (?, ?, ?, ?)",
                        (document_id, product_id, quantity, unit_price),
                    )
            after = snapshot_document(entity, document_id)
            record_history(
                entity, document_id, "DRAFT_UPDATED",
                json.dumps({"before": before, "after": after}, ensure_ascii=False),
            )
        flash("Draft berhasil diperbarui.", "success")
    except Exception as error:
        flash(f"Dokumen tidak dapat diperbarui: {error}", "error")
    return redirect(url_for("main.document_detail", entity=entity, document_id=document_id))


@bp.post("/documents/<entity>/<int:document_id>/<action>")
def document_action(entity, document_id, action):
    try:
        if action == "delete":
            delete_draft(entity, document_id)
            flash("Draft berhasil dihapus.", "success")
            return redirect(url_for("main.documents"))
        new_status = transition_document(entity, document_id, action, request.form.get("reason", ""))
        if entity == "invoice" and new_status == "Submitted":
            match_invoice(document_id, current_app.config["PRICE_TOLERANCE_PERCENT"])
        elif entity in {"po", "receipt"}:
            run_all_matching(current_app.config["PRICE_TOLERANCE_PERCENT"])
        flash(f"Status dokumen diperbarui menjadi {new_status}.", "success")
    except Exception as error:
        flash(f"Tindakan gagal: {error}", "error")
    return redirect(url_for("main.document_detail", entity=entity, document_id=document_id))


@bp.route("/exceptions")
def exceptions():
    rows = get_db().execute(
        """SELECT mr.*, i.invoice_number, po.po_number, s.name AS supplier
           FROM matching_results mr JOIN invoices i ON i.id=mr.invoice_id
           JOIN suppliers s ON s.id=i.supplier_id
           LEFT JOIN purchase_orders po ON po.id=mr.purchase_order_id
           WHERE mr.status != 'Matched' ORDER BY mr.matched_at DESC"""
    ).fetchall()
    results = [{**dict(row), "issues": json.loads(row["details"])} for row in rows]
    return render_template("exceptions.html", results=results)


@bp.route("/data-intake")
def data_intake():
    db = get_db()
    suppliers = db.execute("SELECT id, code, name FROM suppliers ORDER BY name").fetchall()
    products = db.execute("SELECT id, sku, name FROM products ORDER BY name").fetchall()
    purchase_orders = db.execute(
        """SELECT po.id, po.po_number, po.supplier_id, s.name AS supplier
           FROM purchase_orders po JOIN suppliers s ON s.id=po.supplier_id
           WHERE po.status='Submitted' ORDER BY po.id DESC"""
    ).fetchall()
    return render_template(
        "data_intake.html", suppliers=suppliers, products=products,
        purchase_orders=purchase_orders,
    )


@bp.post("/data-intake/import")
def import_excel():
    try:
        counts = import_workbook(request.files.get("workbook"))
        run_all_matching(current_app.config["PRICE_TOLERANCE_PERCENT"])
        flash(
            f"Import berhasil: {counts['purchase_orders']} PO, "
            f"{counts['goods_receipts']} penerimaan, {counts['invoices']} invoice, "
            f"dan {counts['lines']} baris produk.",
            "success",
        )
    except ImportValidationError as error:
        flash(str(error), "error")
    return redirect(url_for("main.data_intake"))


@bp.post("/data-intake/manual")
def manual_entry():
    db = get_db()
    entity = request.form.get("entity", "")
    try:
        with db:
            if entity == "supplier":
                db.execute(
                    "INSERT INTO suppliers (code, name) VALUES (?, ?)",
                    (_required("code"), _required("name")),
                )
            elif entity == "product":
                db.execute(
                    "INSERT INTO products (sku, name) VALUES (?, ?)",
                    (_required("sku"), _required("name")),
                )
            elif entity == "po":
                cursor = db.execute(
                    """INSERT INTO purchase_orders
                       (po_number, supplier_id, order_date, expected_date, status)
                       VALUES (?, ?, ?, ?, 'Draft')""",
                    (_required("po_number"), _required("supplier_id"), _required("order_date"),
                     request.form.get("expected_date") or None),
                )
                db.execute(
                    "INSERT INTO po_items (purchase_order_id, product_id, quantity, unit_price) VALUES (?, ?, ?, ?)",
                    (cursor.lastrowid, _required("product_id"), _positive("quantity"), _positive("unit_price", True)),
                )
            elif entity == "receipt":
                po_id = _required("purchase_order_id")
                _validate_po_product(db, po_id, _required("product_id"))
                cursor = db.execute(
                    "INSERT INTO goods_receipts (receipt_number, purchase_order_id, receipt_date, status) VALUES (?, ?, ?, 'Draft')",
                    (_required("receipt_number"), po_id, _required("receipt_date")),
                )
                db.execute(
                    "INSERT INTO receipt_items (goods_receipt_id, product_id, quantity) VALUES (?, ?, ?)",
                    (cursor.lastrowid, _required("product_id"), _positive("quantity")),
                )
            elif entity == "invoice":
                po_id = _required("purchase_order_id")
                po = db.execute(
                    "SELECT supplier_id FROM purchase_orders WHERE id=? AND status='Submitted'", (po_id,)
                ).fetchone()
                if not po:
                    raise ValueError("PO harus berstatus Submitted.")
                product_id = _required("product_id")
                _validate_po_product(db, po_id, product_id)
                cursor = db.execute(
                    """INSERT INTO invoices
                       (invoice_number, purchase_order_id, supplier_id, invoice_date, status)
                       VALUES (?, ?, ?, ?, 'Draft')""",
                    (_required("invoice_number"), po_id, po[0], _required("invoice_date")),
                )
                db.execute(
                    "INSERT INTO invoice_items (invoice_id, product_id, quantity, unit_price) VALUES (?, ?, ?, ?)",
                    (cursor.lastrowid, product_id, _positive("quantity"), _positive("unit_price", True)),
                )
            else:
                raise ValueError("Jenis data tidak dikenali.")
        if entity in {"po", "receipt", "invoice"}:
            record_history(entity, cursor.lastrowid, "CREATED", "Dokumen dibuat sebagai Draft.")
            db.commit()
        flash("Data berhasil disimpan.", "success")
    except Exception as error:
        flash(f"Data tidak dapat disimpan: {error}", "error")
    return redirect(url_for("main.data_intake"))


def _required(name):
    value = request.form.get(name, "").strip()
    if not value:
        raise ValueError(f"Field {name.replace('_', ' ')} wajib diisi.")
    return value


def _positive(name, allow_zero=False):
    try:
        value = float(_required(name))
    except ValueError as error:
        raise ValueError(f"Field {name.replace('_', ' ')} harus berupa angka.") from error
    if value < 0 or (value == 0 and not allow_zero):
        raise ValueError(f"Field {name.replace('_', ' ')} harus lebih besar dari nol.")
    return value


def _validate_po_product(db, po_id, product_id):
    exists = db.execute(
        """SELECT 1 FROM po_items pi JOIN purchase_orders po ON po.id=pi.purchase_order_id
           WHERE pi.purchase_order_id=? AND pi.product_id=? AND po.status='Submitted'""",
        (po_id, product_id),
    ).fetchone()
    if not exists:
        raise ValueError("Produk tidak terdapat pada PO Submitted yang dipilih.")


def _document_items(entity):
    product_ids = request.form.getlist("product_id")
    quantities = request.form.getlist("quantity")
    prices = request.form.getlist("unit_price") if entity in {"po", "invoice"} else []
    if not product_ids or len(product_ids) != len(quantities):
        raise ValueError("Minimal satu baris produk wajib diisi.")
    if len(set(product_ids)) != len(product_ids):
        raise ValueError("Produk yang sama tidak boleh diulang dalam satu dokumen.")
    items = []
    for index, product_id in enumerate(product_ids):
        try:
            quantity = float(quantities[index])
            unit_price = float(prices[index]) if entity in {"po", "invoice"} else None
        except (ValueError, IndexError) as error:
            raise ValueError("Kuantitas dan harga harus berupa angka.") from error
        if quantity <= 0 or (unit_price is not None and unit_price < 0):
            raise ValueError("Kuantitas harus positif dan harga tidak boleh negatif.")
        items.append((product_id, quantity, unit_price))
    return items


@bp.post("/seed")
def seed():
    created = seed_demo_data()
    if created:
        run_all_matching(current_app.config["PRICE_TOLERANCE_PERCENT"])
        flash("Data demo berhasil dibuat dan dicocokkan.", "success")
    else:
        flash("Data sudah tersedia; tidak ada data demo yang ditambahkan.", "info")
    return redirect(url_for("main.dashboard"))


@bp.post("/matching/run")
def run_matching():
    results = run_all_matching(current_app.config["PRICE_TOLERANCE_PERCENT"])
    flash(f"Matching selesai untuk {len(results)} invoice.", "success")
    return redirect(url_for("main.dashboard"))
