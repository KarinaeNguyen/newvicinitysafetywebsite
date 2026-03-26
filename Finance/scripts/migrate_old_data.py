"""
Migrate legacy CSV data from Old/import_data into FinancialDatabase.db.
Default is dry-run. Use --apply to write changes.
"""

import argparse
import csv
import re
import sqlite3
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
OLD_DIR = BASE_DIR / "Old" / "import_data"
DB_PATH = BASE_DIR / "db" / "FinancialDatabase.db"

FILES = {
    "sales_log": OLD_DIR / "Sales Management-Mastersheet - Sales Log.csv",
    "cost_log": OLD_DIR / "Sales Management-Mastersheet - Cost Log.csv",
    "cash_in": OLD_DIR / "Sales Management-Mastersheet - Cash In.csv",
    "stock_log": OLD_DIR / "Sales Management-Mastersheet - Stock Log.csv",
    "timeline": OLD_DIR / "Sales Management-Mastersheet - Timeline.csv",
    "sales_total": OLD_DIR / "Sales Management-Mastersheet - Sales Total.csv",
    "sales_out": OLD_DIR / "Sales Management-Mastersheet - Sales Out.csv",
    "stock_balance": OLD_DIR / "Sales Management-Mastersheet - Stock Balance.csv",
    "cash_flow": OLD_DIR / "Sales Management-Mastersheet - Cash Flow (2).csv",
}

DATE_FORMATS = ["%m/%d/%Y", "%d/%m/%Y", "%m/%d/%y", "%d/%m/%y"]

MONTH_MAP = {
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
    "Oct": 10,
    "Nov": 11,
    "Dec": 12,
}


def parse_date(value):
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def parse_money(value):
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    cleaned = re.sub(r"[^0-9.\-]", "", text)
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_int(value):
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    cleaned = re.sub(r"[^0-9\-]", "", text)
    if not cleaned:
        return None
    try:
        return int(cleaned)
    except ValueError:
        return None


