"""Import historical data from Google Sheets exports."""

import csv
import re
from datetime import datetime
from typing import Dict, Any, List
from core.db import init_db, get_session
from core.services import LogService, ServiceError
from core.validate import ValidationError


def parse_vietnamese_currency(value: str) -> float:
    """Parse Vietnamese currency format: '810,000 ₫' -> 810000.0"""
    if not value or value == "0 ₫":
        return 0.0
    # Remove ₫, spaces, commas
    cleaned = value.replace("₫", "").replace(",", "").replace(" ", "").strip()
    if not cleaned:
        return 0.0
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def parse_date(date_str: str) -> str:
    """Parse date from M/D/YYYY or MM/DD/YYYY to YYYY-MM-DD."""
    if not date_str:
        return None
    try:
        dt = datetime.strptime(date_str, "%m/%d/%Y")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        try:
            dt = datetime.strptime(date_str, "%m/%d/%Y")
            return dt.strftime("%Y-%m-%d")
        except:
            return None


def import_stock_log(file_path: str, service: LogService) -> int:
    """Import stock/purchase data (inventory in).
    
    Columns: Date, Product SKU, Unit Cost, Unit In, Total, Note
    """
    count = 0
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Skip summary rows
            if not row.get("Product SKU") or row.get("Product SKU") == "Total":
                continue
            
            date = parse_date(row.get("Date", ""))
            sku = row.get("Product SKU", "").strip()
            unit_cost = parse_vietnamese_currency(row.get("Unit Cost", "0 ₫"))
            qty = row.get("Unit In", "0").replace(",", "").strip()
            note = row.get("Note", "")
            
            if not sku or not qty or qty == "0":
                continue
            
            try:
                qty = int(qty)
            except ValueError:
                continue
            
            # Create PURCHASE log
            payload = {
                "date": date,
                "sku": sku,
                "qty": qty,
                "unit_cost": unit_cost / 1.25,  # Remove VAT (GTGT 8%) to get base cost
                "vendor": "Import from historical data",
                "notes": note if note else f"Historical stock in"
            }
            
            try:
                service.insert_log(payload, force_log_type="PURCHASE")
                count += 1
            except (ValidationError, ServiceError) as e:
                print(f"⚠️  Skipped stock row: {e}")
    
    return count


def import_sales_log(file_path: str, service: LogService) -> int:
    """Import sales transactions.
    
    Columns: Sale Date, Order ID, Channel, Product SKU, Units Sold, Unit Price, 
             Gross Sales, GTGT, Service Fee, Shipping Fees, Note
    """
    count = 0
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            date = parse_date(row.get("Sale Date", ""))
            order_id = row.get("Order ID", "").strip()
            channel = row.get("Channel", "").strip()
            sku = row.get("Product SKU", "").strip()
            qty = row.get("Units Sold", "0").replace(",", "").strip()
            unit_price = parse_vietnamese_currency(row.get("Unit Price", "0 ₫"))
            gross_sales = parse_vietnamese_currency(row.get("Gross Sales", "0 ₫"))
            gtgt = parse_vietnamese_currency(row.get("GTGT", "0 ₫"))
            note = row.get("Note", "")
            
            if not sku or not qty or qty == "0":
                continue
            
            try:
                qty = int(qty)
            except ValueError:
                continue
            
            # Calculate net amount (remove VAT)
            amount = gross_sales - gtgt if gtgt > 0 else gross_sales
            
            # Create SALES log
            payload = {
                "date": date,
                "sku": sku,
                "qty": qty,
                "unit_price": unit_price / 1.08,  # Remove VAT to get base price
                "amount": amount,
                "customer": channel,
                "ref_no": order_id,
                "notes": note if note else f"Historical sale via {channel}"
            }
            
            try:
                service.insert_log(payload, force_log_type="SALES")
                count += 1
            except (ValidationError, ServiceError) as e:
                print(f"⚠️  Skipped sales row: {e}")
    
    return count


def import_cost_log(file_path: str, service: LogService) -> int:
    """Import expense/cost data.
    
    Columns: Date, Type, Cost Item, Price, GTGT, Note
    """
    count = 0
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Skip stocking costs (already imported via stock log)
            if row.get("Type", "") == "Stocking Cost":
                continue
            
            date = parse_date(row.get("Date", ""))
            cost_type = row.get("Type", "").strip()
            cost_item = row.get("Cost Item", "").strip()
            price = parse_vietnamese_currency(row.get("Price", "0 ₫"))
            gtgt = parse_vietnamese_currency(row.get("GTGT", "0 ₫"))
            note = row.get("Note", "")
            
            if not cost_item or price == 0:
                continue
            
            # Calculate net amount
            amount = price - gtgt if gtgt > 0 else price
            
            # Create EXPENSE log
            payload = {
                "date": date,
                "amount": amount,
                "category": cost_type,
                "vendor": cost_item,
                "notes": note if note else f"Historical {cost_type}"
            }
            
            try:
                service.insert_log(payload, force_log_type="EXPENSE")
                count += 1
            except (ValidationError, ServiceError) as e:
                print(f"⚠️  Skipped cost row: {e}")
    
    return count


def run_import(import_folder: str = "import_data"):
    """Run full import from all CSV files."""
    print("🚀 Starting data import...\n")
    
    init_db()
    session = get_session()
    service = LogService(session)
    
    # Import in order: Stock → Sales → Costs
    print("📦 Importing stock/purchase data...")
    stock_count = import_stock_log(
        f"{import_folder}/Sales Management-Mastersheet - Stock Log.csv",
        service
    )
    print(f"   ✓ Imported {stock_count} stock entries\n")
    
    print("💰 Importing sales data...")
    sales_count = import_sales_log(
        f"{import_folder}/Sales Management-Mastersheet - Sales Log.csv",
        service
    )
    print(f"   ✓ Imported {sales_count} sales entries\n")
    
    print("💸 Importing cost/expense data...")
    cost_count = import_cost_log(
        f"{import_folder}/Sales Management-Mastersheet - Cost Log.csv",
        service
    )
    print(f"   ✓ Imported {cost_count} expense entries\n")
    
    session.close()
    
    print("=" * 50)
    print(f"✅ Import complete!")
    print(f"   Total logs: {stock_count + sales_count + cost_count}")
    print(f"   - Purchases: {stock_count}")
    print(f"   - Sales: {sales_count}")
    print(f"   - Expenses: {cost_count}")
    print("=" * 50)


if __name__ == "__main__":
    run_import()
