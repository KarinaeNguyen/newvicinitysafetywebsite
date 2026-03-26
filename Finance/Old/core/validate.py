"""Input validation and type coercion."""

from datetime import datetime
from typing import Any, Dict, Tuple


class ValidationError(Exception):
    """Raised when validation fails."""
    pass


def coerce_date(value: Any) -> str:
    """Parse date string to ISO8601 format.
    
    Accepts: YYYY-MM-DD, datetime object, or None.
    Returns: ISO8601 string or None.
    """
    if value is None or value == "":
        return None
    
    if isinstance(value, datetime):
        return value.isoformat()
    
    if isinstance(value, str):
        try:
            dt = datetime.strptime(value.strip(), "%Y-%m-%d")
            return dt.isoformat()
        except ValueError as e:
            raise ValidationError(f"Invalid date format: {value}. Expected YYYY-MM-DD. {e}")
    
    raise ValidationError(f"Cannot parse date from {type(value).__name__}: {value}")


def coerce_int(value: Any, field_name: str) -> int:
    """Coerce to integer.
    
    Accepts: int, float (if whole), string representation, or None.
    """
    if value is None or value == "":
        return None
    
    if isinstance(value, int):
        return value
    
    if isinstance(value, float):
        if value.is_integer():
            return int(value)
        raise ValidationError(f"{field_name}: Cannot coerce {value} (float) to int")
    
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError as e:
            raise ValidationError(f"{field_name}: Cannot parse int from '{value}'. {e}")
    
    raise ValidationError(f"{field_name}: Unsupported type {type(value).__name__}")


def coerce_float(value: Any, field_name: str) -> float:
    """Coerce to float.
    
    Accepts: int, float, string representation, or None.
    """
    if value is None or value == "":
        return None
    
    if isinstance(value, (int, float)):
        return float(value)
    
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError as e:
            raise ValidationError(f"{field_name}: Cannot parse float from '{value}'. {e}")
    
    raise ValidationError(f"{field_name}: Unsupported type {type(value).__name__}")


def coerce_string(value: Any) -> str:
    """Coerce to string.
    
    Strips whitespace; treats empty string as None.
    """
    if value is None:
        return None
    
    s = str(value).strip()
    return s if s else None


def validate_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and coerce all payload fields.
    
    Returns coerced payload.
    Raises ValidationError if any field is invalid.
    """
    coerced = {}
    
    # Integer fields
    int_fields = ["qty", "qty_delta", "unit_count"]
    for field in int_fields:
        if field in payload:
            coerced[field] = coerce_int(payload[field], field)
    
    # Float fields
    float_fields = ["unit_cost", "unit_price", "amount", "discount", "tax", "shipping"]
    for field in float_fields:
        if field in payload:
            coerced[field] = coerce_float(payload[field], field)
    
    # Date fields
    date_fields = ["date", "created_at"]
    for field in date_fields:
        if field in payload:
            coerced[field] = coerce_date(payload[field])
    
    # String fields (strip & normalize)
    string_fields = ["sku", "barcode", "name", "customer", "vendor", "category", "ref_no", "notes", "reason", "payment_method"]
    for field in string_fields:
        if field in payload:
            coerced[field] = coerce_string(payload[field])
    
    # Copy any other fields as-is
    for key, value in payload.items():
        if key not in coerced:
            coerced[key] = value
    
    return coerced


def check_required_fields(payload: Dict[str, Any], required_fields: list) -> Tuple[bool, list]:
    """Check if all required fields are present and non-empty.
    
    Returns: (all_present: bool, missing_fields: list)
    """
    missing = []
    for field in required_fields:
        value = payload.get(field)
        if value is None or value == "":
            missing.append(field)
    
    return len(missing) == 0, missing
