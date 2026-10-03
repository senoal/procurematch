from pathlib import Path

import pytest

from app import create_app
from app.database import get_db, seed_demo_data
from app.matching import run_all_matching


@pytest.fixture()
def app():
    database = Path(__file__).with_name("test.sqlite")
    database.unlink(missing_ok=True)
    application = create_app({"TESTING": True, "DATABASE": str(database)})
    yield application
    database.unlink(missing_ok=True)


def test_demo_matching_detects_expected_results(app):
    with app.app_context():
        assert seed_demo_data() is True
        results = run_all_matching(1.0)
        assert [status for status, _ in results] == ["Matched", "Partial Match", "Mismatch"]
        price_issue = results[2][1][0]
        assert price_issue["code"] == "PRICE_MISMATCH"


def test_matching_is_idempotent(app):
    with app.app_context():
        seed_demo_data()
        run_all_matching()
        run_all_matching()
        count = get_db().execute("SELECT COUNT(*) FROM matching_results").fetchone()[0]
        assert count == 3


def test_pages_render(app):
    client = app.test_client()
    assert client.get("/").status_code == 200
    assert client.get("/documents").status_code == 200
    assert client.get("/exceptions").status_code == 200
    assert client.get("/data-intake").status_code == 200
    assert client.get("/health").get_json() == {"status": "ok", "database": "connected"}


def test_excel_template_imports_and_matches(app):
    client = app.test_client()
    template = Path(__file__).parents[1] / "app" / "static" / "templates" / "purchase_order_import_template.xlsx"
    with template.open("rb") as workbook:
        response = client.post(
            "/data-intake/import",
            data={"workbook": (workbook, "purchase_order_import_template.xlsx")},
            content_type="multipart/form-data",
            follow_redirects=True,
        )
    assert response.status_code == 200
    assert b"Import berhasil" in response.data
    with app.app_context():
        db = get_db()
        assert db.execute("SELECT COUNT(*) FROM purchase_orders").fetchone()[0] == 1
        assert db.execute("SELECT status FROM matching_results").fetchone()[0] == "Matched"


def test_manual_master_data_entry(app):
    client = app.test_client()
    response = client.post(
        "/data-intake/manual",
        data={"entity": "supplier", "code": "SUP-T01", "name": "Test Supplier"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Data berhasil disimpan" in response.data
    with app.app_context():
        assert get_db().execute("SELECT name FROM suppliers WHERE code='SUP-T01'").fetchone()[0] == "Test Supplier"


def test_invoice_revision_preserves_snapshot_and_rematches(app):
    with app.app_context():
        seed_demo_data()
        run_all_matching()
    client = app.test_client()
    response = client.post(
        "/documents/invoice/1/revise",
        data={"reason": "Harga supplier perlu dikoreksi"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Draft" in response.data
    with app.app_context():
        db = get_db()
        invoice = db.execute("SELECT status, version FROM invoices WHERE id=1").fetchone()
        assert tuple(invoice) == ("Draft", 2)
        assert db.execute("SELECT COUNT(*) FROM document_revisions WHERE entity_type='invoice' AND entity_id=1").fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM matching_results WHERE invoice_id=1").fetchone()[0] == 0

    response = client.post(
        "/documents/invoice/1/edit",
        data={
            "document_number": "INV-NE-1001",
            "purchase_order_id": "1",
            "document_date": "2026-09-25",
            "product_id": ["1"],
            "quantity": ["10"],
            "unit_price": ["13000000"],
        },
        follow_redirects=True,
    )
    assert b"Draft berhasil diperbarui" in response.data
    assert b"Unit price" in response.data
    assert b"Rp 12.500.000" in response.data
    assert b"Rp 13.000.000" in response.data
    assert b'&quot;before&quot;' not in response.data
    client.post("/documents/invoice/1/submit", follow_redirects=True)
    with app.app_context():
        db = get_db()
        assert db.execute("SELECT status FROM invoices WHERE id=1").fetchone()[0] == "Submitted"
        assert db.execute("SELECT status FROM matching_results WHERE invoice_id=1").fetchone()[0] == "Mismatch"
        actions = [row[0] for row in db.execute("SELECT action FROM transaction_history WHERE entity_type='invoice' AND entity_id=1")]
        assert "REVISION_OPENED" in actions
        assert "DRAFT_UPDATED" in actions
        assert "SUBMITTED" in actions


def test_only_unprocessed_first_version_draft_can_be_deleted(app):
    with app.app_context():
        db = get_db()
        db.execute("INSERT INTO suppliers (code, name) VALUES ('SUP-D', 'Draft Supplier')")
        db.execute("INSERT INTO products (sku, name) VALUES ('SKU-D', 'Draft Product')")
        db.execute("INSERT INTO purchase_orders (po_number, supplier_id, order_date, status) VALUES ('PO-D', 1, '2026-10-03', 'Draft')")
        db.execute("INSERT INTO po_items (purchase_order_id, product_id, quantity, unit_price) VALUES (1, 1, 1, 100)")
        db.commit()
    response = app.test_client().post("/documents/po/1/delete", follow_redirects=True)
    assert b"Draft berhasil dihapus" in response.data
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM purchase_orders").fetchone()[0] == 0