def read_csv_rows(path):
    if not Path(path).exists():
        return []
    with open(path, "r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_monthly_matrix(path):
    if not Path(path).exists():
        return [], []
    with open(path, "r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.reader(handle))
    if len(rows) < 3:
        return [], []
    years_row = rows[0]
    months_row = rows[1]

    columns = []
    for idx in range(1, len(months_row)):
        year_text = years_row[idx].strip() if idx < len(years_row) else ""
        month_text = months_row[idx].strip() if idx < len(months_row) else ""
        if not year_text or month_text not in MONTH_MAP:
            continue
        try:
            year_val = int(year_text)
        except ValueError:
            continue
        columns.append((idx, year_val, MONTH_MAP[month_text]))

    return columns, rows[2:]


def build_note(*parts):
    cleaned = [p for p in parts if p]
    return "; ".join(cleaned) if cleaned else None


def log_exists(cursor, log_date, log_type, product_sku, details):
        cursor.execute(
                """
                SELECT 1 FROM Logs
                WHERE log_date = ? AND log_type = ?
                    AND (product_sku IS ? OR product_sku = ?)
                    AND details = ?
                LIMIT 1
                """,
                (log_date, log_type, product_sku, product_sku, details),
        )
        return cursor.fetchone() is not None


def ensure_product(cursor, sku, unit_cost=None):
    if not sku:
        return
    cursor.execute("SELECT sku, unit_cost FROM Products WHERE sku = ?", (sku,))
    row = cursor.fetchone()
    if row:
        if unit_cost is not None and row[1] is None:
            cursor.execute("UPDATE Products SET unit_cost = ? WHERE sku = ?", (unit_cost, sku))
        return
    cursor.execute(
        "INSERT INTO Products (sku, name, category, unit_cost) VALUES (?, ?, ?, ?)",
        (sku, None, None, unit_cost),
    )


def migrate(apply_changes=False):
    summary = {
        "sales": 0,
        "costs": 0,
        "stock": 0,
        "timeline": 0,
        "cash_in": 0,
        "products": 0,
        "sales_total_logs": 0,
        "sales_out_logs": 0,
        "stock_balance_logs": 0,
        "cash_flow_logs": 0,
    }

    sales_rows = read_csv_rows(FILES["sales_log"])
    cost_rows = read_csv_rows(FILES["cost_log"])
    cash_in_rows = read_csv_rows(FILES["cash_in"])
    stock_rows = read_csv_rows(FILES["stock_log"])
    timeline_rows = read_csv_rows(FILES["timeline"])
    sales_total_cols, sales_total_rows = read_monthly_matrix(FILES["sales_total"])
    sales_out_cols, sales_out_rows = read_monthly_matrix(FILES["sales_out"])
    stock_balance_cols, stock_balance_rows = read_monthly_matrix(FILES["stock_balance"])
    cash_flow_cols, cash_flow_rows = read_monthly_matrix(FILES["cash_flow"])

    if not apply_changes:
        summary["sales"] = len(sales_rows)
        summary["costs"] = len(cost_rows)
        summary["cash_in"] = len(cash_in_rows)
        summary["stock"] = len(stock_rows)
        summary["timeline"] = len(timeline_rows)
        summary["sales_total_logs"] = sum(1 for _ in sales_total_rows)
        summary["sales_out_logs"] = sum(1 for _ in sales_out_rows)
        summary["stock_balance_logs"] = sum(1 for _ in stock_balance_rows)
        summary["cash_flow_logs"] = sum(1 for _ in cash_flow_rows)
        return summary

    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")

        # Sales
        for row in sales_rows:
            sale_date = parse_date(row.get("Sale Date"))
            order_id = row.get("Order ID")
            channel = row.get("Channel")
            sku = row.get("Product SKU")
            units_sold = parse_int(row.get("Units Sold"))
            unit_price = parse_money(row.get("Unit Price"))
            gross_sales = parse_money(row.get("Gross Sales"))
            service_fee = parse_money(row.get("Service Fee"))
            shipping_fee = parse_money(row.get("Shipping Fees"))
            gtgt = row.get("GTGT")
            note = build_note(row.get("Note"), f"GTGT={gtgt}" if gtgt else None)

            cursor.execute(
                """
                INSERT INTO Sales (sale_date, order_id, channel, product_sku, units_sold, unit_price, gross_sales, service_fee, shipping_fee, note)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (sale_date, order_id, channel, sku, units_sold, unit_price, gross_sales, service_fee, shipping_fee, note),
            )
            summary["sales"] += 1
            ensure_product(cursor, sku, unit_price)

        # Costs
        for row in cost_rows:
            cost_date = parse_date(row.get("Date"))
            cost_type = row.get("Type")
            item = row.get("Cost Item")
            price = parse_money(row.get("Price"))
            gtgt = row.get("GTGT")
            note = build_note(item, row.get("Note"), f"GTGT={gtgt}" if gtgt else None)

            cursor.execute(
                """
                INSERT INTO Costs (cost_type, cost_date, amount, note)
                VALUES (?, ?, ?, ?)
                """,
                (cost_type, cost_date, price, note),
            )
            summary["costs"] += 1

        # Cash In -> Timeline
        for row in cash_in_rows:
            event_date = parse_date(row.get("Date"))
            event_type = row.get("Type")
            item = row.get("Cost Item")
            price = parse_money(row.get("Price"))
            gtgt = row.get("GTGT")
            note = build_note(row.get("Note"), f"GTGT={gtgt}" if gtgt else None)
            event_name = build_note(event_type, item)

            cursor.execute(
                """
                INSERT INTO Timeline (event_date, event_name, cash_in, cash_out, balance, note)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (event_date, event_name, price, None, None, note),
            )
            summary["cash_in"] += 1

        # Stock
        for row in stock_rows:
            stock_date = parse_date(row.get("Date"))
            sku = row.get("Product SKU")
            unit_cost = parse_money(row.get("Unit Cost"))
            unit_in = parse_int(row.get("Unit In"))
            total = parse_money(row.get("Total"))
            note = build_note(row.get("Note"))

            cursor.execute(
                """
                INSERT INTO Stock (date, product_sku, unit_cost, unit_in, total, note)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (stock_date, sku, unit_cost, unit_in, total, note),
            )
            summary["stock"] += 1
            ensure_product(cursor, sku, unit_cost)

        # Timeline
        for row in timeline_rows:
            event_date = parse_date(row.get("Date"))
            event_name = row.get("Event name")
            cash_in = parse_money(row.get("Cash In"))
            cash_out = parse_money(row.get("Cash Out"))
            balance = parse_money(row.get("Balance"))
            note = build_note(row.get("Note"))

            cursor.execute(
                """
                INSERT INTO Timeline (event_date, event_name, cash_in, cash_out, balance, note)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (event_date, event_name, cash_in, cash_out, balance, note),
            )
            summary["timeline"] += 1

        # Sales Total (monthly aggregates)
        for row in sales_total_rows:
            if not row:
                continue
            sku = row[0].strip() if row[0] else None
            if not sku:
                continue
            for idx, year_val, month_val in sales_total_cols:
                if idx >= len(row):
                    continue
                value = parse_money(row[idx])
                if value is None or value == 0:
                    continue
                log_date = datetime(year_val, month_val, 1).date().isoformat()
                details = f"gross_sales={value}"
                if not log_exists(cursor, log_date, "sales_total", sku, details):
                    cursor.execute(
                        "INSERT INTO Logs (log_date, log_type, product_sku, details) VALUES (?, ?, ?, ?)",
                        (log_date, "sales_total", sku, details),
                    )
                    summary["sales_total_logs"] += 1

        # Sales Out (monthly units)
        for row in sales_out_rows:
            if not row:
                continue
            sku = row[0].strip() if row[0] else None
            if not sku:
                continue
            for idx, year_val, month_val in sales_out_cols:
                if idx >= len(row):
                    continue
                units = parse_int(row[idx])
                if units is None or units == 0:
                    continue
                log_date = datetime(year_val, month_val, 1).date().isoformat()
                details = f"units_out={units}"
                if not log_exists(cursor, log_date, "sales_out", sku, details):
                    cursor.execute(
                        "INSERT INTO Logs (log_date, log_type, product_sku, details) VALUES (?, ?, ?, ?)",
                        (log_date, "sales_out", sku, details),
                    )
                    summary["sales_out_logs"] += 1

        # Stock Balance (monthly ending balance)
        for row in stock_balance_rows:
            if not row:
                continue
            sku = row[0].strip() if row[0] else None
            if not sku:
                continue
            for idx, year_val, month_val in stock_balance_cols:
                if idx >= len(row):
                    continue
                balance = parse_int(row[idx])
                if balance is None or balance == 0:
                    continue
                log_date = datetime(year_val, month_val, 1).date().isoformat()
                details = f"stock_balance={balance}"
                if not log_exists(cursor, log_date, "stock_balance", sku, details):
                    cursor.execute(
                        "INSERT INTO Logs (log_date, log_type, product_sku, details) VALUES (?, ?, ?, ?)",
                        (log_date, "stock_balance", sku, details),
                    )
                    summary["stock_balance_logs"] += 1

        # Cash Flow (monthly total cost)
        for row in cash_flow_rows:
            if not row:
                continue
            label = row[0].strip() if row[0] else "Total"
            for idx, year_val, month_val in cash_flow_cols:
                if idx >= len(row):
                    continue
                amount = parse_money(row[idx])
                if amount is None or amount == 0:
                    continue
                log_date = datetime(year_val, month_val, 1).date().isoformat()
                details = f"{label}={amount}"
                if not log_exists(cursor, log_date, "cash_flow", None, details):
                    cursor.execute(
                        "INSERT INTO Logs (log_date, log_type, product_sku, details) VALUES (?, ?, ?, ?)",
                        (log_date, "cash_flow", None, details),
                    )
                    summary["cash_flow_logs"] += 1

        # Count products
        cursor.execute("SELECT COUNT(*) FROM Products")
        summary["products"] = cursor.fetchone()[0]

        conn.commit()
        return summary
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Migrate legacy CSV data to FinancialDatabase.db")
    parser.add_argument("--apply", action="store_true", help="Apply changes to the database")
    args = parser.parse_args()

    summary = migrate(apply_changes=args.apply)

    if args.apply:
        print("Migration complete.")
    else:
        print("Dry-run complete (no database changes).")

    print("Summary:")
    print(f"  Sales rows: {summary['sales']}")
    print(f"  Cost rows: {summary['costs']}")
    print(f"  Cash In rows: {summary['cash_in']}")
    print(f"  Stock rows: {summary['stock']}")
    print(f"  Timeline rows: {summary['timeline']}")
    print(f"  Sales Total logs: {summary['sales_total_logs']}")
    print(f"  Sales Out logs: {summary['sales_out_logs']}")
    print(f"  Stock Balance logs: {summary['stock_balance_logs']}")
    print(f"  Cash Flow logs: {summary['cash_flow_logs']}")
    print(f"  Products (post-migration): {summary.get('products', 0)}")

    if not args.apply:
        print("\nTo apply changes, run:")
        python_path = BASE_DIR / ".venv" / "Scripts" / "python.exe"
        script_path = BASE_DIR / "scripts" / "migrate_old_data.py"
        print(f"  {python_path} {script_path} --apply")


if __name__ == "__main__":
    main()
