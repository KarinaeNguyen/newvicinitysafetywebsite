"""
Clean up financial data by removing zero-meaning rows.
Applies changes directly to FinancialDatabase.db.
"""

import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "db" / "FinancialDatabase.db"


def clean_table(cursor, table, where_clause, params=None):
    params = params or []
    cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE {where_clause}", params)
    before = cursor.fetchone()[0]
    cursor.execute(f"DELETE FROM {table} WHERE {where_clause}", params)
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    after_total = cursor.fetchone()[0]
    removed = before
    return removed, after_total


def main():
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        results = {}

        # Sales: remove rows with no units, no prices, no gross sales
        results["Sales"] = clean_table(
            cursor,
            "Sales",
            "(units_sold IS NULL OR units_sold = 0) AND (unit_price IS NULL OR unit_price = 0) AND (gross_sales IS NULL OR gross_sales = 0)"
        )

        # Costs: remove zero amounts with empty notes
        results["Costs"] = clean_table(
            cursor,
            "Costs",
            "(amount IS NULL OR amount = 0) AND (note IS NULL OR TRIM(note) = '')"
        )

        # Stock: remove zero entries
        results["Stock"] = clean_table(
            cursor,
            "Stock",
            "(unit_in IS NULL OR unit_in = 0) AND (unit_cost IS NULL OR unit_cost = 0) AND (total IS NULL OR total = 0)"
        )

        # Timeline: remove entries with no cash movement and no balance
        results["Timeline"] = clean_table(
            cursor,
            "Timeline",
            "(cash_in IS NULL OR cash_in = 0) AND (cash_out IS NULL OR cash_out = 0) AND (balance IS NULL OR balance = 0)"
        )

        # Logs: remove empty details
        results["Logs"] = clean_table(
            cursor,
            "Logs",
            "details IS NULL OR TRIM(details) = ''"
        )

        conn.commit()

        print("Cleanup complete.")
        for table, (removed, total) in results.items():
            print(f"{table}: removed {removed}, remaining {total}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
