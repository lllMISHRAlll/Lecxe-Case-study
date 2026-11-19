"""The seed must reproduce every quirk found in the real company data."""

from sqlalchemy import text


def scalar(db, sql):
    with db.read_engine.connect() as conn:
        return conn.execute(text(sql)).scalar()


def test_seed_has_raw_unit_spellings(raw_db):
    units = scalar(raw_db, "select array_agg(distinct unit) from proc_po_lines")
    assert {"KG", "Nos.", "Nos", "Unit", "Set", "Ltr", "Mtr", "pcs"} <= set(units)


def test_seed_has_payment_term_variants(raw_db):
    terms = scalar(raw_db, "select array_agg(distinct payment_terms) from proc_purchase_orders")
    assert {"10 DAys PDC Against Dispatch", "10 Days PDC Agst Dispatch", ""} <= set(terms)


def test_seed_has_vendor_without_terms_and_typo_terms(raw_db):
    assert scalar(raw_db, "select count(*) from proc_vendors where payment_terms is null") >= 1
    assert scalar(
        raw_db, "select count(*) from proc_vendors where payment_terms = '100% Payment Adavcne'"
    ) == 1


def test_seed_has_null_and_empty_date_lists(raw_db):
    assert scalar(raw_db, "select count(*) from proc_purchase_orders "
                          "where expected_delivery_date is null") >= 1
    assert scalar(raw_db, "select count(*) from proc_purchase_orders "
                          "where expected_delivery_date::text = '[]'") >= 1


def test_seed_has_item_without_stock_row_and_without_category(raw_db):
    assert scalar(raw_db, "select count(*) from inv_items i where not exists "
                          "(select 1 from inv_current_stock s where s.item_id = i.id)") >= 1
    assert scalar(raw_db, "select count(*) from inv_items where category_id is null") >= 1


def test_seed_has_usd_order(raw_db):
    assert scalar(raw_db, "select count(*) from proc_purchase_orders where currency = 'USD'") == 1


def test_seed_has_untrimmed_names_and_a_trim_collision(raw_db):
    assert scalar(raw_db, "select count(*) from inv_items "
                          "where name <> regexp_replace(btrim(name), '\\s+', ' ', 'g')") >= 3
    assert scalar(raw_db, "select count(*) from inv_items a join inv_items b on a.id <> b.id "
                          "and regexp_replace(btrim(a.name), '\\s+', ' ', 'g') = b.name") == 1


def test_seed_has_open_overdue_po_and_unresolved_unexpected_receipt(raw_db):
    assert scalar(raw_db, "select count(*) from proc_purchase_orders "
                          "where status in ('placed', 'partial')") >= 2
    assert scalar(raw_db, "select count(*) from proc_unexpected_receipts "
                          "where resolved_po_id is null") >= 1

