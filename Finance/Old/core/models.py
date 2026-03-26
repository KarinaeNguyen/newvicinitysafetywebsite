"""SQLAlchemy models for the accounting system."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class LogEntry(Base):
    """Source of truth: all log entries regardless of type."""
    __tablename__ = "log_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(String, default=lambda: datetime.utcnow().isoformat(), nullable=False)
    log_type = Column(String, nullable=False)  # auto-detected: PRODUCT_UPDATE, SALES, PURCHASE, etc.
    ref_no = Column(String, nullable=True)
    counterparty = Column(String, nullable=True)  # customer/vendor
    notes = Column(Text, nullable=True)
    payload_json = Column(Text, nullable=False)  # full payload as JSON string

    # Relationships
    product_movements = relationship("ProductMovement", back_populates="log_entry")


class Product(Base):
    """Normalized product inventory for dashboard & fast lookups."""
    __tablename__ = "products"

    sku = Column(String, primary_key=True)
    barcode = Column(String, unique=True, nullable=True)
    name = Column(String, nullable=True)
    unit_cost = Column(Float, nullable=True)
    unit_price = Column(Float, nullable=True)
    on_hand = Column(Integer, default=0, nullable=False)
    updated_at = Column(String, default=lambda: datetime.utcnow().isoformat(), nullable=False)


class ProductMovement(Base):
    """Audit trail: every inventory change tied to source log."""
    __tablename__ = "product_movements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(String, default=lambda: datetime.utcnow().isoformat(), nullable=False)
    sku = Column(String, nullable=False)
    qty_delta = Column(Integer, nullable=False)  # +in / -out / 0
    unit_cost = Column(Float, nullable=True)  # snapshot at time of movement
    unit_price = Column(Float, nullable=True)  # snapshot at time of movement
    source_log_id = Column(Integer, ForeignKey("log_entries.id"), nullable=False)

    # Relationships
    log_entry = relationship("LogEntry", back_populates="product_movements")
