# Local AI Build Guide — Standardized Python Accounting + Unified Log Form

## Goal
Build a simple, standardized Python accounting/log system that:
- Presents a single unified “Log Form” (one input experience).
- Auto-detects log type after submission based on entered fields (deterministic rules).
- Stores all entries in a database (SQLite).
- Supports Product Update logs (SKU, Barcode, Pricing, Unit Count).
- Provides a dashboard window summarizing KPIs, product inventory, and recent logs.
- Keeps column naming compatible with an external “master sheet” by using config-driven field definitions.

## Non-Goals
- No fancy ERP features (no multi-currency, no complex tax engine).
- No external cloud dependencies; runs locally.
- No heavy authentication.

---

## Architecture Summary
We use:
1) A **single canonical log table** to store all records (schema-stable).
2) A **product table** to support inventory & pricing dashboards.
3) A **movement table** to preserve inventory changes and enable audits.

All logs go into `log_entries`. Some log types also “project” into `products` and `product_movements`.

---

## Data Model (SQLite)
### Table: log_entries (source of truth)
- id (INTEGER PK AUTOINCREMENT or UUID TEXT)
- created_at (TEXT ISO8601)
- log_type (TEXT)  # auto-detected
- ref_no (TEXT NULL)
- counterparty (TEXT NULL) # customer/vendor
- notes (TEXT NULL)
- payload_json (TEXT) # JSON blob with all fields as entered (sheet-compatible)

### Table: products (normalized for dashboard)
- sku (TEXT PRIMARY KEY)
- barcode (TEXT UNIQUE NULL)
- name (TEXT NULL)
- unit_cost (REAL NULL)
- unit_price (REAL NULL)
- on_hand (INTEGER NOT NULL DEFAULT 0)
- updated_at (TEXT ISO8601)

### Table: product_movements (audit trail; recommended)
- id (INTEGER PK AUTOINCREMENT)
- created_at (TEXT ISO8601)
- sku (TEXT NOT NULL)
- qty_delta (INTEGER NOT NULL)  # +in / -out / 0
- unit_cost (REAL NULL)        # snapshot, optional
- unit_price (REAL NULL)       # snapshot, optional
- source_log_id (INTEGER or TEXT FK -> log_entries.id)

---

## Log Types (initial)
1) PRODUCT_UPDATE
2) SALES
3) PURCHASE
4) EXPENSE
5) ADJUSTMENT (inventory correction)

Log types and their fields are defined in config (`config/log_types.yml`).

---

## Unified Log Form Behavior
The user fills a single form with a superset of fields. Most fields are optional.
After submission:
1) Validate input types (numbers, dates).
2) Run detection rules to determine `log_type`.
3) Persist `log_entries` record with full payload JSON.
4) If log_type impacts products/inventory:
   - update `products`
   - append `product_movements`

---

## Log Type Detection (deterministic scoring)
Rules live in config. Detection must:
- evaluate required_all, required_any, forbidden_any
- assign a score per type
- select the highest-scoring match
- if tie or low confidence: prompt user to confirm selection

Suggested scoring:
- +5 for each satisfied required_all field
- +2 for each satisfied required_any field (up to max)
- -100 if any forbidden_any present
- -10 if missing a required_all field

Confidence:
- High if winner score >= 12 and margin >= 5
- Medium if winner score >= 8
- Low otherwise (ask user to choose)

---

## UI
Two entry points:
1) CLI entry (fast data capture; good for barcode scanners that emulate keyboard)
2) Dashboard window via Streamlit

CLI:
- command: `python -m app add`
- prompts for standard/common fields first, then optional extras
- supports “press Enter to skip”
- supports barcode input as a normal string field

Dashboard:
- run: `streamlit run dashboard.py`
- shows KPI tiles + tables + charts
- includes a “Recent logs” table with filters
- includes “Products” table with SKU, barcode, price, cost, on_hand
- includes low stock and top sellers

---

## Implementation Plan (Milestones)
M1: DB + models
- SQLAlchemy models for all tables
- DB init/migrations-lite (create tables if not exist)

M2: Config-driven log types
- parse YAML config
- generate prompt schema from config
- validate payload types

M3: Detection engine
- apply config detection rules to payload
- return (log_type, score, confidence)

M4: Persistence services
- insert into log_entries
- product projection:
  - upsert products fields if present
  - on_hand update:
    - if payload has qty_delta: apply it
    - else if has unit_count as absolute set: treat as set-on-hand (configurable)
  - insert movement record if qty changed or product_update occurred

M5: Dashboard
- read data via SQLAlchemy
- compute KPIs using pandas
- render Streamlit components

---

## Key Constraints
- Keep field names in payload matching the “master sheet” column headers.
- Never break existing logs if config changes; payload_json preserves history.
- Use SQLite file `accounting.db` by default; allow override via env var.

---

## Commands
Install:
- `pip install sqlalchemy pydantic typer streamlit pandas pyyaml`

Run CLI:
- `python app.py add`

Run dashboard:
- `streamlit run dashboard.py`

---

## Testing Expectations
- Unit tests for detection engine
- Unit tests for product projection (inventory math)
- Smoke test: add a PRODUCT_UPDATE then dashboard shows updated product row
