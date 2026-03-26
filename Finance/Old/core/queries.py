"""Query helpers and KPI computations for dashboard."""

from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from core.models import LogEntry, Product, ProductMovement


class DashboardQueries:
    """Read-only queries for dashboard widgets."""

    def __init__(self, session: Session):
        self.session = session

    def get_kpis(self) -> Dict[str, Any]:
        """Return KPI summary: total products, total inventory value, etc."""
        total_products = self.session.query(func.count(Product.sku)).scalar() or 0
        total_units = self.session.query(func.sum(Product.on_hand)).scalar() or 0
        
        total_value = self.session.query(
            func.sum(Product.on_hand * Product.unit_price)
        ).scalar() or 0.0
        
        total_logs = self.session.query(func.count(LogEntry.id)).scalar() or 0
        
        return {
            "total_products": total_products,
            "total_units_on_hand": total_units,
            "inventory_value": round(total_value, 2),
            "total_logs": total_logs
        }

    def get_all_products(self, limit: int = None) -> List[Dict[str, Any]]:
        """Return all products as dicts."""
        query = self.session.query(Product).order_by(Product.sku)
        
        if limit:
            query = query.limit(limit)
        
        return [
            {
                "sku": p.sku,
                "barcode": p.barcode,
                "name": p.name,
                "unit_cost": p.unit_cost,
                "unit_price": p.unit_price,
                "on_hand": p.on_hand,
                "updated_at": p.updated_at
            }
            for p in query.all()
        ]

    def get_low_stock_products(self, threshold: int = 10) -> List[Dict[str, Any]]:
        """Return products below stock threshold."""
        products = self.session.query(Product).filter(
            Product.on_hand <= threshold
        ).order_by(Product.on_hand).all()
        
        return [
            {
                "sku": p.sku,
                "name": p.name,
                "on_hand": p.on_hand,
                "unit_price": p.unit_price
            }
            for p in products
        ]

    def get_recent_logs(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Return recent log entries."""
        logs = self.session.query(LogEntry).order_by(
            LogEntry.created_at.desc()
        ).limit(limit).all()
        
        return [
            {
                "id": log.id,
                "created_at": log.created_at,
                "log_type": log.log_type,
                "ref_no": log.ref_no,
                "counterparty": log.counterparty,
                "notes": log.notes
            }
            for log in logs
        ]

    def get_sales_summary(self, limit: int = 30) -> List[Dict[str, Any]]:
        """Return recent sales with amounts."""
        import json
        
        logs = self.session.query(LogEntry).filter_by(
            log_type="SALES"
        ).order_by(LogEntry.created_at.desc()).limit(limit).all()
        
        result = []
        for log in logs:
            try:
                payload = json.loads(log.payload_json)
                amount = payload.get("amount", 0)
            except:
                amount = 0
            
            result.append({
                "id": log.id,
                "created_at": log.created_at,
                "sku": payload.get("sku") if 'payload' in locals() else None,
                "qty": payload.get("qty") if 'payload' in locals() else None,
                "amount": amount,
                "customer": log.counterparty
            })
        
        return result

    def get_movement_history(self, sku: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Return inventory movements for a specific SKU."""
        movements = self.session.query(ProductMovement).filter_by(
            sku=sku
        ).order_by(ProductMovement.created_at.desc()).limit(limit).all()
        
        return [
            {
                "id": m.id,
                "created_at": m.created_at,
                "qty_delta": m.qty_delta,
                "unit_cost": m.unit_cost,
                "unit_price": m.unit_price,
                "source_log_id": m.source_log_id
            }
            for m in movements
        ]
