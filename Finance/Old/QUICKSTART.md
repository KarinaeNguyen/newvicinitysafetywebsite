# Quick Start Guide

## 5-Minute Setup

### 1. Install Dependencies

```powershell
cd "d:\Vicinity Safety\Finance"
pip install -r requirements.txt
```

### 2. Initialize Database

```powershell
python
>>> from core.db import init_db
>>> init_db()
>>> exit()
```

### 3. Add Your First Log Entry (CLI)

```powershell
python app.py add
```

Follow the prompts:
- **SKU**: `WIDGET-001`
- **Qty**: `10`
- **Unit Price**: `19.99`
- **Customer**: `Test Co`
- Leave other fields blank

**Result**: Log auto-detects as `SALES` and decrements inventory by 10 units

### 4. View Dashboard

```powershell
streamlit run dashboard.py
```

Opens `http://localhost:8501` with KPIs, products, and charts.

---

## Key Commands

| Task | Command |
|------|---------|
| Add log entry | `python app.py add` |
| View KPIs | `python app.py show-kpis` |
| View all products | `python app.py show-products` |
| View recent logs | `python app.py show-recent` |
| Start dashboard | `streamlit run dashboard.py` |
| Run tests | `pytest tests/ -v` |

---

## How It Works (30-second version)

1. **Input** → User enters transaction fields (SKU, qty, price, customer, etc.)
2. **Validate** → Fields coerced to correct types (int, float, date, etc.)
3. **Detect** → System scores all log types; picks highest (SALES, PURCHASE, etc.)
4. **Store** → Log inserted + side effects applied
   - **SALES** → on_hand -= qty
   - **PURCHASE** → on_hand += qty
   - **ADJUSTMENT** → on_hand += qty_delta
5. **Dashboard** → Real-time KPI charts, inventory, sales trends

---

## Example Workflows

### Log a Sale

```powershell
python app.py add

# Enter:
# SKU: WIDGET-001
# Qty: 5
# Unit Price: 19.99
# Amount: 99.95
# Customer: Acme Corp

# Result:
# ✓ Log entry created (ID: 1)
# Type: SALES
# Confidence: high
```

### Record Receipt

```powershell
python app.py add

# Enter:
# SKU: WIDGET-001
# Qty: 100
# Unit Cost: 10.00
# Vendor: Supplier Inc

# Result:
# ✓ Log entry created (ID: 2)
# Type: PURCHASE
# Confidence: high
```

### Update Product Master

```powershell
python app.py add

# Enter:
# SKU: WIDGET-001
# Name: Blue Widget
# Unit Price: 19.99
# Barcode: 123456789

# Result:
# ✓ Log entry created (ID: 3)
# Type: PRODUCT_UPDATE
# Confidence: high
```

---

## File Reference

| File | Purpose |
|------|---------|
| `app.py` | CLI interface (Typer) |
| `dashboard.py` | Dashboard (Streamlit) |
| `core/models.py` | Database schema |
| `core/db.py` | SQLAlchemy engine |
| `core/config.py` | Config loader |
| `core/validate.py` | Input validation |
| `core/detect.py` | Log type detection |
| `core/services.py` | Business logic |
| `core/queries.py` | Dashboard queries |
| `config/log_types.yml` | Log type definitions |

---

## Customization

### Add a New Log Type

Edit `config/log_types.yml`:

```yaml
log_types:
  CUSTOM_TYPE:
    fields: [field1, field2, ...]
    detect:
      required_all: [...]
      required_any: [...]
      forbidden_any: [...]
```

### Change Scoring Rules

In `config/log_types.yml`:

```yaml
scoring:
  required_all_present: 5      # ← adjust
  required_all_missing: -10    # ← adjust
  required_any_present: 2      # ← adjust
  forbidden_any_present: -100  # ← adjust
```

### Override Database Path

```powershell
$env:ACCOUNTING_DB_PATH = "C:\path\to\accounting.db"
python app.py show-kpis
```

---

## Troubleshooting

**"ModuleNotFoundError: No module named 'core'"**
- Ensure you're in project root: `cd "d:\Vicinity Safety\Finance"`

**Detection confidence is "low"**
- Check log output for `candidate_scores`
- Ensure you're providing enough distinguishing fields
- Review detection rules in `config/log_types.yml`

**Database locked error**
- Close dashboard before running CLI
- Or specify different DB path via env var

---

## Next Steps

1. ✅ Run through Quick Start above
2. Review [README.md](README.md) for full documentation
3. Edit `config/log_types.yml` to match your business rules
4. Run tests: `pytest tests/ -v`
5. Deploy dashboard for team access

---

**Questions?** Check README.md or review test cases in `tests/test_core.py` for examples.
