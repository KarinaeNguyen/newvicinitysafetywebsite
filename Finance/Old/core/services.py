"""Business logic: log persistence, product updates, and inventory tracking."""

import json
from datetime import datetime
from typing import Dict, Any, Tuple

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from core.models import LogEntry, Product, ProductMovement
from core.validate import validate_payload, ValidationError
from core.detect import get_detection_engine, DetectionResult
from core.config import get_config


class ServiceError(Exception):
    """Raised when a business logic error occurs."""
    pass


class LogService:
    """Service for inserting and managing log entries."""

    def __init__(self, session: Session):
        self.session = session
        self.config = get_config()
        self.detector = get_detection_engine()

    def insert_log(
        self, 
        payload: Dict[str, Any], 
        force_log_type: str = None,
        validate_input: bool = True
    ) -> Tuple[LogEntry, DetectionResult]:
        """Insert a log entry with auto-detection and side effects.
        
        Args:
            payload: raw input dict
            force_log_type: if provided, skip detection and use this type
            validate_input: if True, validate/coerce payload before processing
        
        Returns: (log_entry: LogEntry, detection_result: DetectionResult)
        Raises: ValidationError, ServiceError
        """
        # Validate & coerce
        if validate_input:
            payload = validate_payload(payload)
        
        # Detect or use forced type
        if force_log_type:
            detection = DetectionResult(
                log_type=force_log_type,
                score=-1,
                confidence="forced",
                candidate_scores={},
                debug_breakdown={}
            )
        else:
            detection = self.detector.detect(payload)
        
        # Create log entry
        log_entry = LogEntry(
            log_type=detection.log_type,
            ref_no=payload.get("ref_no"),
            counterparty=payload.get("customer") or payload.get("vendor"),
            notes=payload.get("notes"),
            payload_json=json.dumps(payload, default=str)
        )
        
        self.session.add(log_entry)
        self.session.flush()  # Get the ID
        
        # Process side effects based on log type
        self._process_log_side_effects(log_entry, payload, detection.log_type)
        
        self.session.commit()
        return log_entry, detection

    def _process_log_side_effects(
        self, 
        log_entry: LogEntry, 
        payload: Dict[str, Any], 
        log_type: str
    ):
        """Apply side effects: product updates, inventory movements, etc."""
        
        if log_type == "PRODUCT_UPDATE":
            self._handle_product_update(log_entry, payload)
        
        elif log_type == "SALES":
            self._handle_sales(log_entry, payload)
        
        elif log_type == "PURCHASE":
            self._handle_purchase(log_entry, payload)
        
        elif log_type == "ADJUSTMENT":
            self._handle_adjustment(log_entry, payload)
        
        # EXPENSE has no inventory side effects

    def _handle_product_update(self, log_entry: LogEntry, payload: Dict[str, Any]):
        """Update product master data (SKU, pricing, barcode)."""
        sku = payload.get("sku")
        if not sku:
            raise ServiceError("PRODUCT_UPDATE requires SKU")
        
        product = self.session.query(Product).filter_by(sku=sku).first()
        
        if not product:
            product = Product(sku=sku)
            self.session.add(product)
        
        # Update fields
        if "barcode" in payload and payload["barcode"]:
            product.barcode = payload["barcode"]
        if "name" in payload and payload["name"]:
            product.name = payload["name"]
        if "unit_cost" in payload and payload["unit_cost"] is not None:
            product.unit_cost = payload["unit_cost"]
        if "unit_price" in payload and payload["unit_price"] is not None:
            product.unit_price = payload["unit_price"]
        
        product.updated_at = datetime.utcnow().isoformat()

    def _handle_sales(self, log_entry: LogEntry, payload: Dict[str, Any]):
        """Record a sale: decrement inventory and update selling price."""
        sku = payload.get("sku")
        qty = payload.get("qty")
        unit_price = payload.get("unit_price")
        
        if not sku or qty is None:
            raise ServiceError("SALES requires SKU and qty")
        
        if qty <= 0:
            raise ServiceError("SALES qty must be > 0")
        
        # Ensure product exists
        product = self._ensure_product(sku, payload)
        
        # Update unit_price if provided (latest selling price)
        if unit_price is not None and unit_price > 0:
            product.unit_price = unit_price
        
        # Decrement on_hand
        product.on_hand -= qty
        product.updated_at = datetime.utcnow().isoformat()
        
        # Record movement
        movement = ProductMovement(
            sku=sku,
            qty_delta=-qty,
            unit_price=unit_price,
            source_log_id=log_entry.id
        )
        self.session.add(movement)

    def _handle_purchase(self, log_entry: LogEntry, payload: Dict[str, Any]):
        """Record a purchase: increment inventory and update weighted average cost."""
        sku = payload.get("sku")
        qty = payload.get("qty")
        unit_cost = payload.get("unit_cost")
        
        if not sku or qty is None:
            raise ServiceError("PURCHASE requires SKU and qty")
        
        if not unit_cost or unit_cost <= 0:
            raise ServiceError("PURCHASE requires unit_cost (must be > 0)")
        
        if qty <= 0:
            raise ServiceError("PURCHASE qty must be > 0")
        
        # Ensure product exists
        product = self._ensure_product(sku, payload)
        
        # Calculate weighted average cost
        old_qty = product.on_hand
        old_cost = product.unit_cost or 0
        new_qty = old_qty + qty
        
        # Weighted average: (old_qty * old_cost + qty * unit_cost) / new_qty
        if new_qty > 0:
            product.unit_cost = ((old_qty * old_cost) + (qty * unit_cost)) / new_qty
        
        # Increment on_hand
        product.on_hand += qty
        product.updated_at = datetime.utcnow().isoformat()
        
        # Record movement with actual purchase cost
        movement = ProductMovement(
            sku=sku,
            qty_delta=qty,
            unit_cost=unit_cost,  # Store actual purchase cost for this transaction
            source_log_id=log_entry.id
        )
        self.session.add(movement)

    def _handle_adjustment(self, log_entry: LogEntry, payload: Dict[str, Any]):
        """Record inventory adjustment (loss, damage, count variance)."""
        sku = payload.get("sku")
        qty_delta = payload.get("qty_delta")
        
        if not sku or qty_delta is None:
            raise ServiceError("ADJUSTMENT requires SKU and qty_delta")
        
        # Ensure product exists (even if adjustment is negative)
        product = self._ensure_product(sku, payload)
        
        # Apply delta
        product.on_hand += qty_delta
        product.updated_at = datetime.utcnow().isoformat()
        
        # Record movement
        movement = ProductMovement(
            sku=sku,
            qty_delta=qty_delta,
            source_log_id=log_entry.id
        )
        self.session.add(movement)

    def _ensure_product(self, sku: str, payload: Dict[str, Any]) -> Product:
        """Get or create a product, populating from payload if new."""
        product = self.session.query(Product).filter_by(sku=sku).first()
        
        if not product:
            product = Product(
                sku=sku,
                barcode=payload.get("barcode"),
                name=payload.get("name"),
                unit_cost=payload.get("unit_cost"),
                unit_price=payload.get("unit_price"),
                on_hand=0
            )
            self.session.add(product)
        
        return product
