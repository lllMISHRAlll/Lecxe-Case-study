# Data changes

Every change made to company data, newest last.

## 001 PO line units

- When: 2026-11-19 11:02 UTC
- Target: company DB
- Table: proc_po_lines (unit)
- Reason: Unit spellings on PO lines (KG, Nos., Unit, Set, Ltr, Mtr) aligned to the item unit vocabulary so quantities can be compared.
- Rows changed: 61
- Backup: db/changes/001_po_line_units/backup.csv
- Roll back: `make normalise-rollback CHANGE=001` (or run db/changes/001_po_line_units/rollback.sql)
- Findings left for a business decision:
  - none

## 002 PO payment terms

- When: 2026-11-19 11:02 UTC
- Target: company DB
- Table: proc_purchase_orders (payment_terms)
- Reason: Payment-term spellings collapsed to canonical terms, empty strings set to NULL.
- Rows changed: 18
- Backup: db/changes/002_po_payment_terms/backup.csv
- Roll back: `make normalise-rollback CHANGE=002` (or run db/changes/002_po_payment_terms/rollback.sql)
- Findings left for a business decision:
  - none

## 003 Vendor payment terms

- When: 2026-11-19 11:02 UTC
- Target: company DB
- Table: proc_vendors (payment_terms)
- Reason: Payment-term spellings collapsed to canonical terms, empty strings set to NULL.
- Rows changed: 12
- Backup: db/changes/003_vendor_payment_terms/backup.csv
- Roll back: `make normalise-rollback CHANGE=003` (or run db/changes/003_vendor_payment_terms/rollback.sql)
- Findings left for a business decision:
  - none

## 004 Payment tranche stages

- When: 2026-11-19 11:02 UTC
- Target: company DB
- Table: proc_po_payment_tranches (stage)
- Reason: Payment-term spellings collapsed to canonical terms.
- Rows changed: 4
- Backup: db/changes/004_tranche_stages/backup.csv
- Roll back: `make normalise-rollback CHANGE=004` (or run db/changes/004_tranche_stages/rollback.sql)
- Findings left for a business decision:
  - none

## 005 Item name spaces

- When: 2026-11-19 11:02 UTC
- Target: company DB
- Table: inv_items (name)
- Reason: Leading, trailing and repeated spaces removed from item names. Names that would then equal another item's name are skipped and reported.
- Rows changed: 8
- Backup: db/changes/005_item_name_spaces/backup.csv
- Roll back: `make normalise-rollback CHANGE=005` (or run db/changes/005_item_name_spaces/rollback.sql)
- Findings left for a business decision:
  - Item BO-EL-0193 ('Electromagnet Solenoid for AFC Mechanism ') not trimmed: the trimmed name already belongs to another item

## 006 PO header date lists

- When: 2026-11-19 11:02 UTC
- Target: company DB
- Table: proc_purchase_orders (expected_delivery_date, expected_dispatch_date)
- Reason: NULL expected-date lists replaced with [] so every row uses one empty form.
- Rows changed: 4
- Backup: db/changes/006_po_date_lists/backup.csv
- Roll back: `make normalise-rollback CHANGE=006` (or run db/changes/006_po_date_lists/rollback.sql)
- Findings left for a business decision:
  - none

## 007 PO line date lists

- When: 2026-11-19 11:02 UTC
- Target: company DB
- Table: proc_po_lines (expected_delivery_date, expected_dispatch_date)
- Reason: NULL expected-date lists replaced with [] so every row uses one empty form.
- Rows changed: 5
- Backup: db/changes/007_po_line_date_lists/backup.csv
- Roll back: `make normalise-rollback CHANGE=007` (or run db/changes/007_po_line_date_lists/rollback.sql)
- Findings left for a business decision:
  - none

