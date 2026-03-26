"""
Reconcile Q4 VAT report against FinancialDatabase.db and apply adjustments.
Defaults to a dry run; use --apply to write changes.
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import sqlite3
from datetime import date
from pathlib import Path
from typing import Dict, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "db" / "FinancialDatabase.db"

CODE_MAP = {
    "23": "purchases_taxable",
    "24": "purchases_vat",
    "27": "sales_taxable",
    "28": "sales_vat",
}

NUMBER_RE = re.compile(r"\(?-?\d[\d, ]*\)?")
CODE_RE = re.compile(r"\[(\d+[a-z]?)\]")


def parse_money(text: str) -> Optional[float]:
    cleaned = text.strip().replace(",", "")
    cleaned = cleaned.replace(" ", "")
    if not cleaned:
        return None
    negative = cleaned.startswith("(") and cleaned.endswith(")")
    cleaned = cleaned.strip("()")
    try:
        value = float(cleaned)
    except ValueError:
        return None
    return -value if negative else value


def extract_report_values(report_text: str) -> Dict[str, float]:
    values: Dict[str, float] = {}
    reader = csv.reader(io.StringIO(report_text))
    for row in reader:
        for idx, cell in enumerate(row):
            cell = cell.strip()
            match = CODE_RE.search(cell)
            if not match:
                continue
            code = match.group(1)
            if code not in CODE_MAP:
                continue
            parsed = None
            for next_cell in row[idx + 1 :]:
                next_cell = next_cell.strip()
                if not next_cell or "[" in next_cell:
                    continue
                number_match = NUMBER_RE.search(next_cell)
                if not number_match:
                    continue
                parsed = parse_money(number_match.group(0))
                if parsed is not None:
                    break
            if parsed is None:
                continue
            values[CODE_MAP[code]] = parsed
    return values


def read_report(path: Path) -> Dict[str, float]:
    data = path.read_bytes()
    for encoding in ("utf-8-sig", "cp1258", "latin1"):
        try:
            text = data.decode(encoding)
            return extract_report_values(text)
        except UnicodeDecodeError:
            continue
    return extract_report_values(data.decode("latin1", errors="ignore"))


def ensure_vat_columns(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(Sales)")
    sales_cols = {row[1] for row in cursor.fetchall()}
    if "vat_rate" not in sales_cols:
        cursor.execute("ALTER TABLE Sales ADD COLUMN vat_rate REAL")
    if "vat_amount" not in sales_cols:
        cursor.execute("ALTER TABLE Sales ADD COLUMN vat_amount REAL")

    cursor.execute("PRAGMA table_info(Costs)")
    cost_cols = {row[1] for row in cursor.fetchall()}
    if "vat_rate" not in cost_cols:
        cursor.execute("ALTER TABLE Costs ADD COLUMN vat_rate REAL")
    if "vat_amount" not in cost_cols:
        cursor.execute("ALTER TABLE Costs ADD COLUMN vat_amount REAL")

    conn.commit()


def sum_range(conn: sqlite3.Connection, table: str, amount_col: str, date_col: str,
              start: str, end: str) -> float:
    cursor = conn.cursor()
    cursor.execute(
        f"SELECT COALESCE(SUM({amount_col}), 0) FROM {table} WHERE {date_col} BETWEEN ? AND ?",
        (start, end),
    )
    return float(cursor.fetchone()[0] or 0)


def update_vat_fields(conn: sqlite3.Connection, table: str, amount_col: str, date_col: str,
                       start: str, end: str, rate: float) -> None:
    cursor = conn.cursor()
    cursor.execute(
        f"""
        UPDATE {table}
        SET vat_rate = ?,
            vat_amount = ROUND({amount_col} * ?, 2)
        WHERE {date_col} BETWEEN ? AND ?
          AND ({amount_col} IS NOT NULL)
          AND (vat_rate IS NULL OR vat_amount IS NULL)
        """,
        (rate, rate, start, end),
    )


def apply_adjustment_sales(conn: sqlite3.Connection, delta: float, vat_rate: float,
                           period_end: str) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO Sales (sale_date, order_id, channel, product_sku, units_sold,
                           unit_price, gross_sales, vat_rate, vat_amount,
                           service_fee, shipping_fee, note)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            period_end,
            "TAX-ADJ-Q4-2025",
            "Tax Adjustment",
            None,
            None,
            None,
            delta,
            vat_rate,
            round(delta * vat_rate, 2),
            0,
            0,
            "VAT reconciliation adjustment for Q4 2025",
        ),
    )


def apply_adjustment_costs(conn: sqlite3.Connection, delta: float, vat_rate: float,
                           period_end: str) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO Costs (cost_type, cost_date, amount, vat_rate, vat_amount, note)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            "Tax Adjustment",
            period_end,
            delta,
            vat_rate,
            round(delta * vat_rate, 2),
            "VAT reconciliation adjustment for Q4 2025",
        ),
    )


def resolve_target(report: Dict[str, float], key: str, override: Optional[float]) -> float:
    if override is not None:
        return override
    if key not in report:
        raise ValueError(f"Missing value in report: {key}")
    return report[key]


def reconcile(
    report_path: Path,
    start: str,
    end: str,
    vat_rate: float,
    apply: bool,
    sales_taxable_override: Optional[float] = None,
    purchases_taxable_override: Optional[float] = None,
    sales_vat_override: Optional[float] = None,
    purchases_vat_override: Optional[float] = None,
) -> None:
    report = read_report(report_path)

    conn = sqlite3.connect(DB_PATH)
    try:
        ensure_vat_columns(conn)

        sales_total = sum_range(conn, "Sales", "gross_sales", "sale_date", start, end)
        costs_total = sum_range(conn, "Costs", "amount", "cost_date", start, end)

        target_sales = resolve_target(report, "sales_taxable", sales_taxable_override)
        target_costs = resolve_target(report, "purchases_taxable", purchases_taxable_override)

        sales_vat = resolve_target(report, "sales_vat", sales_vat_override)
        purchases_vat = resolve_target(report, "purchases_vat", purchases_vat_override)

        if sales_vat_override is None:
            sales_vat = round(target_sales * vat_rate, 2)
        if purchases_vat_override is None:
            purchases_vat = round(target_costs * vat_rate, 2)

        delta_sales = round(target_sales - sales_total, 2)
        delta_costs = round(target_costs - costs_total, 2)

        print("Report values:")
        print(f"  Sales taxable: {target_sales:,.2f}")
        print(f"  Sales VAT: {sales_vat:,.2f}")
        print(f"  Purchases taxable: {target_costs:,.2f}")
        print(f"  Purchases VAT: {purchases_vat:,.2f}")

        print("\nDatabase totals:")
        print(f"  Sales taxable: {sales_total:,.2f}")
        print(f"  Purchases taxable: {costs_total:,.2f}")

        print("\nDeltas:")
        print(f"  Sales delta: {delta_sales:,.2f}")
        print(f"  Purchases delta: {delta_costs:,.2f}")

        if not apply:
            print("\nDry run only. Use --apply to write changes.")
            return

        update_vat_fields(conn, "Sales", "gross_sales", "sale_date", start, end, vat_rate)
        update_vat_fields(conn, "Costs", "amount", "cost_date", start, end, vat_rate)

        if abs(delta_sales) >= 0.01:
            apply_adjustment_sales(conn, delta_sales, vat_rate, end)
        if abs(delta_costs) >= 0.01:
            apply_adjustment_costs(conn, delta_costs, vat_rate, end)

        conn.commit()
        print("\nAdjustments applied.")
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Reconcile VAT report against FinancialDatabase.db")
    parser.add_argument("--report", required=True, help="Path to VAT report CSV")
    parser.add_argument("--start", default="2025-10-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", default="2025-12-31", help="End date (YYYY-MM-DD)")
    parser.add_argument("--vat-rate", type=float, default=0.08, help="VAT rate (e.g., 0.08)")
    parser.add_argument("--sales-taxable", type=float, help="Override sales taxable total")
    parser.add_argument("--purchases-taxable", type=float, help="Override purchases taxable total")
    parser.add_argument("--sales-vat", type=float, help="Override sales VAT total")
    parser.add_argument("--purchases-vat", type=float, help="Override purchases VAT total")
    parser.add_argument("--apply", action="store_true", help="Apply adjustments")
    args = parser.parse_args()

    reconcile(
        Path(args.report),
        args.start,
        args.end,
        args.vat_rate,
        args.apply,
        sales_taxable_override=args.sales_taxable,
        purchases_taxable_override=args.purchases_taxable,
        sales_vat_override=args.sales_vat,
        purchases_vat_override=args.purchases_vat,
    )


if __name__ == "__main__":
    main()
