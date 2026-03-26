"""
Inventory integrity scan for POS operations.

Checks:
- Unknown SKUs used in Sales/Stock
- Current availability per SKU (Stock in - Sales out)
- Low stock (<=2) and critical stock (<=0)

Read-only report script.
"""

import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "db" / "FinancialDatabase.db"


def main():
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()

        cursor.execute("SELECT sku FROM Products")
        product_skus = {row[0] for row in cursor.fetchall() if row[0]}

        cursor.execute("SELECT DISTINCT product_sku FROM Sales WHERE product_sku IS NOT NULL")
        sales_skus = {row[0] for row in cursor.fetchall() if row[0]}

        cursor.execute("SELECT DISTINCT product_sku FROM Stock WHERE product_sku IS NOT NULL")
        stock_skus = {row[0] for row in cursor.fetchall() if row[0]}

        unknown_in_sales = sorted(sales_skus - product_skus)
        unknown_in_stock = sorted(stock_skus - product_skus)

        cursor.execute(
            """
            SELECT product_sku, COALESCE(SUM(unit_in), 0)
            FROM Stock
            WHERE product_sku IS NOT NULL
            GROUP BY product_sku
            """
        )
        stock_in = {sku: qty or 0 for sku, qty in cursor.fetchall()}

        cursor.execute(
            """
            SELECT product_sku, COALESCE(SUM(units_sold), 0)
            FROM Sales
            WHERE product_sku IS NOT NULL
            GROUP BY product_sku
            """
        )
        sold = {sku: qty or 0 for sku, qty in cursor.fetchall()}

        all_skus = sorted(set(stock_in.keys()) | set(sold.keys()) | set(product_skus))
        availability = []
        for sku in all_skus:
            available = (stock_in.get(sku, 0) or 0) - (sold.get(sku, 0) or 0)
            availability.append((sku, available))

        low_stock = [(sku, available) for sku, available in availability if 1 <= available <= 2]
        critical_stock = [(sku, available) for sku, available in availability if available <= 0]

        print("Inventory Integrity Report")
        print("=" * 30)
        print(f"Products in catalog: {len(product_skus)}")
        print(f"SKUs in Sales: {len(sales_skus)}")
        print(f"SKUs in Stock: {len(stock_skus)}")
        print()

        print(f"Unknown SKUs in Sales: {len(unknown_in_sales)}")
        for sku in unknown_in_sales:
            print(f"  - {sku}")

        print(f"Unknown SKUs in Stock: {len(unknown_in_stock)}")
        for sku in unknown_in_stock:
            print(f"  - {sku}")

        print()
        print(f"Low stock (<=2 and >0): {len(low_stock)}")
        for sku, available in low_stock:
            print(f"  - {sku}: {available}")

        print(f"Critical stock (<=0): {len(critical_stock)}")
        for sku, available in critical_stock:
            print(f"  - {sku}: {available}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
