# API Reference

Quick reference for all modules, classes, and key functions.

---

## `core.db`

**Database engine and session management.**

### Functions

```python
init_db() -> None
    Create all tables if they don't exist.
    
get_session() -> Session
    Return a new SQLAlchemy session.
```

### Constants

```python
DATABASE_URL: str
    SQLite connection string (from ACCOUNTING_DB_PATH env or default)
    
engine: Engine
    SQLAlchemy engine instance
    
SessionLocal: sessionmaker
    Session factory
```

---

## `core.models`

**SQLAlchemy ORM models.**

### Classes

```python
class LogEntry(Base):
    id: int (PK, AUTOINCREMENT)
    created_at: str (ISO8601)
    log_type: str (PRODUCT_UPDATE, SALES, PURCHASE, EXPENSE, ADJUSTMENT)
    ref_no: str (nullable)
    counterparty: str (customer or vendor, nullable)
    notes: str (nullable)
    payload_json: str (full JSON payload)
    
    Relationships:
    - product_movements: List[ProductMovement]


class Product(Base):
    sku: str (PK)
    barcode: str (UNIQUE, nullable)
    name: str (nullable)
    unit_cost: float (nullable)
    unit_price: float (nullable)
    on_hand: int (default=0)
    updated_at: str (ISO8601)


class ProductMovement(Base):
    id: int (PK, AUTOINCREMENT)
    created_at: str (ISO8601)
    sku: str (FK -> Product.sku)
    qty_delta: int (+ for inbound, - for outbound, 0 for neutral)
    unit_cost: float (snapshot, nullable)
    unit_price: float (snapshot, nullable)
    source_log_id: int (FK -> LogEntry.id)
    
    Relationships:
    - log_entry: LogEntry
```

---

## `core.config`

**Configuration loading and access.**

### Classes

```python
class LogTypeConfig:
    def __init__(config_path: Path = CONFIG_PATH)
        Load YAML config file.
    
    def get_log_types() -> List[str]
        Return all log type names: [PRODUCT_UPDATE, SALES, ...]
    
    def get_fields_for_type(log_type: str) -> List[str]
        Return field names for a log type.
    
    def get_detection_rules(log_type: str) -> Dict[str, List[str]]
        Return {required_all, required_any, forbidden_any} for a type.
    
    def get_scoring_rules() -> Dict[str, int]
        Return scoring multipliers.
    
    def get_confidence_thresholds() -> Dict[str, str]
        Return confidence level definitions.
```

### Functions

```python
get_config() -> LogTypeConfig
    Get or create config singleton.
```

### Config File Structure (`config/log_types.yml`)

```yaml
log_types:
  LOG_TYPE_NAME:
    description: str
    fields: [field_name, ...]
    detect:
      required_all: [field_name, ...]    # All must be present
      required_any: [field_name, ...]    # At least one must be present
      forbidden_any: [field_name, ...]   # None must be present

scoring:
  required_all_present: int              # +5 per satisfied
  required_all_missing: int              # -10 per missing
  required_any_present: int              # +2 per satisfied
  forbidden_any_present: int             # -100 if any present

confidence:
  high: str                              # "winner_score >= 12 AND margin >= 5"
  medium: str                            # "winner_score >= 8"
  low: str                               # "else"
```

---

## `core.validate`

**Input validation and type coercion.**

### Exceptions

```python
class ValidationError(Exception)
    Raised when validation fails. Contains detailed error message.
```

### Functions

```python
validate_payload(payload: Dict[str, Any]) -> Dict[str, Any]
    Validate and coerce all fields in payload.
    
    Integer fields: qty, qty_delta, unit_count
    Float fields: unit_cost, unit_price, amount, discount, tax, shipping
    Date fields: date, created_at
    String fields: sku, barcode, name, customer, vendor, ...
    
    Returns: coerced payload
    Raises: ValidationError

coerce_int(value: Any, field_name: str) -> int
    Coerce value to integer. Accepts int, float (if whole), string.
    Raises: ValidationError

coerce_float(value: Any, field_name: str) -> float
    Coerce value to float. Accepts int, float, string.
    Raises: ValidationError

coerce_date(value: Any) -> str
    Parse date to ISO8601. Accepts YYYY-MM-DD, datetime, None.
    Returns: ISO8601 string or None
    Raises: ValidationError

coerce_string(value: Any) -> str
    Strip whitespace, convert to string. Empty string → None.
    Returns: trimmed string or None

check_required_fields(
    payload: Dict[str, Any], 
    required_fields: list
) -> Tuple[bool, list]
    Check if all required fields present and non-empty.
    Returns: (all_present: bool, missing_fields: list)
```

