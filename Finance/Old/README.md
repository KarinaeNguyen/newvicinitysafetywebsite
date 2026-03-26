# Accounting & Inventory Log System

A lightweight, standardized Python accounting system for logging inventory, sales, purchases, and expenses with automatic log type detection.

## Features

✅ **Single Unified Log Form** — One input experience for all transaction types
✅ **Auto-Detection** — Deterministic rules detect log type from entered fields
✅ **SQLite Database** — Local storage, no cloud dependencies
✅ **Product Inventory** — Track SKUs, pricing, and stock levels
✅ **Audit Trail** — Every inventory movement tied to source transaction
✅ **CLI & Dashboard** — Both interfaces read from same database

## Project Structure

```
.
├── app.py                    # CLI interface (Typer)
├── dashboard.py              # Dashboard (Streamlit)
├── config/
│   └── log_types.yml        # Log type definitions & detection rules
├── core/
│   ├── __init__.py
│   ├── db.py                # SQLAlchemy engine & session
│   ├── models.py            # LogEntry, Product, ProductMovement
│   ├── config.py            # YAML config loader
│   ├── validate.py          # Input validation & coercion
│   ├── detect.py            # Log type detection engine
│   ├── services.py          # Business logic (insert, update, project)
│   └── queries.py           # Dashboard query helpers
├── tests/
│   └── test_core.py         # Unit tests
├── requirements.txt
└── README.md
```

## Installation

### 1. Clone/Setup

```bash
cd "d:\Vicinity Safety\Finance"
```

### 2. Create Virtual Environment (Optional but Recommended)

**Windows:**
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

**macOS/Linux:**
```bash
python -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Initialize Database

```bash
python -m typer app run init
```

Or directly:
```bash
python
>>> from core.db import init_db
>>> init_db()
```

## Usage

### CLI Interface

The CLI prompts you through all fields and auto-detects the log type.

#### Add a New Log Entry

```bash
python app.py add
```

Interactive prompts will walk you through:
1. Common fields (ref_no, date)
2. Product/inventory fields (SKU, quantity, etc.)
3. Pricing fields (unit cost, unit price, amount)
4. Party fields (customer/vendor)
5. Additional fields (category, reason, discounts, etc.)

#### View Inventory Summary

```bash
python app.py show-kpis
```

Shows: total products, units on hand, inventory value, total logs.

#### View All Products

```bash
python app.py show-products
```

Displays product table with SKU, name, on-hand quantity, pricing.

#### View Recent Logs

```bash
python app.py show-recent
```

Shows last 20 transaction logs.

### Dashboard

Start the Streamlit dashboard:

```bash
streamlit run dashboard.py
```

Opens browser to `http://localhost:8501`

**Tabs:**
- **Products** — Full product inventory with values
- **Low Stock** — Products below threshold with bar chart
- **Recent Logs** — Filterable transaction history
- **Sales Analysis** — Sales revenue trends and summary stats

## Log Types

| Type | Detection Rules | Side Effects |
|------|---|---|
| **PRODUCT_UPDATE** | SKU + (price \| barcode \| name) | Creates/updates Product record |
| **SALES** | SKU + qty + unit_price + customer | Decrements on_hand; records movement |
| **PURCHASE** | SKU + qty + unit_cost + vendor | Increments on_hand; records movement |
| **EXPENSE** | amount + (vendor \| category) | No inventory impact |
| **ADJUSTMENT** | SKU + qty_delta | Updates on_hand (e.g., loss, damage) |

See `config/log_types.yml` for full detection rules.

## Detection Logic

Detection uses a **scoring algorithm**:

```
+5 per required_all field satisfied
-10 per required_all field missing
+2 per required_any field satisfied
-100 if any forbidden_any field present
```

**Confidence levels:**
- **High** — score >= 12 AND margin >= 5
- **Medium** — score >= 8
- **Low** — else (user prompted to confirm)

## Database Schema

### log_entries
Source of truth; stores all transaction logs with full payload JSON.

```sql
id, created_at, log_type, ref_no, counterparty, notes, payload_json
```

### products
Normalized inventory; used for dashboard & fast lookups.

