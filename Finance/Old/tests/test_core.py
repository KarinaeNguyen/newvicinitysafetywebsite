"""Tests for detection and services logic."""

import pytest
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.models import Base, LogEntry, Product
from core.detect import DetectionEngine
from core.validate import validate_payload, ValidationError
from core.services import LogService
from core.config import get_config


# Test database setup
@pytest.fixture
def test_db():
    """Create in-memory test database."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


# ============================================================================
# Detection Tests
# ============================================================================

class TestDetection:
    """Test log type detection."""

    def test_detect_product_update(self):
        """PRODUCT_UPDATE: sku + price."""
        detector = DetectionEngine()
        
        payload = {
            "sku": "WIDGET-001",
            "unit_price": 19.99,
            "barcode": "123456789"
        }
        
        result = detector.detect(payload)
        
        assert result.log_type == "PRODUCT_UPDATE"
        assert result.confidence in ["high", "medium"]

    def test_detect_sales(self):
        """SALES: sku + qty + unit_price + customer."""
        detector = DetectionEngine()
        
        payload = {
            "sku": "WIDGET-001",
            "qty": 5,
            "unit_price": 19.99,
            "amount": 99.95,
            "customer": "Acme Corp",
            "ref_no": "INV-001"
        }
        
        result = detector.detect(payload)
        
        assert result.log_type == "SALES"
        assert result.confidence == "high"

    def test_detect_purchase(self):
        """PURCHASE: sku + qty + unit_cost + vendor."""
        detector = DetectionEngine()
        
        payload = {
            "sku": "WIDGET-001",
            "qty": 100,
            "unit_cost": 10.00,
            "vendor": "Supplier Inc",
            "ref_no": "PO-042"
        }
        
        result = detector.detect(payload)
        
        assert result.log_type == "PURCHASE"
        assert result.confidence in ["high", "medium"]

    def test_detect_adjustment(self):
        """ADJUSTMENT: sku + qty_delta."""
        detector = DetectionEngine()
        
        payload = {
            "sku": "WIDGET-001",
            "qty_delta": -3,
            "reason": "Damaged"
        }
        
        result = detector.detect(payload)
        
        assert result.log_type == "ADJUSTMENT"

    def test_detect_expense(self):
        """EXPENSE: amount + vendor (no sku)."""
        detector = DetectionEngine()
        
        payload = {
            "amount": 250.00,
            "vendor": "Rent Company",
            "category": "Rent"
        }
        
        result = detector.detect(payload)
        
        assert result.log_type == "EXPENSE"


# ============================================================================
# Validation Tests
# ============================================================================

class TestValidation:
    """Test input validation and coercion."""

    def test_validate_ints(self):
        """Integer fields coerced correctly."""
        payload = {
            "qty": "10",
            "qty_delta": 5,
            "unit_count": "100"
        }
        
        coerced = validate_payload(payload)
        
        assert coerced["qty"] == 10
        assert coerced["qty_delta"] == 5
        assert coerced["unit_count"] == 100

    def test_validate_floats(self):
        """Float fields coerced correctly."""
        payload = {
            "unit_cost": "10.50",
            "unit_price": 19.99,
            "amount": "100"
        }
        
        coerced = validate_payload(payload)
        
        assert coerced["unit_cost"] == 10.50
        assert coerced["unit_price"] == 19.99
        assert coerced["amount"] == 100.0

    def test_validate_date(self):
        """Dates parsed to ISO8601."""
        payload = {
            "date": "2025-12-25"
        }
        
        coerced = validate_payload(payload)
        
        assert coerced["date"] == "2025-12-25T00:00:00"

    def test_validate_strips_strings(self):
        """Strings trimmed; empty -> None."""
        payload = {
            "sku": "  WIDGET-001  ",
            "barcode": "",
            "notes": "  Test note  "
        }
        
        coerced = validate_payload(payload)
        
        assert coerced["sku"] == "WIDGET-001"
        assert coerced["barcode"] is None
        assert coerced["notes"] == "Test note"

    def test_validate_invalid_int(self):
        """Invalid int raises ValidationError."""
        payload = {
            "qty": "abc"
        }
        
        with pytest.raises(ValidationError):
            validate_payload(payload)


# ============================================================================
# Service Tests
# ============================================================================

class TestServices:
    """Test business logic."""

    def test_insert_log_detects_type(self, test_db):
        """Log insertion auto-detects type."""
        service = LogService(test_db)
        
        payload = {
            "sku": "SKU-001",
            "qty": 10,
            "unit_price": 15.00,
            "amount": 150.00,
            "customer": "Test Co"
        }
        
        log, detection = service.insert_log(payload)
        
        assert log.log_type == "SALES"
        assert detection.log_type == "SALES"

    def test_insert_sales_updates_inventory(self, test_db):
        """SALES log decrements product on_hand."""
        service = LogService(test_db)
        
        # Insert product first
        product = Product(sku="SKU-001", on_hand=100)
        test_db.add(product)
        test_db.commit()
        
        payload = {
            "sku": "SKU-001",
            "qty": 10,
            "unit_price": 15.00,
            "amount": 150.00,
            "customer": "Test Co"
        }
        
        service.insert_log(payload)
        
        # Check product updated
        product = test_db.query(Product).filter_by(sku="SKU-001").first()
        assert product.on_hand == 90

    def test_insert_purchase_updates_inventory(self, test_db):
        """PURCHASE log increments product on_hand."""
        service = LogService(test_db)
        
        # Insert product first
        product = Product(sku="SKU-001", on_hand=50)
        test_db.add(product)
        test_db.commit()
        
        payload = {
            "sku": "SKU-001",
            "qty": 30,
            "unit_cost": 10.00,
            "vendor": "Supplier"
        }
        
        service.insert_log(payload)
        
        # Check product updated
        product = test_db.query(Product).filter_by(sku="SKU-001").first()
        assert product.on_hand == 80

    def test_insert_product_update(self, test_db):
        """PRODUCT_UPDATE creates/updates product master."""
        service = LogService(test_db)
        
        payload = {
            "sku": "SKU-NEW",
            "name": "New Widget",
            "unit_price": 25.00,
            "unit_cost": 12.00,
            "barcode": "987654321"
        }
        
        service.insert_log(payload)
        
        product = test_db.query(Product).filter_by(sku="SKU-NEW").first()
        assert product is not None
        assert product.name == "New Widget"
        assert product.unit_price == 25.00


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