---

## `core.detect`

**Log type detection engine.**

### Dataclasses

```python
@dataclass
class DetectionResult:
    log_type: str                              # Detected type
    score: int                                 # Final score
    confidence: str                            # high|medium|low
    candidate_scores: Dict[str, int]           # Scores for all types
    debug_breakdown: Dict[str, Dict[str, Any]] # Per-field scoring
```

### Classes

```python
class DetectionEngine:
    def detect(payload: Dict[str, Any]) -> DetectionResult
        Detect log type and return result with confidence.
        Scoring:
        - +5 per required_all satisfied
        - -10 per required_all missing
        - +2 per required_any satisfied
        - -100 if any forbidden_any present
        
        Confidence:
        - high: score >= 12 AND margin >= 5
        - medium: score >= 8
        - low: else
```

### Functions

```python
get_detection_engine() -> DetectionEngine
    Get or create detection engine singleton.
```

---

## `core.services`

**Business logic for log insertion and inventory management.**

### Exceptions

```python
class ServiceError(Exception)
    Raised when business logic error occurs.
```

### Classes

```python
class LogService:
    def __init__(session: Session)
        Initialize with database session.
    
    def insert_log(
        payload: Dict[str, Any],
        force_log_type: str = None,
        validate_input: bool = True
    ) -> Tuple[LogEntry, DetectionResult]
        Insert log entry with auto-detection and side effects.
        
        Args:
        - payload: raw input dict
        - force_log_type: skip detection and use this type
        - validate_input: validate/coerce payload before processing
        
        Returns: (log_entry, detection_result)
        Raises: ValidationError, ServiceError
        
        Side effects by log_type:
        - PRODUCT_UPDATE: create/update Product record
        - SALES: decrement on_hand, record movement
        - PURCHASE: increment on_hand, record movement
        - ADJUSTMENT: apply qty_delta, record movement
        - EXPENSE: no inventory impact
```

---

## `core.queries`

**Dashboard query helpers.**

### Classes

```python
class DashboardQueries:
    def __init__(session: Session)
        Initialize with database session.
    
    def get_kpis() -> Dict[str, Any]
        Return KPI dict:
        {
            "total_products": int,
            "total_units_on_hand": int,
            "inventory_value": float,
            "total_logs": int
        }
    
    def get_all_products(limit: int = None) -> List[Dict[str, Any]]
        Return all products as dicts:
        {
            "sku": str,
            "barcode": str,
            "name": str,
            "unit_cost": float,
            "unit_price": float,
            "on_hand": int,
            "updated_at": str
        }
    
    def get_low_stock_products(threshold: int = 10) -> List[Dict[str, Any]]
        Return products with on_hand <= threshold:
        {
            "sku": str,
            "name": str,
            "on_hand": int,
            "unit_price": float
        }
    
    def get_recent_logs(limit: int = 20) -> List[Dict[str, Any]]
        Return recent log entries:
        {
            "id": int,
            "created_at": str,
            "log_type": str,
            "ref_no": str,
            "counterparty": str,
            "notes": str
        }
    
    def get_sales_summary(limit: int = 30) -> List[Dict[str, Any]]
        Return recent sales:
        {
            "id": int,
            "created_at": str,
            "sku": str,
            "qty": int,
            "amount": float,
            "customer": str
        }
    
    def get_movement_history(sku: str, limit: int = 50) -> List[Dict[str, Any]]
        Return inventory movements for SKU:
        {
            "id": int,
            "created_at": str,
            "qty_delta": int,
            "unit_cost": float,
            "unit_price": float,
            "source_log_id": int
        }
```

---

## `app.py`

**Typer CLI interface.**

### Commands