```sql
sku (PK), barcode (UNIQUE), name, unit_cost, unit_price, on_hand, updated_at
```

### product_movements
Audit trail; every inventory change linked to source log.

```sql
id, created_at, sku, qty_delta, unit_cost, unit_price, source_log_id (FK)
```

## Configuration

### Log Types (`config/log_types.yml`)

Edit this file to:
- Add new log types or fields
- Modify detection rules
- Change scoring weights
- Set confidence thresholds

Example adding a new log type:

```yaml
log_types:
  RETURN:
    description: "Customer return / refund"
    fields:
      - sku
      - qty
      - reason
      - ref_no
    detect:
      required_all: [sku, qty]
      required_any: [reason]
      forbidden_any: [vendor, unit_cost]
```

### Database Path

By default, uses `accounting.db` in current directory.

Override via environment variable:

```bash
$env:ACCOUNTING_DB_PATH = "C:\path\to\accounting.db"
python app.py show-kpis
```

## Validation Rules

Input fields are automatically validated and coerced:

- **Integers**: `qty`, `qty_delta`, `unit_count` 
  - Accepts int, float (if whole), strings
- **Floats**: `unit_cost`, `unit_price`, `amount`, `discount`, `tax`, `shipping`
  - Accepts int, float, strings
- **Dates**: `date`, `created_at`
  - Parses YYYY-MM-DD → ISO8601 string
- **Strings**: `sku`, `name`, `customer`, `vendor`, etc.
  - Strips whitespace; treats empty string as None

Invalid inputs raise `ValidationError` with details.

## Testing

Run the test suite:

```bash
pytest tests/ -v
```

Tests cover:
- Log type detection (all 5 types)
- Input validation & coercion
- Service logic (product updates, inventory math)

## Inventory Math Rules

- **SALES**: on_hand -= qty (must have stock)
- **PURCHASE**: on_hand += qty
- **ADJUSTMENT**: on_hand += qty_delta (can be negative)
- **PRODUCT_UPDATE**: no inventory impact
- **EXPENSE**: no inventory impact

## Common Workflows

### Log a Sale

```bash
python app.py add
# Enter: sku, qty, unit_price, amount, customer
# System detects: SALES
```

### Record Receipt (Purchase Order)

```bash
python app.py add
# Enter: sku, qty, unit_cost, vendor
# System detects: PURCHASE
```

### Adjust Inventory (Damage/Loss)

```bash
python app.py add
# Enter: sku, qty_delta (negative), reason
# System detects: ADJUSTMENT
```

### Add Product Master Data

```bash
python app.py add
# Enter: sku, name, barcode, unit_price
# System detects: PRODUCT_UPDATE
```

## Troubleshooting

### "No module named 'core'"
- Ensure you're running from project root: `cd "d:\Vicinity Safety\Finance"`
- Check Python path includes current directory

### "database.db locked"
- Only one process can write to SQLite at a time
- Close dashboard before running CLI (or vice versa)
- Or use `ACCOUNTING_DB_PATH` to point to different database

### Detection confidence is "low"
- Check `candidate_scores` output
- Verify fields match detection rules in `config/log_types.yml`
- Consider adding more required fields to disambiguate

### Barcode unique constraint error
- Same barcode assigned to different SKUs
- Edit product or use `--force-type` to skip detection

## Environment Variables

- `ACCOUNTING_DB_PATH` — Path to SQLite database (default: `accounting.db`)

## Performance Notes

- SQLite is suitable for local, single-user use
- For large volumes (>100k logs), consider migration to PostgreSQL
- Dashboard queries are optimized for <10k products
- Increase Streamlit timeout if dashboard is slow:
  ```toml
  # .streamlit/config.toml
  [client]
  showRunningSpinner = false
  ```

## Future Enhancements

- [ ] Multi-user support & authentication
- [ ] REST API (FastAPI)
- [ ] Export to Excel/CSV
- [ ] Barcode scanner integration
- [ ] Mobile app (Flutter)
- [ ] Cloud sync (optional)
- [ ] Advanced reporting (profit margins, ABC analysis)
- [ ] Recurring transactions (subscriptions)

## License

Internal use only.
