# Build Checklist

## 1) Bootstrap
- [ ] Create repo structure per ARCHITECTURE_MAP.yml
- [ ] Add dependencies: sqlalchemy, pydantic, typer, streamlit, pandas, pyyaml

## 2) Database
- [ ] Implement core/db.py (engine + session)
- [ ] Implement core/models.py
- [ ] Create tables if not exist on startup

## 3) Config
- [ ] Implement core/config.py to load config/log_types.yml
- [ ] Provide helper: get_fields_for_type(type), get_detection_rules(type)

## 4) Validation
- [ ] Implement core/validate.py:
  - ints: qty, qty_delta, unit_count
  - floats: unit_cost, unit_price, amount, discount, tax, shipping
  - date parse (YYYY-MM-DD) into ISO string
  - strip strings; treat "" as null

## 5) Detection
- [ ] Implement core/detect.py scoring algorithm
- [ ] Return {log_type, score, confidence, debug_breakdown}

## 6) Persistence + Business Logic
- [ ] Implement core/services.py:
  - insert_log_entry(payload, detected_type)
  - product upsert by sku
  - barcode unique enforcement
  - inventory math rules (qty_delta vs unit_count)
  - record product_movements with source_log_id

## 7) CLI
- [ ] app.py Typer command `add`
- [ ] Ask common fields first; then additional optional fields
- [ ] Confirm log_type when confidence low

## 8) Dashboard
- [ ] dashboard.py:
  - KPI tiles
  - Products table
  - Low stock table
  - Recent logs table + filters
  - Sales over time chart

## 9) Tests
- [ ] Detection tests: each sample payload maps correctly
- [ ] Service tests: product updates adjust on_hand correctly