```bash
python app.py init
    Initialize database tables.

python app.py add [--force-type TYPE]
    Add log entry interactively.
    Walks through:
    1. Common fields (ref_no, date)
    2. Product fields (SKU, qty, name)
    3. Pricing (unit cost, price, amount)
    4. Party (customer, vendor)
    5. Additional (category, reason, etc.)
    
    Options:
    --force-type TYPE : Skip detection, use this type

python app.py show-kpis
    Display KPI metrics.

python app.py show-products
    Display all products.

python app.py show-recent
    Display last 20 logs.
```

### CLI Modules

- `console` — Rich console for pretty output
- `typer.Typer` — CLI framework
- `typer.prompt()` — Interactive input

---

## `dashboard.py`

**Streamlit web dashboard.**

### Pages

**Main:** 4 tabs

1. **Products**
   - Full product table with SKU, name, on_hand, pricing, total value
   - Sortable/filterable

2. **Low Stock**
   - Threshold slider
   - Products below threshold
   - Red-gradient bar chart

3. **Recent Logs**
   - Log type filter (multi-select)
   - Date range picker
   - Last N logs table

4. **Sales Analysis**
   - KPI cards (count, revenue, average)
   - Daily sales line chart
   - Recent sales detail table

### Key Functions

```python
init_session_state()
    Initialize Streamlit session state (DB init).

get_queries() -> DashboardQueries
    Get query helper instance.
```

---

## Testing (`tests/test_core.py`)

### Test Classes

**TestDetection** (5 tests)
```python
test_detect_product_update()
test_detect_sales()
test_detect_purchase()
test_detect_adjustment()
test_detect_expense()
```

**TestValidation** (5 tests)
```python
test_validate_ints()
test_validate_floats()
test_validate_date()
test_validate_strips_strings()
test_validate_invalid_int()
```

**TestServices** (4 tests)
```python
test_insert_log_detects_type()
test_insert_sales_updates_inventory()
test_insert_purchase_updates_inventory()
test_insert_product_update()
```

### Fixtures

```python
@pytest.fixture
def test_db()
    In-memory SQLite test database.
```

### Run Tests

```bash
pytest tests/ -v                # Run all tests
pytest tests/test_core.py::TestDetection -v  # Run one class
pytest tests/test_core.py::TestDetection::test_detect_sales -v  # Run one test
```

---

## Common Imports

```python
# For services
from core.db import init_db, get_session
from core.services import LogService, ServiceError
from core.validate import ValidationError

# For queries/dashboard
from core.queries import DashboardQueries

# For config
from core.config import get_config

# For detection
from core.detect import get_detection_engine

# For models
from core.models import LogEntry, Product, ProductMovement
```

---

## Example: Add a Log Entry Programmatically

```python
from core.db import init_db, get_session
from core.services import LogService

# Initialize
init_db()

# Create session
session = get_session()
service = LogService(session)

# Insert log
payload = {
    "sku": "WIDGET-001",
    "qty": 10,
    "unit_price": 19.99,
    "amount": 199.90,
    "customer": "Acme Corp"
}

log, detection = service.insert_log(payload)

print(f"Log ID: {log.id}")
print(f"Type: {detection.log_type}")
print(f"Confidence: {detection.confidence}")

session.close()
```

---

## Example: Query Dashboard Data

```python
from core.db import get_session
from core.queries import DashboardQueries

session = get_session()
queries = DashboardQueries(session)

# KPIs
kpis = queries.get_kpis()
print(f"Products: {kpis['total_products']}")
print(f"Value: ${kpis['inventory_value']}")

# Low stock
low = queries.get_low_stock_products(threshold=10)
for p in low:
    print(f"{p['sku']}: {p['on_hand']} units")

# Recent sales
sales = queries.get_sales_summary(limit=5)
for s in sales:
    print(f"{s['created_at']}: ${s['amount']}")

session.close()
```

---

## Environment Variables

```bash
ACCOUNTING_DB_PATH
    Path to SQLite database file.
    Default: accounting.db (in current directory)
    
    Example:
    $env:ACCOUNTING_DB_PATH = "C:\data\accounting.db"
```

---

**Last Updated:** January 29, 2026
