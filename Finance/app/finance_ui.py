import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import sqlite3
import bcrypt
import json
import re
import shutil
import csv
from datetime import datetime
from pathlib import Path
import sys

try:
    from PIL import Image, ImageTk
except Exception:
    Image = None
    ImageTk = None

try:
    import matplotlib
    matplotlib.use("TkAgg")
    import matplotlib.pyplot as plt
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    MATPLOTLIB_OK = True
except Exception:
    MATPLOTLIB_OK = False

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors as rl_colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
    )
    REPORTLAB_OK = True
except Exception:
    REPORTLAB_OK = False


def resolve_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        start_dir = Path(sys.executable).resolve().parent
    else:
        start_dir = Path(__file__).resolve().parent
    for candidate in [start_dir, *start_dir.parents]:
        if (candidate / "security").exists() and (candidate / "db").exists():
            return candidate
    return start_dir


BASE_DIR = resolve_base_dir()
sys.path.insert(0, str(BASE_DIR / "security"))

# Database paths
SECURITY_DB = str(BASE_DIR / "security" / "security.db")
LOGS_DB = str(BASE_DIR / "security" / "logs.db")
FINANCIAL_DB = str(BASE_DIR / "db" / "FinancialDatabase.db")

# Security level names
SECURITY_LEVELS = {
    1: "Employee",
    2: "Manager",
    3: "Admin",
    4: "Owner",
    5: "Police/Government"
}

# Permission definitions
PERMISSIONS = {
    1: {  # Employee
        'financial_data': 'edit',
        'can_add_users': [],
        'can_remove_users': []
    },
    2: {  # Manager
        'financial_data': 'edit',
        'can_add_users': [1],
        'can_remove_users': [1]
    },
    3: {  # Admin
        'financial_data': 'edit',
        'can_add_users': [1, 2, 3],
        'can_remove_users': [1, 2]
    },
    4: {  # Owner
        'financial_data': 'edit',
        'can_add_users': [1, 2, 3, 4],
        'can_remove_users': [1, 2, 3, 4]
    },
    5: {  # Police/Government
        'financial_data': 'view',
        'can_add_users': [1, 2, 3, 4, 5],
        'can_remove_users': [1, 2, 3, 4, 5]
    }
}


class FinanceSystem:
    def __init__(self, root):
        self.root = root
        self.root.title("Vicinity Safety - Financial Management System")
        self.root.geometry("900x600")
        self.current_user = None
        self.current_level = None
        self._governance_api = None
        self.product_management_refresh_callback = None
        self.product_management_popup = None
        self._sku_image_popup = None
        self._sku_image_label = None
        self._sku_image_text = None
        self._sku_image_hide_after = None
        self._product_image_cache = {}
        self._placeholder_image_cache = {}
        self.user_info_label = None
        self.last_annual_export_checks = []
        self.startup_checks_complete = False
        self.startup_check_errors = []
        self.sidebar_buttons = {}
        self._login_images = []
        self.ui_palette = {
            "bg": "#f4f6f9",
            "surface": "#ffffff",
            "surface_alt": "#eef2f6",
            "sidebar": "#1f2933",
            "sidebar_button": "#2b3a42",
            "accent": "#0ea5a4",
            "accent_alt": "#2563eb",
            "danger": "#dc2626",
            "text": "#0f172a",
            "muted": "#64748b",
            "header": "#111827",
        }
        self.ui_typography = {
            "title": ("Segoe UI", 18, "bold"),
            "subtitle": ("Segoe UI", 10, "italic"),
            "label": ("Segoe UI", 9),
            "label_bold": ("Segoe UI", 9, "bold"),
            "status": ("Segoe UI", 9, "italic"),
            "table": ("Segoe UI", 9),
        }
        self.ui_spacing = {
            "xs": 4,
            "sm": 8,
            "md": 12,
            "lg": 16,
        }
        self.ui_state_colors = {
            "warning_bg": "#fff7ed",
            "warning_text": "#9a3412",
            "warning_border": "#fdba74",
            "success_text": "#166534",
            "neutral_border": "#d1d5db",
        }
        self.configure_styles()
        self.show_login()
        self.root.after(50, self.run_startup_checks)

    def run_startup_checks(self):
        self.ensure_pending_entries_table()
        self.ensure_products_schema()
        self.ensure_pos_receipt_tables()
        self.ensure_security_user_schema()
        self.ensure_sales_approval_columns()
        self.ensure_opening_balances_table()
        self.ensure_export_adjustments_table()
        self.ensure_export_text_adjustments_table()
        self.ensure_accounts_payable_table()
        self.startup_checks_complete = True
        if hasattr(self, "_startup_status_label"):
            try:
                self._startup_status_label.config(text="Ready \u2713", fg="#166534")
            except Exception:
                pass
        if self.startup_check_errors:
            message = "Startup checks found schema problems:\n\n" + "\n".join(self.startup_check_errors)
            self.root.after(0, lambda: messagebox.showerror("Startup Check Failed", message))

    def _get_governance_api(self):
        if self._governance_api is None:
            from security_governance import SecurityGovernance, DualControlError
            self._governance_api = (SecurityGovernance, DualControlError)
        return self._governance_api

    def configure_styles(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(
            "App.TNotebook",
            background=self.ui_palette["bg"],
            borderwidth=0,
            tabmargins=[8, 6, 8, 0],
        )
        style.configure(
            "App.TNotebook.Tab",
            padding=[12, 6],
            background=self.ui_palette["surface_alt"],
            foreground=self.ui_palette["text"],
            font=("Segoe UI", 9, "bold"),
        )
        style.map(
            "App.TNotebook.Tab",
            background=[("selected", self.ui_palette["surface"])],
            foreground=[("selected", self.ui_palette["text"])],
        )
        style.configure(
            "App.Treeview",
            background=self.ui_palette["surface"],
            fieldbackground=self.ui_palette["surface"],
            foreground=self.ui_palette["text"],
            rowheight=30,
            borderwidth=0,
            font=self.ui_typography["table"],
        )
        style.map(
            "App.Treeview",
            background=[("selected", "#dbeafe")],
            foreground=[("selected", self.ui_palette["text"])],
        )
        style.configure("App.Treeview.Dense", rowheight=26)
        style.configure(
            "App.Treeview.Heading",
            background=self.ui_palette["surface_alt"],
            foreground=self.ui_palette["text"],
            font=self.ui_typography["label_bold"],
        )

    def log_action(self, action, details=""):
        """Log all actions to the immutable audit log"""
        try:
            conn = sqlite3.connect(LOGS_DB)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO AuditLog (user_id, action, affected_table, affected_record, security_level, details) VALUES (?, ?, ?, ?, ?, ?)",
                (self.current_user['user_id'], action, '', '', self.current_level, details)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Logging error: {e}")

    def record_startup_check_error(self, check_name, error):
        message = f"{check_name}: {error}"
        self.startup_check_errors.append(message)
        print(f"Startup check error: {message}")

    def ensure_pending_entries_table(self):
        """Ensure the pending entries table exists in the financial database"""
        try:
            conn = sqlite3.connect(FINANCIAL_DB)
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS PendingEntries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    created_by INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    approved_by INTEGER,
                    approved_at TIMESTAMP,
                    rejected_reason TEXT
                )
                """
            )
            conn.commit()
            conn.close()
        except Exception as e:
            self.record_startup_check_error("Pending entries table init", e)

    def ensure_products_schema(self):
        """Ensure Products has current_unit_price for retail pricing"""
        try:
            conn = sqlite3.connect(FINANCIAL_DB)
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(Products)")
            columns = {row[1] for row in cursor.fetchall()}
            if "current_unit_price" not in columns:
                cursor.execute("ALTER TABLE Products ADD COLUMN current_unit_price REAL")
            if "unit_price" in columns:
                cursor.execute(
                    """
                    UPDATE Products
                    SET current_unit_price = unit_price
                    WHERE current_unit_price IS NULL
                    """
                )
            if "image_path" not in columns:
                cursor.execute("ALTER TABLE Products ADD COLUMN image_path TEXT")
            conn.commit()
            conn.close()
        except Exception as e:
            self.record_startup_check_error("Products schema init", e)

    def ensure_pos_receipt_tables(self):
        """Ensure POS receipt workflow tables exist"""
        try:
            conn = sqlite3.connect(FINANCIAL_DB)
            cursor = conn.cursor()

            cursor.execute("PRAGMA table_info(Stock)")
            stock_columns = {row[1] for row in cursor.fetchall()}
            if "tax_rate" not in stock_columns:
                cursor.execute("ALTER TABLE Stock ADD COLUMN tax_rate REAL")
            if "tax_amount" not in stock_columns:
                cursor.execute("ALTER TABLE Stock ADD COLUMN tax_amount REAL")
            if "current_unit_price" not in stock_columns:
                cursor.execute("ALTER TABLE Stock ADD COLUMN current_unit_price REAL")
            if "approved_by" not in stock_columns:
                cursor.execute("ALTER TABLE Stock ADD COLUMN approved_by INTEGER")
            if "approved_at" not in stock_columns:
                cursor.execute("ALTER TABLE Stock ADD COLUMN approved_at TIMESTAMP")

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS CustomerProfiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name TEXT NOT NULL,
                    phone TEXT,
                    email TEXT,
                    address TEXT,
                    norm_phone TEXT,
                    norm_email TEXT,
                    norm_address TEXT,
                    status TEXT NOT NULL DEFAULT 'ACTIVE',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_customer_norm_phone ON CustomerProfiles(norm_phone)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_customer_norm_email ON CustomerProfiles(norm_email)")

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS SalesReceipts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pending_entry_id INTEGER,
                    customer_id INTEGER,
                    receipt_no TEXT NOT NULL,
                    sale_date DATE,
                    tax_rate REAL,
                    subtotal REAL,
                    service_total REAL,
                    tax_amount REAL,
                    total REAL,
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    pdf_path TEXT,
                    note TEXT,
                    created_by INTEGER,
                    approved_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    approved_at TIMESTAMP
                )
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS SalesReceiptLines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    receipt_id INTEGER NOT NULL,
                    line_type TEXT NOT NULL,
                    item_name TEXT NOT NULL,
                    product_sku TEXT,
                    unit_price REAL,
                    quantity INTEGER,
                    line_total REAL
                )
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS CustomerMatchFlags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pending_entry_id INTEGER,
                    submitted_name TEXT,
                    submitted_phone TEXT,
                    submitted_email TEXT,
                    submitted_address TEXT,
                    matched_customer_id INTEGER,
                    matched_score INTEGER,
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    review_note TEXT,
                    reviewed_by INTEGER,
                    reviewed_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            conn.commit()
            conn.close()
        except Exception as e:
            self.record_startup_check_error("POS receipt table init", e)

    def ensure_security_user_schema(self):
        """Ensure Users has editable display ID separate from internal user_id."""
        try:
            conn = sqlite3.connect(SECURITY_DB)
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(Users)")
            columns = {row[1] for row in cursor.fetchall()}
            if "display_id" not in columns:
                cursor.execute("ALTER TABLE Users ADD COLUMN display_id TEXT")

            # Backfill existing users so each row has a visible ID value.
            cursor.execute(
                """
                UPDATE Users
                SET display_id = CAST(user_id AS TEXT)
                WHERE display_id IS NULL OR TRIM(display_id) = ''
                """
            )
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_display_id_unique ON Users(display_id)")
            conn.commit()
            conn.close()
        except Exception as e:
            self.record_startup_check_error("Security user schema init", e)

    def ensure_sales_approval_columns(self):
        """Add approved_by and approved_at to Sales table for display in Sales Detail view."""
        try:
            conn = sqlite3.connect(FINANCIAL_DB)
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(Sales)")
            existing = {row[1] for row in cursor.fetchall()}
            if "approved_by" not in existing:
                cursor.execute("ALTER TABLE Sales ADD COLUMN approved_by INTEGER")
            if "approved_at" not in existing:
                cursor.execute("ALTER TABLE Sales ADD COLUMN approved_at TIMESTAMP")
            conn.commit()
            conn.close()
        except Exception as e:
            self.record_startup_check_error("Sales approval columns migration", e)

    def ensure_opening_balances_table(self):
        try:
            conn = sqlite3.connect(FINANCIAL_DB)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS OpeningBalances (
                    year INTEGER PRIMARY KEY,
                    opening_cash REAL NOT NULL DEFAULT 0,
                    opening_receivables REAL NOT NULL DEFAULT 0,
                    opening_payables REAL NOT NULL DEFAULT 0,
                    opening_owner_capital REAL NOT NULL DEFAULT 0,
                    opening_retained_earnings REAL NOT NULL DEFAULT 0,
                    opening_vat_deductible REAL NOT NULL DEFAULT 0,
                    note TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            self.record_startup_check_error("Opening balances table init", e)

    def ensure_export_adjustments_table(self):
        try:
            conn = sqlite3.connect(FINANCIAL_DB)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ExportAdjustments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    year INTEGER NOT NULL,
                    form_code TEXT NOT NULL,
                    line_code TEXT NOT NULL,
                    line_label TEXT,
                    adjusted_value REAL NOT NULL,
                    original_value REAL,
                    note TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(year, form_code, line_code)
                )
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            self.record_startup_check_error("Export adjustments table init", e)

    def get_export_adjustments_for_year(self, year):
        result = {}
        try:
            conn = sqlite3.connect(FINANCIAL_DB)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT form_code, line_code, adjusted_value FROM ExportAdjustments WHERE year = ?",
                (int(year),)
            )
            for form_code, line_code, adjusted_value in cursor.fetchall():
                result[(form_code, line_code)] = float(adjusted_value)
            conn.close()
        except Exception:
            pass
        return result

    def save_export_adjustment(self, year, form_code, line_code, line_label, adjusted_value, original_value, note):
        conn = sqlite3.connect(FINANCIAL_DB)
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO ExportAdjustments
                    (year, form_code, line_code, line_label, adjusted_value, original_value, note, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                int(year), str(form_code), str(line_code), str(line_label or ""),
                float(adjusted_value), float(original_value or 0), str(note or "")
            ))
            conn.commit()
        finally:
            conn.close()

    def delete_export_adjustment(self, year, form_code, line_code):
        conn = sqlite3.connect(FINANCIAL_DB)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM ExportAdjustments WHERE year = ? AND form_code = ? AND line_code = ?",
                (int(year), str(form_code), str(line_code))
            )
            conn.commit()
        finally:
            conn.close()

    def ensure_export_text_adjustments_table(self):
        try:
            conn = sqlite3.connect(FINANCIAL_DB)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ExportTextAdjustments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    year INTEGER NOT NULL,
                    form_code TEXT NOT NULL,
                    line_code TEXT NOT NULL,
                    field_type TEXT NOT NULL,
                    text_value TEXT NOT NULL,
                    note TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(year, form_code, line_code, field_type)
                )
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            self.record_startup_check_error("Export text adjustments table init", e)

    def get_export_text_adjustments_for_year(self, year):
        result = {}
        try:
            conn = sqlite3.connect(FINANCIAL_DB)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT form_code, line_code, field_type, text_value "
                "FROM ExportTextAdjustments WHERE year = ?",
                (int(year),)
            )
            for form_code, line_code, field_type, text_value in cursor.fetchall():
                result[(str(form_code), str(line_code), str(field_type))] = str(text_value)
            conn.close()
        except Exception:
            pass
        return result

    def save_export_text_adjustment(self, year, form_code, line_code, field_type, text_value, note=""):
        conn = sqlite3.connect(FINANCIAL_DB)
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO ExportTextAdjustments
                    (year, form_code, line_code, field_type, text_value, note, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (int(year), str(form_code), str(line_code), str(field_type),
                  str(text_value), str(note or "")))
            conn.commit()
        finally:
            conn.close()

    def delete_export_text_adjustment(self, year, form_code, line_code, field_type):
        conn = sqlite3.connect(FINANCIAL_DB)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM ExportTextAdjustments WHERE year=? AND form_code=? AND line_code=? AND field_type=?",
                (int(year), str(form_code), str(line_code), str(field_type))
            )
            conn.commit()
        finally:
            conn.close()

    # ── Accounts Payable ──────────────────────────────────────────────────────
    def ensure_accounts_payable_table(self):
        try:
            conn = sqlite3.connect(FINANCIAL_DB)
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS AccountsPayable (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        vendor_name TEXT NOT NULL,
                        invoice_ref  TEXT,
                        invoice_date TEXT NOT NULL,
                        due_date     TEXT,
                        amount       REAL NOT NULL DEFAULT 0,
                        paid_amount  REAL NOT NULL DEFAULT 0,
                        paid_date    TEXT,
                        note         TEXT,
                        created_at   TEXT DEFAULT (datetime('now'))
                    )
                """)
                conn.commit()
            finally:
                conn.close()
        except Exception as e:
            self.startup_check_errors.append(f"AccountsPayable table: {e}")

    def get_accounts_payable_as_of(self, end_date):
        """Return total outstanding AP (invoiced on or before end_date, minus payments by end_date)."""
        try:
            conn = sqlite3.connect(FINANCIAL_DB)
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT COALESCE(SUM(
                        CASE
                            WHEN paid_date IS NULL OR paid_date > ? THEN amount
                            ELSE MAX(0, amount - COALESCE(paid_amount, 0))
                        END
                    ), 0)
                    FROM AccountsPayable
                    WHERE invoice_date <= ?
                    """,
                    (end_date, end_date),
                )
                return float((cursor.fetchone() or [0])[0] or 0)
            finally:
                conn.close()
        except Exception:
            return 0.0

    def get_all_accounts_payable_entries(self):
        try:
            conn = sqlite3.connect(FINANCIAL_DB)
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, vendor_name, invoice_ref, invoice_date, due_date, "
                    "amount, paid_amount, paid_date, note FROM AccountsPayable ORDER BY invoice_date DESC, id DESC"
                )
                return cursor.fetchall()
            finally:
                conn.close()
        except Exception:
            return []

    def save_accounts_payable_entry(self, entry_id, vendor_name, invoice_ref, invoice_date,
                                     due_date, amount, paid_amount, paid_date, note):
        conn = sqlite3.connect(FINANCIAL_DB)
        try:
            cursor = conn.cursor()
            if entry_id:
                cursor.execute(
                    "UPDATE AccountsPayable SET vendor_name=?, invoice_ref=?, invoice_date=?, "
                    "due_date=?, amount=?, paid_amount=?, paid_date=?, note=? WHERE id=?",
                    (vendor_name, invoice_ref or "", invoice_date, due_date or "",
                     float(amount or 0), float(paid_amount or 0), paid_date or "", note or "", int(entry_id))
                )
            else:
                cursor.execute(
                    "INSERT INTO AccountsPayable (vendor_name, invoice_ref, invoice_date, due_date, "
                    "amount, paid_amount, paid_date, note) VALUES (?,?,?,?,?,?,?,?)",
                    (vendor_name, invoice_ref or "", invoice_date, due_date or "",
                     float(amount or 0), float(paid_amount or 0), paid_date or "", note or "")
                )
            conn.commit()
        finally:
            conn.close()

    def delete_accounts_payable_entry(self, entry_id):
        conn = sqlite3.connect(FINANCIAL_DB)
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM AccountsPayable WHERE id=?", (int(entry_id),))
            conn.commit()
        finally:
            conn.close()

    def get_opening_balance_for_year(self, year):
        empty = {
            "opening_cash": 0.0,
            "opening_receivables": 0.0,
            "opening_payables": 0.0,
            "opening_owner_capital": 0.0,
            "opening_retained_earnings": 0.0,
            "opening_vat_deductible": 0.0,
            "note": "",
        }
        try:
            conn = sqlite3.connect(FINANCIAL_DB)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT opening_cash, opening_receivables, opening_payables, "
                "opening_owner_capital, opening_retained_earnings, opening_vat_deductible, note "
                "FROM OpeningBalances WHERE year = ?",
                (int(year),)
            )
            row = cursor.fetchone()
            conn.close()
            if row:
                return {
                    "opening_cash": float(row[0] or 0),
                    "opening_receivables": float(row[1] or 0),
                    "opening_payables": float(row[2] or 0),
                    "opening_owner_capital": float(row[3] or 0),
                    "opening_retained_earnings": float(row[4] or 0),
                    "opening_vat_deductible": float(row[5] or 0),
                    "note": row[6] or "",
                }
        except Exception:
            pass
        return empty

    def save_opening_balance_for_year(self, year, payload):
        conn = sqlite3.connect(FINANCIAL_DB)
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO OpeningBalances
                    (year, opening_cash, opening_receivables, opening_payables,
                     opening_owner_capital, opening_retained_earnings, opening_vat_deductible, note, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                int(year),
                float(payload.get("opening_cash", 0)),
                float(payload.get("opening_receivables", 0)),
                float(payload.get("opening_payables", 0)),
                float(payload.get("opening_owner_capital", 0)),
                float(payload.get("opening_retained_earnings", 0)),
                float(payload.get("opening_vat_deductible", 0)),
                str(payload.get("note", "")),
            ))
            conn.commit()
        finally:
            conn.close()

    def open_opening_balances_dialog(self, default_year, on_saved=None):
        existing = self.get_opening_balance_for_year(default_year)

        dlg = tk.Toplevel(self.root)
        dlg.title(f"Opening Balances \u2013 {default_year}")
        dlg.resizable(False, False)
        dlg.grab_set()
        bg = self.ui_palette["bg"]
        dlg.configure(bg=bg)

        # Section-grouped fields
        asset_fields = [
            ("opening_cash",           "Opening Cash *"),
            ("opening_receivables",    "Receivables"),
            ("opening_vat_deductible", "VAT Deductible"),
        ]
        liab_fields = [
            ("opening_payables",          "Payables"),
            ("opening_owner_capital",     "Owner Capital *"),
            ("opening_retained_earnings", "Retained Earnings *"),
        ]

        def _section_header(text, row):
            tk.Frame(dlg, bg=self.ui_state_colors["neutral_border"], height=1).grid(
                row=row, column=0, columnspan=2, sticky="ew", padx=12, pady=(8, 0)
            )
            tk.Label(dlg, text=text, bg=bg, fg=self.ui_palette["accent"],
                     font=("Segoe UI", 8, "bold")).grid(
                row=row+1, column=0, columnspan=2, sticky="w", padx=12, pady=(2, 4)
            )

        entries = {}
        row_idx = 0
        _section_header("ASSETS", row_idx);  row_idx += 2
        for key, label in asset_fields:
            tk.Label(dlg, text=label, bg=bg, fg=self.ui_palette["text"],
                     font=("Segoe UI", 9), anchor="w").grid(
                row=row_idx, column=0, sticky="w", padx=12, pady=4)
            var = tk.StringVar(value=f"{existing.get(key, 0.0):,.0f}")
            tk.Entry(dlg, textvariable=var, width=22, justify="right").grid(row=row_idx, column=1, padx=12, pady=4)
            entries[key] = var
            row_idx += 1

        _section_header("LIABILITIES & EQUITY", row_idx);  row_idx += 2
        for key, label in liab_fields:
            tk.Label(dlg, text=label, bg=bg, fg=self.ui_palette["text"],
                     font=("Segoe UI", 9), anchor="w").grid(
                row=row_idx, column=0, sticky="w", padx=12, pady=4)
            var = tk.StringVar(value=f"{existing.get(key, 0.0):,.0f}")
            tk.Entry(dlg, textvariable=var, width=22, justify="right").grid(row=row_idx, column=1, padx=12, pady=4)
            entries[key] = var
            row_idx += 1

        tk.Label(dlg, text="Note", bg=bg, fg=self.ui_palette["text"],
                 font=("Segoe UI", 9), anchor="w").grid(
            row=row_idx, column=0, sticky="w", padx=12, pady=4)
        note_var = tk.StringVar(value=existing.get("note", ""))
        tk.Entry(dlg, textvariable=note_var, width=36).grid(
            row=row_idx, column=1, padx=12, pady=4, sticky="w")

        def _save():
            try:
                payload = {key: float(str(var.get()).replace(",", "")) for key, var in entries.items()}
                payload["note"] = note_var.get().strip()
                self.save_opening_balance_for_year(default_year, payload)
                self.log_action(
                    "OPENING_BALANCE_SAVED",
                    f"year={default_year} cash={payload['opening_cash']:.0f} capital={payload['opening_owner_capital']:.0f}"
                )
                dlg.destroy()
                if on_saved:
                    on_saved()
            except ValueError as exc:
                messagebox.showerror("Invalid Input", f"Please enter valid numbers.\n{exc}", parent=dlg)

        row_idx += 1
        tk.Button(
            dlg, text="Save / Luu", command=_save,
            bg=self.ui_palette["accent"], fg="white", relief="flat", padx=16, pady=4
        ).grid(row=row_idx, column=0, columnspan=2, pady=12)

    def open_export_adjustments_dialog(self, year, on_saved=None):
        """Surgical per-line override dialog for all four statutory export forms."""
        adj_existing = self.get_export_adjustments_for_year(year)

        # ---- per-form line definitions ----------------------------------------
        form_lines = {
            "B01a": [
                ("110", "I. Tien va cac khoan tuong duong tien"),
                ("120", "II. Dau tu tai chinh"),
                ("130", "III. Cac khoan phai thu"),
                ("140", "IV. Hang ton kho"),
                ("141", "1. Hang ton kho"),
                ("150", "V. Tai san co dinh"),
                ("160", "VI. Bat dong san dau tu"),
                ("170", "VII. XDCB do dang"),
                ("180", "VIII. Tai san khac"),
                ("181", "1. Thue GTGT duoc khau tru"),
                ("200", "TONG CONG TAI SAN"),
                ("300", "I. No phai tra"),
                ("311", "1. Phai tra nguoi ban"),
                ("312", "2. Nguoi mua tra tien truoc"),
                ("313", "3. Thue va cac khoan phai nop Nha nuoc"),
                ("314", "4. Phai tra nguoi lao dong"),
                ("315", "5. Phai tra khac"),
                ("400", "II. Von chu so huu"),
                ("411", "1. Von gop cua chu so huu"),
                ("417", "7. Loi nhuan sau thue chua phan phoi"),
                ("500", "TONG CONG NGUON VON"),
            ],
            "B02": [
                ("01", "1. Doanh thu ban hang va cung cap dich vu"),
                ("02", "2. Cac khoan giam tru doanh thu"),
                ("10", "3. Doanh thu thuan"),
                ("11", "4. Gia von hang ban"),
                ("20", "5. Loi nhuan gop"),
                ("21", "6. Doanh thu hoat dong tai chinh"),
                ("22", "7. Chi phi tai chinh"),
                ("24", "8. Chi phi quan ly kinh doanh"),
                ("30", "9. Loi nhuan thuan tu HDKD"),
                ("31", "10. Thu nhap khac"),
                ("32", "11. Chi phi khac"),
                ("40", "12. Loi nhuan khac"),
                ("50", "13. Tong loi nhuan truoc thue"),
                ("51", "14. Chi phi thue TNDN"),
                ("60", "15. Loi nhuan sau thue TNDN"),
            ],
            "B03": [
                ("01", "1. Tien thu tu ban hang, cung cap dich vu"),
                ("02", "2. Tien chi tra cho nguoi cung cap"),
                ("03", "3. Tien chi tra cho nguoi lao dong"),
                ("07", "7. Tien chi khac cho HDKD"),
                ("20", "Luu chuyen tien thuan tu HDKD"),
                ("30", "Luu chuyen tien thuan tu HDDT"),
                ("31", "1. Tien thu tu phat hanh co phieu, nhan von gop"),
                ("40", "Luu chuyen tien thuan tu HDTC"),
                ("50", "Luu chuyen tien thuan trong ky"),
                ("60", "Tien va tuong duong tien dau ky"),
                ("61", "Anh huong cua thay doi ty gia"),
                ("70", "Tien va tuong duong tien cuoi ky"),
            ],
            "F01": [
                ("111", "Tien mat"),
                ("1111", "Tien Viet Nam (mat)"),
                ("112", "Tien gui Ngan hang"),
                ("1121", "Tien Viet Nam (bank)"),
                ("131", "Phai thu cua khach hang"),
                ("133", "Thue GTGT duoc khau tru"),
                ("1331", "Thue GTGT duoc khau tru (hang hoa)"),
                ("156", "Hang hoa"),
                ("331", "Phai tra cho nguoi ban"),
                ("333", "Thue va cac khoan phai nop"),
                ("3331", "Thue GTGT phai nop"),
                ("33311", "Thue GTGT dau ra"),
                ("334", "Phai tra nguoi lao dong"),
                ("411", "Von dau tu cua chu so huu"),
                ("4111", "Von gop cua chu so huu"),
                ("421", "Loi nhuan sau thue chua phan phoi"),
                ("4212", "LNST chua phan phoi nam nay"),
                ("511", "Doanh thu ban hang"),
                ("5111", "Doanh thu ban hang hoa"),
                ("632", "Gia von hang ban"),
                ("642", "Chi phi quan ly kinh doanh"),
                ("6422", "Chi phi quan ly doanh nghiep"),
                ("911", "Xac dinh ket qua kinh doanh"),
            ],
        }

        dlg = tk.Toplevel(self.root)
        dlg.title(f"Adjust Export Values \u2013 {year}")
        dlg.geometry("780x520")
        dlg.grab_set()
        bg = self.ui_palette["bg"]
        dlg.configure(bg=bg)

        # top instruction label
        tk.Label(
            dlg,
            text=f"Year {year}: enter the accountant-verified value for any line. Leave blank = use calculated value.",
            bg=bg, fg=self.ui_palette["muted"], font=("Segoe UI", 9, "italic"),
            wraplength=740, justify="left",
        ).pack(fill="x", padx=12, pady=(8, 2))

        notebook = ttk.Notebook(dlg)
        notebook.pack(fill="both", expand=True, padx=8, pady=4)

        # pending edits: {(form, code): (StringVar_value, StringVar_note, label)}
        pending = {}

        def _build_tab(form_code, lines):
            frame = tk.Frame(notebook, bg=bg)
            notebook.add(frame, text=form_code)

            cols = ("Code", "Line Label", "Adjusted Value", "Note")
            tree = ttk.Treeview(frame, columns=cols, show="headings", height=14)
            tree.heading("Code", text="Code")
            tree.heading("Line Label", text="Line Label")
            tree.heading("Adjusted Value", text="Adjusted Value")
            tree.heading("Note", text="Note")
            tree.column("Code", width=70, anchor="center")
            tree.column("Line Label", width=310, anchor="w")
            tree.column("Adjusted Value", width=160, anchor="e")
            tree.column("Note", width=180, anchor="w")

            vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
            tree.configure(yscrollcommand=vsb.set)
            tree.pack(side="left", fill="both", expand=True)
            vsb.pack(side="right", fill="y")

            for code, label in lines:
                adj_val = adj_existing.get((form_code, code))
                adj_text = f"{adj_val:,.0f}" if adj_val is not None else ""
                iid = f"{form_code}|{code}"
                tree.insert("", "end", iid=iid, values=(code, label, adj_text, ""))
                if iid in pending:
                    pass  # already set from previous tab build

            def _on_double_click(event):
                sel = tree.selection()
                if not sel:
                    return
                iid = sel[0]
                parts = iid.split("|", 1)
                if len(parts) != 2:
                    return
                fc, lc = parts
                # find label
                row_vals = tree.item(iid, "values")
                lbl = row_vals[1] if len(row_vals) > 1 else ""
                cur_adj = row_vals[2] if len(row_vals) > 2 else ""
                cur_note = row_vals[3] if len(row_vals) > 3 else ""

                popup = tk.Toplevel(dlg)
                popup.title(f"Edit {fc} line {lc}")
                popup.resizable(False, False)
                popup.grab_set()
                popup.configure(bg=bg)

                tk.Label(popup, text=f"{fc} — {lc}: {lbl}", bg=bg, fg=self.ui_palette["text"],
                         font=("Segoe UI", 9, "bold")).grid(row=0, column=0, columnspan=2, padx=12, pady=(10, 4), sticky="w")
                tk.Label(popup, text="Adjusted Value (blank = clear override):", bg=bg,
                         fg=self.ui_palette["text"], font=("Segoe UI", 9)).grid(row=1, column=0, padx=12, pady=4, sticky="w")
                val_var = tk.StringVar(value=cur_adj)
                tk.Entry(popup, textvariable=val_var, width=22, justify="right").grid(row=1, column=1, padx=12, pady=4)
                tk.Label(popup, text="Note:", bg=bg, fg=self.ui_palette["text"],
                         font=("Segoe UI", 9)).grid(row=2, column=0, padx=12, pady=4, sticky="w")
                note_var = tk.StringVar(value=cur_note)
                tk.Entry(popup, textvariable=note_var, width=32).grid(row=2, column=1, padx=12, pady=4)

                def _apply():
                    raw = val_var.get().strip().replace(",", "")
                    note_text = note_var.get().strip()
                    if raw == "":
                        tree.set(iid, "Adjusted Value", "")
                        tree.set(iid, "Note", "")
                        pending[iid] = (None, note_text, lbl)
                    else:
                        try:
                            fval = float(raw)
                            tree.set(iid, "Adjusted Value", f"{fval:,.0f}")
                            tree.set(iid, "Note", note_text)
                            pending[iid] = (fval, note_text, lbl)
                        except ValueError:
                            messagebox.showerror("Invalid", "Please enter a valid number.", parent=popup)
                            return
                    popup.destroy()

                tk.Button(popup, text="Apply", command=_apply,
                          bg=self.ui_palette["accent"], fg="white", relief="flat", padx=12, pady=4
                          ).grid(row=3, column=0, columnspan=2, pady=10)

            tree.bind("<Double-1>", _on_double_click)

        for fc, lines in form_lines.items():
            _build_tab(fc, lines)

        # ---- Text / Labels tab -----------------------------------------------
        text_existing = self.get_export_text_adjustments_for_year(year)
        text_pending = {}  # {(form_code, line_code, field_type): str_or_None}

        text_lines = [
            # (form_code, line_code, field_type, default_value, description)
            ("HEADER", "company",   "company_name",    "CONG TY TNHH VICINITY SAFETY",                       "Company Name (all forms)"),
            ("HEADER", "company",   "company_address", "267 Nguyen Van Dau, Phuong Binh Loi Trung, Ho Chi Minh", "Company Address (all forms)"),
            ("B01a-DNN", "header",  "period_text",     f"Tai ngay 31 thang 12 nam {year}",                    "B01a Period Text"),
            ("B02-DNN", "header",   "period_text",     f"Nam {year}",                                         "B02 Period Text"),
            ("B03-DNN", "header",   "period_text",     f"Nam {year}",                                         "B03 Period Text"),
            ("F01-DNN", "header",   "period_text",     f"Nam {year}",                                         "F01 Period Text"),
        ]
        # Line labels for B01a
        for code, lbl in [
            ("110","I. Tien va cac khoan tuong duong tien"), ("130","III. Cac khoan phai thu"),
            ("140","IV. Hang ton kho"), ("181","1. Thue GTGT duoc khau tru"),
            ("200","TONG CONG TAI SAN"), ("300","I. No phai tra"),
            ("311","1. Phai tra nguoi ban"), ("313","3. Thue va cac khoan phai nop"),
            ("411","1. Von gop cua chu so huu"), ("417","7. Loi nhuan sau thue"),
            ("500","TONG CONG NGUON VON"),
        ]:
            text_lines.append(("B01a", code, "label", lbl, f"B01a {code} label"))
        # Line labels for B02
        for code, lbl in [
            ("01","1. Doanh thu ban hang"), ("10","3. Doanh thu thuan"),
            ("11","4. Gia von hang ban"), ("20","5. Loi nhuan gop"),
            ("24","8. Chi phi quan ly kinh doanh"), ("30","9. Loi nhuan thuan tu HDKD"),
            ("60","15. Loi nhuan sau thue TNDN"),
        ]:
            text_lines.append(("B02", code, "label", lbl, f"B02 {code} label"))
        # Line labels for B03
        for code, lbl in [
            ("01","1. Tien thu tu ban hang"), ("02","2. Tien chi tra nguoi cung cap"),
            ("20","Luu chuyen thuan HDKD"), ("50","Luu chuyen thuan trong ky"),
            ("60","Tien dau ky"), ("70","Tien cuoi ky"),
        ]:
            text_lines.append(("B03", code, "label", lbl, f"B03 {code} label"))
        # Account names for F01
        for code, lbl in [
            ("111","Tien mat"), ("131","Phai thu cua khach hang"),
            ("133","Thue GTGT duoc khau tru"), ("156","Hang hoa"),
            ("331","Phai tra cho nguoi ban"), ("411","Von dau tu cua chu so huu"),
            ("421","Loi nhuan sau thue chua phan phoi"),
        ]:
            text_lines.append(("F01", code, "label", lbl, f"F01 {code} account name"))

        txt_frame = tk.Frame(notebook, bg=bg)
        notebook.add(txt_frame, text="Text / Labels")

        tcols = ("Form", "Field", "Default Value", "Custom Value")
        txt_tree = ttk.Treeview(txt_frame, columns=tcols, show="headings", height=18)
        txt_tree.heading("Form",          text="Form")
        txt_tree.heading("Field",         text="Field / Code")
        txt_tree.heading("Default Value", text="Default Value")
        txt_tree.heading("Custom Value",  text="Custom Value")
        txt_tree.column("Form",          width=80,  anchor="center")
        txt_tree.column("Field",         width=200, anchor="w")
        txt_tree.column("Default Value", width=230, anchor="w")
        txt_tree.column("Custom Value",  width=230, anchor="w")
        tvsb = ttk.Scrollbar(txt_frame, orient="vertical", command=txt_tree.yview)
        txt_tree.configure(yscrollcommand=tvsb.set)
        txt_tree.pack(side="left", fill="both", expand=True)
        tvsb.pack(side="right", fill="y")

        for fc, lc, ft, default_val, desc in text_lines:
            iid = f"TXT|{fc}|{lc}|{ft}"
            cur = text_existing.get((fc, lc, ft), "")
            txt_tree.insert("", "end", iid=iid, values=(f"{fc}/{lc}", desc, default_val, cur))

        def _on_txt_double_click(event):
            sel = txt_tree.selection()
            if not sel:
                return
            iid = sel[0]
            parts = iid.split("|", 3)
            if len(parts) != 4:
                return
            _, fc, lc, ft = parts
            row_vals = txt_tree.item(iid, "values")
            default_val = row_vals[2] if len(row_vals) > 2 else ""
            cur_val = row_vals[3] if len(row_vals) > 3 else ""

            popup = tk.Toplevel(dlg)
            popup.title(f"Edit text: {fc}/{lc}/{ft}")
            popup.resizable(False, False)
            popup.grab_set()
            popup.configure(bg=bg)

            tk.Label(popup, text=f"{fc} — {lc} / {ft}", bg=bg, fg=self.ui_palette["text"],
                     font=("Segoe UI", 9, "bold")).grid(row=0, column=0, columnspan=2, padx=12, pady=(10, 4), sticky="w")
            tk.Label(popup, text="Default:", bg=bg, fg=self.ui_palette["muted"],
                     font=("Segoe UI", 8)).grid(row=1, column=0, padx=12, pady=2, sticky="w")
            tk.Label(popup, text=default_val, bg=bg, fg=self.ui_palette["muted"],
                     font=("Segoe UI", 8), wraplength=320, justify="left").grid(row=1, column=1, padx=12, pady=2, sticky="w")
            tk.Label(popup, text="Custom Value (blank = clear):", bg=bg, fg=self.ui_palette["text"],
                     font=("Segoe UI", 9)).grid(row=2, column=0, padx=12, pady=4, sticky="w")
            val_var = tk.StringVar(value=cur_val)
            tk.Entry(popup, textvariable=val_var, width=40).grid(row=2, column=1, padx=12, pady=4)

            def _apply_text():
                new_val = val_var.get()  # keep raw — may be blank to clear
                if new_val.strip() == "":
                    txt_tree.set(iid, "Custom Value", "")
                    text_pending[(fc, lc, ft)] = None
                else:
                    txt_tree.set(iid, "Custom Value", new_val)
                    text_pending[(fc, lc, ft)] = new_val
                popup.destroy()

            tk.Button(popup, text="Apply", command=_apply_text,
                      bg=self.ui_palette["accent"], fg="white", relief="flat", padx=12, pady=4
                      ).grid(row=3, column=0, columnspan=2, pady=10)

        txt_tree.bind("<Double-1>", _on_txt_double_click)

        # ---- bottom Save All Changes button -----------------------------------
        bottom = tk.Frame(dlg, bg=bg)
        bottom.pack(fill="x", padx=8, pady=6)

        status_var = tk.StringVar(value="Double-click any row to set/clear an override.")
        tk.Label(bottom, textvariable=status_var, bg=bg, fg=self.ui_palette["muted"],
                 font=("Segoe UI", 9, "italic")).pack(side="left", padx=8)

        def _save_all():
            saved = 0
            deleted = 0
            for iid, (fval, note_text, lbl) in pending.items():
                parts = iid.split("|", 1)
                if len(parts) != 2:
                    continue
                fc, lc = parts
                if fval is None:
                    self.delete_export_adjustment(year, fc, lc)
                    deleted += 1
                else:
                    orig = adj_existing.get((fc, lc), 0.0)
                    self.save_export_adjustment(year, fc, lc, lbl, fval, orig, note_text)
                    self.log_action(
                        "EXPORT_ADJUSTMENT_SAVED",
                        f"year={year} form={fc} line={lc} value={fval:.0f}"
                    )
                    saved += 1
            adj_existing.update({
                (fc, lc): fval
                for iid, (fval, note_text, lbl) in pending.items()
                if fval is not None
                for fc, lc in [iid.split("|", 1)]
            })
            # process text pending
            for (fc, lc, ft), tval in text_pending.items():
                if tval is None:
                    self.delete_export_text_adjustment(year, fc, lc, ft)
                    deleted += 1
                else:
                    self.save_export_text_adjustment(year, fc, lc, ft, tval)
                    self.log_action(
                        "EXPORT_TEXT_ADJUSTMENT_SAVED",
                        f"year={year} form={fc} line={lc} field={ft}"
                    )
                    saved += 1
            status_var.set(f"Saved: {saved} override(s), cleared: {deleted}. Close dialog to refresh.")
            if on_saved:
                on_saved()

        tk.Button(
            bottom, text="Save All Changes", command=_save_all,
            bg="#2e7d32", fg="white", relief="flat", padx=16, pady=4,
        ).pack(side="right", padx=8)

        tk.Button(
            bottom, text="Close", command=dlg.destroy,
            bg="#607d8b", fg="white", relief="flat", padx=12, pady=4,
        ).pack(side="right", padx=4)

    def normalize_phone(self, value):
        text = str(value or "").strip()
        if not text:
            return ""
        return re.sub(r"[^0-9+]", "", text)

    def normalize_email(self, value):
        return str(value or "").strip().lower()

    def normalize_address(self, value):
        text = str(value or "").strip().lower()
        text = re.sub(r"\s+", " ", text)
        return text

    def generate_receipt_no(self):
        return f"POS-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    def find_customer_matches(self, phone, email, address):
        norm_phone = self.normalize_phone(phone)
        norm_email = self.normalize_email(email)
        norm_address = self.normalize_address(address)
        conn = sqlite3.connect(FINANCIAL_DB)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, full_name, phone, email, address, norm_phone, norm_email, norm_address
                FROM CustomerProfiles
                WHERE status = 'ACTIVE'
                """
            )
            matches = []
            for row in cursor.fetchall():
                score = 0
                if norm_phone and row[5] and norm_phone == row[5]:
                    score += 1
                if norm_email and row[6] and norm_email == row[6]:
                    score += 1
                if norm_address and row[7] and norm_address == row[7]:
                    score += 1
                if score >= 2:
                    matches.append({
                        "id": row[0],
                        "full_name": row[1],
                        "phone": row[2],
                        "email": row[3],
                        "address": row[4],
                        "score": score,
                    })
            matches.sort(key=lambda item: (-item["score"], item["id"]))
            return matches
        finally:
            conn.close()

    def parse_date_input(self, value):
        if not value:
            return None
        try:
            return datetime.strptime(value, "%Y-%m-%d").date().isoformat()
        except ValueError:
            return None

    def parse_float_input(self, value):
        if value is None:
            return None
        text = str(value).replace(",", "").strip()
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            return None

    def parse_int_input(self, value):
        if value is None:
            return None
        text = str(value).replace(",", "").strip()
        if not text:
            return None
        try:
            return int(text)
        except ValueError:
            return None

    def get_inventory_snapshot(self, year=None):
        stock_units = {}
        stock_costs = {}
        sales_units = {}
        conn = sqlite3.connect(FINANCIAL_DB)
        try:
            cursor = conn.cursor()
            stock_filter = ""
            stock_params = ()
            if year:
                stock_filter = "WHERE strftime('%Y', date) = ?"
                stock_params = (str(year),)
            cursor.execute(
                "SELECT product_sku, unit_in, unit_cost FROM Stock " + stock_filter,
                stock_params,
            )
            for sku, unit_in, unit_cost in cursor.fetchall():
                if not sku:
                    continue
                stock_units[sku] = stock_units.get(sku, 0) + (unit_in or 0)
                if unit_cost is not None:
                    stock_costs[sku] = unit_cost

            sales_filter = ""
            sales_params = ()
            if year:
                sales_filter = "WHERE strftime('%Y', sale_date) = ?"
                sales_params = (str(year),)
            cursor.execute(
                "SELECT product_sku, units_sold FROM Sales " + sales_filter,
                sales_params,
            )
            for sku, units_sold in cursor.fetchall():
                if not sku:
                    continue
                sales_units[sku] = sales_units.get(sku, 0) + (units_sold or 0)
        finally:
            conn.close()

        all_skus = set(stock_units.keys()) | set(sales_units.keys())
        snapshot = {}
        for sku in all_skus:
            stock_in = stock_units.get(sku, 0)
            sold = sales_units.get(sku, 0)
            snapshot[sku] = {
                "stock_in": stock_in,
                "sold": sold,
                "available": stock_in - sold,
                "unit_cost": stock_costs.get(sku, 0),
            }
        return snapshot

    def run_inventory_integrity_scan(self):
        """Return inventory integrity diagnostics for reconciliation and anomaly checks."""
        conn = sqlite3.connect(FINANCIAL_DB)
        try:
            cursor = conn.cursor()

            cursor.execute("SELECT sku FROM Products WHERE sku IS NOT NULL AND TRIM(sku) <> ''")
            product_skus = {str(row[0]).strip() for row in cursor.fetchall() if row and row[0]}

            cursor.execute("SELECT DISTINCT product_sku FROM Sales WHERE product_sku IS NOT NULL")
            sales_skus = {str(row[0]).strip() for row in cursor.fetchall() if row and row[0]}

            cursor.execute("SELECT DISTINCT product_sku FROM Stock WHERE product_sku IS NOT NULL")
            stock_skus = {str(row[0]).strip() for row in cursor.fetchall() if row and row[0]}

            cursor.execute(
                """
                SELECT product_sku, COALESCE(SUM(unit_in), 0)
                FROM Stock
                WHERE product_sku IS NOT NULL
                GROUP BY product_sku
                """
            )
            stock_in = {str(sku).strip(): qty or 0 for sku, qty in cursor.fetchall() if sku}

            cursor.execute(
                """
                SELECT product_sku, COALESCE(SUM(units_sold), 0)
                FROM Sales
                WHERE product_sku IS NOT NULL
                GROUP BY product_sku
                """
            )
            sold = {str(sku).strip(): qty or 0 for sku, qty in cursor.fetchall() if sku}

            all_skus = sorted(product_skus | set(stock_in.keys()) | set(sold.keys()))
            availability = []
            for sku in all_skus:
                available = (stock_in.get(sku, 0) or 0) - (sold.get(sku, 0) or 0)
                availability.append((sku, available))

            low_stock = [(sku, qty) for sku, qty in availability if 1 <= qty <= 2]
            critical_stock = [(sku, qty) for sku, qty in availability if qty <= 0]

            return {
                "product_skus": product_skus,
                "sales_skus": sales_skus,
                "stock_skus": stock_skus,
                "unknown_in_sales": sorted(sales_skus - product_skus),
                "unknown_in_stock": sorted(stock_skus - product_skus),
                "availability": availability,
                "low_stock": low_stock,
                "critical_stock": critical_stock,
            }
        finally:
            conn.close()

    def product_exists(self, sku, cursor=None):
        if not sku:
            return False
        if cursor is not None:
            cursor.execute("SELECT 1 FROM Products WHERE sku = ? LIMIT 1", (sku,))
            return cursor.fetchone() is not None
        conn = sqlite3.connect(FINANCIAL_DB)
        try:
            local_cursor = conn.cursor()
            local_cursor.execute("SELECT 1 FROM Products WHERE sku = ? LIMIT 1", (sku,))
            return local_cursor.fetchone() is not None
        finally:
            conn.close()

    def get_registered_product_skus(self):
        conn = sqlite3.connect(FINANCIAL_DB)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT sku
                FROM Products
                WHERE sku IS NOT NULL AND TRIM(sku) <> ''
                ORDER BY sku
                """
            )
            return [str(row[0]).strip() for row in cursor.fetchall() if row and row[0]]
        finally:
            conn.close()

    def get_product_image_storage_dir(self):
        target_dir = BASE_DIR / "artifacts" / "product_images"
        target_dir.mkdir(parents=True, exist_ok=True)
        return target_dir

    def get_supported_image_extensions(self):
        if Image is not None and ImageTk is not None:
            return {".png", ".jpg", ".jpeg", ".gif", ".bmp"}
        return {".png", ".gif", ".ppm", ".pgm"}

    def validate_image_extension(self, image_path):
        ext = Path(str(image_path or "")).suffix.lower()
        supported_ext = self.get_supported_image_extensions()
        if ext in supported_ext:
            return True, None

        if Image is None or ImageTk is None:
            return (
                False,
                "Image format not supported in this environment. Install Pillow for JPG/JPEG/BMP support.",
            )
        return (
            False,
            "Image must be a standard type: PNG, JPG, JPEG, GIF, BMP.",
        )

    def persist_product_image(self, sku, source_path):
        if not source_path:
            return None
        source = Path(source_path).expanduser().resolve()
        if not source.exists() or not source.is_file():
            raise ValueError("Image file does not exist")

        storage_dir = self.get_product_image_storage_dir()
        source_str = str(source).lower()
        if source_str.startswith(str(storage_dir).lower()):
            return str(source)

        safe_sku = re.sub(r"[^A-Za-z0-9_-]", "_", str(sku or "product").strip()) or "product"
        ext = source.suffix.lower()
        filename = f"{safe_sku}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}{ext}"
        destination = storage_dir / filename
        shutil.copy2(source, destination)
        return str(destination)

    def resolve_product_image_path(self, image_path):
        path_text = str(image_path or "").strip()
        if not path_text:
            return None

        candidate = Path(path_text)
        candidates = [candidate]
        if not candidate.is_absolute():
            candidates.append(BASE_DIR / candidate)

        for entry in candidates:
            try:
                resolved = entry.expanduser().resolve()
            except Exception:
                continue
            if resolved.exists() and resolved.is_file():
                return resolved
        return None

    def get_product_image_path_by_sku(self, sku, cursor=None):
        if not sku:
            return None
        if cursor is not None:
            cursor.execute("SELECT image_path FROM Products WHERE sku = ? LIMIT 1", (sku,))
            row = cursor.fetchone()
            return row[0] if row else None

        conn = sqlite3.connect(FINANCIAL_DB)
        try:
            local_cursor = conn.cursor()
            local_cursor.execute("SELECT image_path FROM Products WHERE sku = ? LIMIT 1", (sku,))
            row = local_cursor.fetchone()
            return row[0] if row else None
        finally:
            conn.close()

    def get_placeholder_image(self, size=(120, 120)):
        key = tuple(size)
        if key in self._placeholder_image_cache:
            return self._placeholder_image_cache[key]

        width, height = key
        image = tk.PhotoImage(width=width, height=height)
        image.put("#e2e8f0", to=(0, 0, width, height))
        image.put("#94a3b8", to=(1, 1, width - 1, 2))
        image.put("#94a3b8", to=(1, height - 2, width - 1, height - 1))
        image.put("#94a3b8", to=(1, 1, 2, height - 1))
        image.put("#94a3b8", to=(width - 2, 1, width - 1, height - 1))
        self._placeholder_image_cache[key] = image
        return image

    def get_product_preview_image(self, sku, size=(120, 120), image_path=None):
        final_path = image_path if image_path is not None else self.get_product_image_path_by_sku(sku)
        resolved = self.resolve_product_image_path(final_path)
        cache_key = (str(resolved) if resolved else "__placeholder__", tuple(size))
        if cache_key in self._product_image_cache:
            return self._product_image_cache[cache_key]

        if resolved is None:
            placeholder = self.get_placeholder_image(size)
            self._product_image_cache[cache_key] = placeholder
            return placeholder

        photo = None
        if Image is not None and ImageTk is not None:
            try:
                pil_image = Image.open(resolved)
                pil_image.thumbnail(size, Image.LANCZOS)
                canvas = Image.new("RGBA", size, (241, 245, 249, 255))
                offset_x = max(0, (size[0] - pil_image.size[0]) // 2)
                offset_y = max(0, (size[1] - pil_image.size[1]) // 2)
                if pil_image.mode in ("RGBA", "LA"):
                    canvas.paste(pil_image, (offset_x, offset_y), pil_image)
                else:
                    canvas.paste(pil_image, (offset_x, offset_y))
                photo = ImageTk.PhotoImage(canvas)
            except Exception:
                photo = None

        if photo is None:
            try:
                raw = tk.PhotoImage(file=str(resolved))
                width = max(1, raw.width())
                height = max(1, raw.height())
                sample = max(1, int(max(width / size[0], height / size[1])))
                resized = raw.subsample(sample, sample)
                if resized.width() > size[0] and resized.width() > 1:
                    resized = resized.subsample(2, 1)
                if resized.height() > size[1] and resized.height() > 1:
                    resized = resized.subsample(1, 2)
                photo = resized
            except Exception:
                photo = self.get_placeholder_image(size)

        self._product_image_cache[cache_key] = photo
        return photo

    def ensure_sku_image_popup(self):
        if self._sku_image_popup and self._sku_image_popup.winfo_exists():
            return

        popup = tk.Toplevel(self.root)
        popup.withdraw()
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)
        popup.configure(bg="#111827")

        frame = tk.Frame(popup, bg="#111827", bd=1, relief="solid")
        frame.pack(fill="both", expand=True)
        image_label = tk.Label(frame, bg="#111827")
        image_label.pack(padx=6, pady=(6, 2))
        text_label = tk.Label(frame, bg="#111827", fg="#f8fafc", font=("Segoe UI", 8))
        text_label.pack(padx=6, pady=(0, 6))

        popup.bind("<Enter>", lambda event: self.cancel_sku_preview_hide())
        popup.bind("<Leave>", lambda event: self.schedule_sku_preview_hide())

        self._sku_image_popup = popup
        self._sku_image_label = image_label
        self._sku_image_text = text_label

    def cancel_sku_preview_hide(self):
        if self._sku_image_hide_after and self._sku_image_popup and self._sku_image_popup.winfo_exists():
            self._sku_image_popup.after_cancel(self._sku_image_hide_after)
        self._sku_image_hide_after = None

    def hide_sku_preview(self):
        self.cancel_sku_preview_hide()
        if self._sku_image_popup and self._sku_image_popup.winfo_exists():
            self._sku_image_popup.withdraw()

    def schedule_sku_preview_hide(self, delay_ms=220):
        self.cancel_sku_preview_hide()
        if self._sku_image_popup and self._sku_image_popup.winfo_exists():
            self._sku_image_hide_after = self._sku_image_popup.after(delay_ms, self.hide_sku_preview)

    def show_sku_preview(self, sku, x, y, image_path=None):
        sku_text = str(sku or "").strip()
        if not sku_text:
            self.hide_sku_preview()
            return

        self.ensure_sku_image_popup()
        self.cancel_sku_preview_hide()
        preview = self.get_product_preview_image(sku_text, (128, 128), image_path=image_path)
        self._sku_image_label.configure(image=preview)
        self._sku_image_label.image = preview
        self._sku_image_text.configure(text=f"SKU: {sku_text}")
        self._sku_image_popup.geometry(f"150x162+{int(x) + 16}+{int(y) + 16}")
        self._sku_image_popup.deiconify()
        self._sku_image_popup.lift()

    def bind_widget_sku_preview(self, widget, sku_provider, image_path_provider=None):
        def show(event):
            try:
                sku_value = sku_provider() if callable(sku_provider) else ""
            except Exception:
                sku_value = ""
            try:
                image_value = image_path_provider() if callable(image_path_provider) else None
            except Exception:
                image_value = None
            self.show_sku_preview(sku_value, event.x_root, event.y_root, image_path=image_value)

        widget.bind("<Enter>", show)
        widget.bind("<Motion>", show)
        widget.bind("<Leave>", lambda event: self.schedule_sku_preview_hide())

    def stock_alert_level(self, available_units):
        units = self.parse_int_input(available_units)
        units = units if units is not None else 0
        if units <= 0:
            return "critical"
        if units <= 2:
            return "low"
        return "ok"

    def submit_pending_entry(self, entry_type, payload):
        """Submit a pending entry for approval"""
        conn = sqlite3.connect(FINANCIAL_DB)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO PendingEntries (entry_type, payload, status, created_by)
                VALUES (?, ?, 'PENDING', ?)
                """,
                (entry_type, json.dumps(payload), self.current_user['user_id']),
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def can_edit_financial_data(self):
        return PERMISSIONS.get(self.current_level, {}).get('financial_data') == 'edit'

    def is_financial_view_only(self):
        return PERMISSIONS.get(self.current_level, {}).get('financial_data') == 'view'

    def can_add_user_level(self, target_level):
        allowed_levels = PERMISSIONS.get(self.current_level, {}).get('can_add_users', [])
        return target_level in allowed_levels

    def can_remove_user_level(self, target_level):
        allowed_levels = PERMISSIONS.get(self.current_level, {}).get('can_remove_users', [])
        return target_level in allowed_levels

    def can_edit_user_level(self, target_level):
        if self.current_level == 3:
            return target_level in {1, 2}
        if self.current_level == 4:
            return target_level in {1, 2, 3, 4}
        return False

    def get_security_user_record(self, user_id):
        conn = sqlite3.connect(SECURITY_DB)
        try:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def validate_password_policy(self, password):
        password = str(password or "")
        if len(password) < 10:
            return "Password must be at least 10 characters long."
        if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
            return "Password must contain both letters and numbers."
        return None

    def refresh_current_user_profile(self):
        if not self.current_user:
            return
        refreshed = self.get_security_user_record(self.current_user['user_id'])
        if not refreshed:
            return
        self.current_user = refreshed
        self.current_level = refreshed['security_level']
        if self.user_info_label is not None:
            user_info = f"{self.current_user['first_name']} {self.current_user['last_name']} ({SECURITY_LEVELS.get(self.current_level, 'Unknown')})"
            self.user_info_label.configure(text=user_info)

    def can_request_sales_log_edit(self):
        return self.current_level in {2, 3, 4} and self.can_edit_financial_data()

    def can_request_stock_log_edit(self):
        return self.current_level in {2, 3, 4} and self.can_edit_financial_data()

    def can_request_cost_log_edit(self):
        return self.current_level in {2, 3, 4} and self.can_edit_financial_data()

    def get_user_security_level(self, user_id):
        conn = sqlite3.connect(SECURITY_DB)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT security_level FROM Users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            return int(row[0]) if row and row[0] is not None else None
        finally:
            conn.close()

    def validate_sales_edit_approval_permission(self, submitter_user_id):
        if submitter_user_id == self.current_user['user_id']:
            raise ValueError("Sales edit request cannot be self-approved.")

        submitter_level = self.get_user_security_level(submitter_user_id)
        approver_level = self.current_level
        if submitter_level is None:
            raise ValueError("Submitter not found for Sales edit request.")

        if submitter_level == 2:
            if approver_level not in {3, 4}:
                raise ValueError("Only Level 3 or 4 can approve Sales edits submitted by Level 2.")
            return
        if submitter_level == 3:
            if approver_level != 4:
                raise ValueError("Only Level 4 can approve Sales edits submitted by Level 3.")
            return
        if submitter_level == 4:
            if approver_level != 4:
                raise ValueError("Only a different Level 4 user can approve Sales edits submitted by Level 4.")
            return
        raise ValueError("Sales edit approvals support submitters at Level 2, 3, or 4 only.")

    def validate_stock_edit_approval_permission(self, submitter_user_id):
        if submitter_user_id == self.current_user['user_id']:
            raise ValueError("Stock edit request cannot be self-approved.")

        submitter_level = self.get_user_security_level(submitter_user_id)
        approver_level = self.current_level
        if submitter_level is None:
            raise ValueError("Submitter not found for Stock edit request.")

        if submitter_level == 2:
            if approver_level not in {3, 4}:
                raise ValueError("Only Level 3 or 4 can approve Stock edits submitted by Level 2.")
            return
        if submitter_level == 3:
            if approver_level != 4:
                raise ValueError("Only Level 4 can approve Stock edits submitted by Level 3.")
            return
        if submitter_level == 4:
            if approver_level != 4:
                raise ValueError("Only a different Level 4 user can approve Stock edits submitted by Level 4.")
            return
        raise ValueError("Stock edit approvals support submitters at Level 2, 3, or 4 only.")

    def validate_cost_edit_approval_permission(self, submitter_user_id):
        if submitter_user_id == self.current_user['user_id']:
            raise ValueError("Cost edit request cannot be self-approved.")

        submitter_level = self.get_user_security_level(submitter_user_id)
        approver_level = self.current_level
        if submitter_level is None:
            raise ValueError("Submitter not found for Cost edit request.")

        if submitter_level == 2:
            if approver_level not in {3, 4}:
                raise ValueError("Only Level 3 or 4 can approve Cost edits submitted by Level 2.")
            return
        if submitter_level == 3:
            if approver_level != 4:
                raise ValueError("Only Level 4 can approve Cost edits submitted by Level 3.")
            return
        if submitter_level == 4:
            if approver_level != 4:
                raise ValueError("Only a different Level 4 user can approve Cost edits submitted by Level 4.")
            return
        raise ValueError("Cost edit approvals support submitters at Level 2, 3, or 4 only.")

    def validate_pending_entry_approval_permission(self, entry_type, submitter_user_id):
        if self.current_level not in {2, 3, 4}:
            raise ValueError("Only Level 2, 3, or 4 can approve pending entries.")
        if entry_type == "SalesEdit":
            self.validate_sales_edit_approval_permission(submitter_user_id)
            return
        if entry_type == "StockEdit":
            self.validate_stock_edit_approval_permission(submitter_user_id)
            return
        if entry_type == "CostEdit":
            self.validate_cost_edit_approval_permission(submitter_user_id)
            return
        if submitter_user_id == self.current_user['user_id']:
            raise ValueError("Pending entry cannot be self-approved.")

    def get_sales_row_by_id(self, sale_id, cursor=None):
        should_close = cursor is None
        conn = None
        if should_close:
            conn = sqlite3.connect(FINANCIAL_DB)
            cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT id, sale_date, order_id, channel, product_sku, units_sold, unit_price,
                      gross_sales, vat_rate, vat_amount, service_fee, shipping_fee, note,
                      approved_by, approved_at
                FROM Sales
                WHERE id = ?
                """,
                (sale_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "id": row[0],
                "sale_date": row[1],
                "order_id": row[2],
                "channel": row[3],
                "product_sku": row[4],
                "units_sold": row[5],
                "unit_price": row[6],
                "gross_sales": row[7],
                "vat_rate": row[8],
                "vat_amount": row[9],
                "service_fee": row[10],
                "shipping_fee": row[11],
                "note": row[12],
                "approved_by": row[13],
                "approved_at": row[14],
            }
        finally:
            if should_close and conn is not None:
                conn.close()

    def get_stock_row_by_id(self, stock_id, cursor=None):
        should_close = cursor is None
        conn = None
        if should_close:
            conn = sqlite3.connect(FINANCIAL_DB)
            cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT id, date, product_sku, unit_cost, current_unit_price, unit_in,
                       tax_rate, tax_amount, total, note, approved_by, approved_at
                FROM Stock
                WHERE id = ?
                """,
                (stock_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "id": row[0],
                "date": row[1],
                "product_sku": row[2],
                "unit_cost": row[3],
                "current_unit_price": row[4],
                "unit_in": row[5],
                "tax_rate": row[6],
                "tax_amount": row[7],
                "total": row[8],
                "note": row[9],
                "approved_by": row[10],
                "approved_at": row[11],
            }
        finally:
            if should_close and conn is not None:
                conn.close()

    def get_cost_row_by_id(self, cost_id, cursor=None):
        should_close = cursor is None
        conn = None
        if should_close:
            conn = sqlite3.connect(FINANCIAL_DB)
            cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT id, cost_type, cost_date, amount, vat_rate, vat_amount, note
                FROM Costs
                WHERE id = ?
                """,
                (cost_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "id": row[0],
                "cost_type": row[1],
                "cost_date": row[2],
                "amount": row[3],
                "vat_rate": row[4],
                "vat_amount": row[5],
                "note": row[6],
            }
        finally:
            if should_close and conn is not None:
                conn.close()

    def show_login(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        self._login_images = []  # keep PIL references alive

        outer = tk.Frame(self.root, bg="#f0f0f0")
        outer.pack(expand=True, fill="both")

        card = tk.Frame(outer, bg="#ffffff", bd=0,
                        highlightbackground="#1e3a5f", highlightthickness=2)
        card.place(relx=0.5, rely=0.5, anchor="center")

        # ── Logo row ──────────────────────────────────────────────────────────
        logo_frame = tk.Frame(card, bg="#ffffff")
        logo_frame.pack(pady=(28, 10), padx=48)

        logo_shown = False
        for logo_file in ["Logo.png", "Safefire.png"]:
            logo_path = BASE_DIR / "Logo" / logo_file
            if Image and logo_path.exists():
                try:
                    img = Image.open(logo_path).convert("RGBA")
                    h = 80
                    w = int(img.width * h / img.height)
                    img = img.resize((w, h), Image.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                    self._login_images.append(photo)
                    tk.Label(logo_frame, image=photo, bg="#ffffff").pack(side="left", padx=8)
                    logo_shown = True
                except Exception:
                    pass

        if not logo_shown:
            tk.Label(logo_frame, text="Vicinity Safety",
                     font=("Segoe UI", 22, "bold"), bg="#ffffff", fg="#1e3a5f").pack()

        # ── Sub-title ─────────────────────────────────────────────────────────
        tk.Label(card, text="Financial Management System",
                 font=("Segoe UI", 13, "bold"), bg="#ffffff", fg="#1e3a5f").pack(pady=(0, 14))

        tk.Frame(card, bg="#d1d5db", height=1).pack(fill="x", padx=32)

        # ── Input fields ──────────────────────────────────────────────────────
        input_frame = tk.Frame(card, bg="#ffffff")
        input_frame.pack(pady=(18, 4), padx=48)

        tk.Label(input_frame, text="Username", font=("Segoe UI", 9),
                 bg="#ffffff", fg="#374151").grid(row=0, column=0, sticky="w", pady=(0, 2))
        username_entry = tk.Entry(input_frame, width=30, font=("Segoe UI", 10),
                                  bd=1, relief="solid", fg="#0f172a")
        username_entry.grid(row=1, column=0, pady=(0, 12), ipady=5)

        tk.Label(input_frame, text="Password", font=("Segoe UI", 9),
                 bg="#ffffff", fg="#374151").grid(row=2, column=0, sticky="w", pady=(0, 2))
        password_entry = tk.Entry(input_frame, show="*", width=30, font=("Segoe UI", 10),
                                  bd=1, relief="solid", fg="#0f172a")
        password_entry.grid(row=3, column=0, pady=(0, 16), ipady=5)

        def attempt_login():
            if not self.startup_checks_complete:
                messagebox.showwarning("Startup In Progress",
                                       "Startup checks are still running. Please try again in a moment.")
                return
            if self.startup_check_errors:
                messagebox.showerror("Startup Check Failed",
                                     "Resolve startup schema issues before logging in.")
                return
            username = username_entry.get()
            password = password_entry.get()
            if self.authenticate(username, password):
                self.log_action("LOGIN", f"User {username} logged in successfully")
                self.show_dashboard()
            else:
                messagebox.showerror("Login Failed", "Invalid username or password")

        tk.Button(
            input_frame, text="Login", command=attempt_login,
            bg=self.ui_palette["accent"], fg="white",
            font=("Segoe UI", 11, "bold"), width=28, height=2,
            relief="flat", cursor="hand2",
            activebackground="#0b8a89", activeforeground="white",
        ).grid(row=4, column=0, pady=(0, 4))

        password_entry.bind('<Return>', lambda e: attempt_login())
        username_entry.focus_set()

        # ── Startup status ────────────────────────────────────────────────────
        status_frame = tk.Frame(card, bg="#ffffff")
        status_frame.pack(pady=(4, 24))
        self._startup_status_label = tk.Label(
            status_frame,
            text="Initializing\u2026",
            font=("Segoe UI", 8, "italic"),
            bg="#ffffff", fg="#94a3b8",
        )
        self._startup_status_label.pack()

    def authenticate(self, username, password):
        try:
            conn = sqlite3.connect(SECURITY_DB)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Users WHERE username = ?", (username,))
            user = cursor.fetchone()
            conn.close()

            if user and bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
                self.current_user = dict(user)
                self.current_level = user['security_level']
                return True
            return False
        except Exception as e:
            print(f"Authentication error: {e}")
            return False

    def _update_sidebar_highlight(self, active_page):
        for page_key, btn in getattr(self, "sidebar_buttons", {}).items():
            if page_key == active_page:
                btn.config(bg=self.ui_palette["accent"], fg="white")
            else:
                btn.config(bg=self.ui_palette["sidebar_button"], fg="white")

    def _navigate_to(self, page_name):
        page_map = {
            "Dashboard": self.show_dashboard_content,
            "Financial Data": self.show_financial_data,
            "Finance Report": self.show_business_finance_report,
            "POS Entry": self.show_financial_entry,
            "Approval": self.show_approval_view,
            "User Management": self.show_user_management,
            "Audit Logs": self.show_audit_logs,
            "Governance": self.show_governance,
        }
        if page_name in page_map:
            self._update_sidebar_highlight(page_name)
            page_map[page_name]()

    def _go_to_approvals(self):
        self._navigate_to("Approval")

    def show_dashboard(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        self.root.configure(bg=self.ui_palette["bg"])

        top_bar = tk.Frame(self.root, bg=self.ui_palette["header"], height=60)
        top_bar.pack(fill="x")
        top_bar.pack_propagate(False)

        tk.Label(top_bar, text="Vicinity Safety Financial System",
                font=("Segoe UI", 15, "bold"), bg=self.ui_palette["header"], fg="white").pack(
            side="left", padx=20, pady=15
        )

        user_info = f"{self.current_user['first_name']} {self.current_user['last_name']} ({SECURITY_LEVELS.get(self.current_level, 'Unknown')})"
        self.user_info_label = tk.Label(top_bar, text=user_info, bg=self.ui_palette["header"], fg="#e2e8f0",
             font=("Segoe UI", 10))
        self.user_info_label.pack(side="right", padx=20)

        tk.Button(
            top_bar,
            text="Logout",
            command=self.logout,
            bg=self.ui_palette["danger"],
            fg="white",
            relief="flat",
            width=10,
        ).pack(side="right", padx=10)

        main_container = tk.Frame(self.root, bg=self.ui_palette["bg"])
        main_container.pack(expand=True, fill="both")

        sidebar = tk.Frame(main_container, bg=self.ui_palette["sidebar"], width=200)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        tk.Label(
            sidebar,
            text="MENU",
            bg=self.ui_palette["sidebar"],
            fg="#cbd5e1",
            font=("Segoe UI", 11, "bold"),
        ).pack(pady=20)

        menu_items = [
            ("Dashboard", "Dashboard", self.show_dashboard_content),
            ("Financial Data", "Financial Data", self.show_financial_data),
            ("Finance Report", "Finance Report", self.show_business_finance_report),
            ("POS Entry", "POS Entry", self.show_financial_entry),
            ("Approval", "Approval", self.show_approval_view),
            ("User Management", "User Management", self.show_user_management),
            ("Audit Logs", "Audit Logs", self.show_audit_logs),
        ]

        if self.current_level >= 4:
            menu_items.append(("Governance", "Governance", self.show_governance))

        self.sidebar_buttons = {}

        for display_name, page_key, command in menu_items:
            def _make_cmd(pkey, cmd):
                def wrapper():
                    self._update_sidebar_highlight(pkey)
                    cmd()
                return wrapper
            btn = tk.Button(
                sidebar,
                text=display_name,
                command=_make_cmd(page_key, command),
                bg=self.ui_palette["sidebar_button"],
                fg="white",
                relief="flat",
                width=20,
                height=2,
            )
            btn.pack(pady=5, padx=10)
            self.sidebar_buttons[page_key] = btn

        self.content_area = tk.Frame(main_container, bg=self.ui_palette["bg"])
        self.content_area.pack(side="right", expand=True, fill="both")

        self._update_sidebar_highlight("Dashboard")
        self.show_dashboard_content()

    def show_dashboard_content(self):
        for widget in self.content_area.winfo_children():
            widget.destroy()

        today = datetime.now()
        today_str = today.strftime("%B %d, %Y")
        current_year = str(today.year)
        username = f"{self.current_user.get('first_name', '')} {self.current_user.get('last_name', '')}".strip()
        role_name = SECURITY_LEVELS.get(self.current_level, "Unknown")

        # ── Row 1: Welcome Header ─────────────────────────────────────────────
        header_bar = tk.Frame(
            self.content_area, bg=self.ui_palette["surface"],
            highlightbackground=self.ui_state_colors["neutral_border"], highlightthickness=1,
        )
        header_bar.pack(fill="x", padx=16, pady=(16, 8))
        tk.Label(header_bar, text=f"Welcome back, {username}",
                 font=("Segoe UI", 16, "bold"), bg=self.ui_palette["surface"],
                 fg=self.ui_palette["text"]).pack(side="left", padx=16, pady=12)
        tk.Label(header_bar, text=f"{role_name}  \u00b7  {today_str}",
                 font=("Segoe UI", 10), bg=self.ui_palette["surface"],
                 fg=self.ui_palette["muted"]).pack(side="right", padx=16, pady=12)

        # ── Row 2: KPI Cards ──────────────────────────────────────────────────
        kpi_row = tk.Frame(self.content_area, bg=self.ui_palette["bg"])
        kpi_row.pack(fill="x", padx=16, pady=8)

        pending_count = 0
        ytd_revenue = 0.0
        outstanding_ap = 0.0
        inventory_val = 0.0
        try:
            conn = sqlite3.connect(FINANCIAL_DB)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM PendingEntries WHERE status = 'PENDING'")
            row = cursor.fetchone()
            pending_count = row[0] if row else 0
            cursor.execute(
                "SELECT COALESCE(SUM(gross_sales), 0) FROM Sales WHERE strftime('%Y', sale_date) = ?",
                (current_year,),
            )
            row = cursor.fetchone()
            ytd_revenue = row[0] if row else 0.0
            conn.close()
        except Exception:
            pass
        try:
            outstanding_ap = self.get_accounts_payable_as_of(today.strftime("%Y-%m-%d"))
        except Exception:
            pass
        try:
            snapshot = self.get_inventory_snapshot()
            for item in snapshot.values():
                on_hand = item.get("available", 0)
                if on_hand > 0:
                    inventory_val += on_hand * item.get("unit_cost", 0.0)
        except Exception:
            pass

        def _fmt(v):
            return f"{int(round(v)):,} VND"

        kpi_cards = [
            ("Pending Approvals", str(pending_count),
             "#dc2626" if pending_count > 0 else "#166534",
             lambda: self._navigate_to("Approval")),
            ("YTD Revenue", _fmt(ytd_revenue), self.ui_palette["accent"], None),
            ("Outstanding Payables", _fmt(outstanding_ap),
             "#dc2626" if outstanding_ap > 0 else self.ui_palette["text"], None),
            ("Inventory Value", _fmt(inventory_val), self.ui_palette["accent_alt"], None),
        ]

        for title, value, color, nav_fn in kpi_cards:
            kcard = tk.Frame(
                kpi_row, bg=self.ui_palette["surface"], bd=0,
                highlightbackground=self.ui_state_colors["neutral_border"], highlightthickness=1,
                cursor="hand2" if nav_fn else "",
            )
            kcard.pack(side="left", padx=8, pady=4, fill="y", expand=True)
            tk.Label(kcard, text=title, font=("Segoe UI", 9),
                     bg=self.ui_palette["surface"], fg=self.ui_palette["muted"],
                     ).pack(pady=(14, 2), padx=20, anchor="w")
            tk.Label(kcard, text=value, font=("Segoe UI", 18, "bold"),
                     bg=self.ui_palette["surface"], fg=color).pack(padx=20, anchor="w")
            if nav_fn:
                lnk = tk.Label(kcard, text="View \u2192", font=("Segoe UI", 8),
                               bg=self.ui_palette["surface"], fg=self.ui_palette["accent"],
                               cursor="hand2")
                lnk.pack(pady=(2, 14), padx=20, anchor="w")
                for widget in (kcard, lnk):
                    widget.bind("<Button-1>", lambda e, fn=nav_fn: fn())
            else:
                tk.Frame(kcard, height=14, bg=self.ui_palette["surface"]).pack()

        # ── Row 3: Quick Actions ───────────────────────────────────────────────
        action_row = tk.Frame(self.content_area, bg=self.ui_palette["bg"])
        action_row.pack(fill="x", padx=16, pady=8)

        quick_actions = [
            ("+  New POS Entry", self.ui_palette["accent"], self.show_financial_entry),
            ("\u23f3  View Pending Approvals", "#d97706", self._go_to_approvals),
            ("\U0001f4ca  Open Finance Report", self.ui_palette["accent_alt"], self.show_business_finance_report),
        ]
        for label, color, cmd in quick_actions:
            tk.Button(
                action_row, text=label, command=cmd,
                bg=color, fg="white", font=("Segoe UI", 10, "bold"),
                relief="flat", padx=16, pady=8, cursor="hand2",
                activebackground=color, activeforeground="white",
            ).pack(side="left", padx=8)

        tk.Frame(self.content_area, bg=self.ui_state_colors["neutral_border"], height=1,
                 ).pack(fill="x", padx=16, pady=(16, 4))

        # ── Permissions (retained) ────────────────────────────────────────────
        tk.Label(self.content_area, text="Your Permissions:",
                 bg=self.ui_palette["bg"], font=("Segoe UI", 11, "bold"),
                 fg=self.ui_palette["text"]).pack(pady=(8, 4), padx=16, anchor="w")

        perms_frame = tk.Frame(self.content_area, bg=self.ui_palette["bg"])
        perms_frame.pack(pady=4, padx=16, anchor="w")

        perm_text = []
        if self.is_financial_view_only():
            perm_text.append("\u2713 View financial data (READ ONLY)")
        else:
            perm_text.append("\u2713 View & Edit financial data")
        can_add = PERMISSIONS.get(self.current_level, {}).get("can_add_users", [])
        if can_add:
            perm_text.append(f"\u2713 Add users: {', '.join([f'Level {l}' for l in can_add])}")
        can_remove = PERMISSIONS.get(self.current_level, {}).get("can_remove_users", [])
        if can_remove:
            perm_text.append(f"\u2713 Remove users: {', '.join([f'Level {l}' for l in can_remove])}")
        for perm in perm_text:
            tk.Label(perms_frame, text=perm, bg=self.ui_palette["bg"],
                     font=("Segoe UI", 10), anchor="w",
                     fg=self.ui_palette["text"]).pack(anchor="w", pady=2)

        if self.current_level in {3, 4, 5}:
            self.render_financial_statement(self.content_area)

        if self.current_level == 5:
            notice_text = "Level 5 (Police/Government) has READ-ONLY access to financial data for oversight purposes."
            tk.Label(self.content_area, text=notice_text, fg="#f97316", bg=self.ui_palette["bg"],
                     font=("Segoe UI", 10, "italic"), wraplength=600).pack(pady=12, padx=16, anchor="w")
        elif self.current_level >= 3:
            notice_text = "You have elevated privileges. Level 5 (Police/Government) access is immutable."
            tk.Label(self.content_area, text=notice_text, fg="#f97316", bg=self.ui_palette["bg"],
                     font=("Segoe UI", 10, "italic")).pack(pady=12, padx=16, anchor="w")

    def show_financial_data(self):
        for widget in self.content_area.winfo_children():
            widget.destroy()

        tk.Label(self.content_area, text="Financial Data",
            font=("Segoe UI", 18, "bold"), bg=self.ui_palette["bg"],
            fg=self.ui_palette["text"]).pack(pady=15)

        access_text = "Display Only"
        tk.Label(self.content_area, text=f"Access: {access_text}", bg=self.ui_palette["bg"],
            fg=self.ui_palette["muted"], font=("Segoe UI", 10, "italic")).pack(pady=5)

        notebook = ttk.Notebook(self.content_area, style="App.TNotebook")
        notebook.pack(expand=True, fill="both", padx=10, pady=10)

        self.create_summary_tab(notebook)
        self.create_taxation_tab(notebook)
        self.create_records_tab(notebook)
        self.create_stock_reports_tab(notebook)
        self.create_payables_tab(notebook)

    def get_quarter_date_bounds(self, year, quarter):
        year = int(year)
        quarter = int(quarter)
        if quarter == 1:
            return f"{year:04d}-01-01", f"{year:04d}-03-31"
        if quarter == 2:
            return f"{year:04d}-04-01", f"{year:04d}-06-30"
        if quarter == 3:
            return f"{year:04d}-07-01", f"{year:04d}-09-30"
        return f"{year:04d}-10-01", f"{year:04d}-12-31"

    def get_year_date_bounds(self, year):
        year = int(year)
        return f"{year:04d}-01-01", f"{year:04d}-12-31"

    def get_business_finance_quarters(self):
        conn = sqlite3.connect(FINANCIAL_DB)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                WITH all_dates AS (
                    SELECT sale_date AS d FROM Sales
                    UNION ALL SELECT cost_date AS d FROM Costs
                    UNION ALL SELECT date AS d FROM Stock
                    UNION ALL SELECT event_date AS d FROM Timeline
                )
                SELECT DISTINCT
                    CAST(strftime('%Y', d) AS INTEGER) AS y,
                    CAST(((CAST(strftime('%m', d) AS INTEGER) + 2) / 3) AS INTEGER) AS q
                FROM all_dates
                WHERE d IS NOT NULL
                  AND TRIM(d) <> ''
                  AND strftime('%Y', d) IS NOT NULL
                  AND strftime('%m', d) IS NOT NULL
                ORDER BY y DESC, q DESC
                """
            )
            rows = cursor.fetchall()
        finally:
            conn.close()

        if rows:
            return [(int(row[0]), int(row[1])) for row in rows if row[0] and row[1]]

        today = datetime.now().date()
        default_q = ((today.month - 1) // 3) + 1
        return [(today.year, default_q)]

    def fetch_weighted_unit_cost_by_sku_as_of(self, end_date):
        conn = sqlite3.connect(FINANCIAL_DB)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    product_sku,
                    COALESCE(SUM(unit_in), 0) AS total_units,
                    COALESCE(SUM(unit_in * unit_cost), 0) AS total_cost
                FROM Stock
                WHERE date <= ?
                GROUP BY product_sku
                """,
                (end_date,),
            )
            rows = cursor.fetchall()
            result = {}
            for sku, total_units, total_cost in rows:
                if not sku:
                    continue
                units = float(total_units or 0)
                if units <= 0:
                    result[str(sku)] = 0.0
                else:
                    result[str(sku)] = float(total_cost or 0) / units
            return result
        finally:
            conn.close()

    def fetch_inventory_snapshot_as_of(self, end_date):
        conn = sqlite3.connect(FINANCIAL_DB)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                WITH stock_totals AS (
                    SELECT product_sku, COALESCE(SUM(unit_in), 0) AS units_in
                    FROM Stock
                    WHERE date <= ?
                    GROUP BY product_sku
                ),
                sales_totals AS (
                    SELECT product_sku, COALESCE(SUM(units_sold), 0) AS units_sold
                    FROM Sales
                    WHERE sale_date <= ?
                    GROUP BY product_sku
                )
                SELECT st.product_sku,
                       COALESCE(st.units_in, 0) AS units_in,
                       COALESCE(sa.units_sold, 0) AS units_sold
                FROM stock_totals st
                LEFT JOIN sales_totals sa ON st.product_sku = sa.product_sku
                """,
                (end_date, end_date),
            )
            rows = cursor.fetchall()
        finally:
            conn.close()

        weighted_cost = self.fetch_weighted_unit_cost_by_sku_as_of(end_date)
        total_units = 0
        total_value = 0.0
        sku_rows = []
        for sku, units_in, units_sold in rows:
            on_hand = int((units_in or 0) - (units_sold or 0))
            if on_hand <= 0:
                continue
            unit_cost = float(weighted_cost.get(str(sku), 0.0))
            line_value = on_hand * unit_cost
            total_units += on_hand
            total_value += line_value
            sku_rows.append(
                {
                    "sku": str(sku),
                    "on_hand": on_hand,
                    "unit_cost": unit_cost,
                    "value": line_value,
                }
            )

        return {
            "total_units": total_units,
            "total_value": total_value,
            "rows": sku_rows,
        }

    def fetch_income_statement_for_range(self, start_date, end_date):
        statement = {
            "revenue": 0.0,
            "service_fee": 0.0,
            "shipping_fee": 0.0,
            "sales_vat": 0.0,
            "cogs": 0.0,
            "operating_expenses": 0.0,
            "expense_vat": 0.0,
            "gross_profit": 0.0,
            "operating_profit": 0.0,
            "net_income": 0.0,
            "warnings": [],
        }

        weighted_cost = self.fetch_weighted_unit_cost_by_sku_as_of(end_date)

        conn = sqlite3.connect(FINANCIAL_DB)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    COALESCE(SUM(gross_sales), 0),
                    COALESCE(SUM(service_fee), 0),
                    COALESCE(SUM(shipping_fee), 0),
                    COALESCE(SUM(vat_amount), 0)
                FROM Sales
                WHERE sale_date BETWEEN ? AND ?
                """,
                (start_date, end_date),
            )
            row = cursor.fetchone()
            if row:
                statement["revenue"] = float(row[0] or 0)
                statement["service_fee"] = float(row[1] or 0)
                statement["shipping_fee"] = float(row[2] or 0)
                statement["sales_vat"] = float(row[3] or 0)

            cursor.execute(
                """
                SELECT product_sku, COALESCE(SUM(units_sold), 0)
                FROM Sales
                WHERE sale_date BETWEEN ? AND ?
                GROUP BY product_sku
                """,
                (start_date, end_date),
            )
            for sku, units_sold in cursor.fetchall():
                units = float(units_sold or 0)
                if units <= 0:
                    continue
                sku_key = str(sku or "").strip()
                unit_cost = float(weighted_cost.get(sku_key, 0.0))
                if unit_cost <= 0 and sku_key:
                    statement["warnings"].append(f"No stock cost found for sold SKU {sku_key}.")
                statement["cogs"] += units * unit_cost

            cursor.execute(
                """
                SELECT COALESCE(SUM(amount), 0), COALESCE(SUM(COALESCE(vat_amount, 0)), 0)
                FROM Costs
                WHERE cost_date BETWEEN ? AND ?
                """,
                (start_date, end_date),
            )
            row = cursor.fetchone()
            if row:
                statement["operating_expenses"] = float(row[0] or 0)
                statement["expense_vat"] = float(row[1] or 0)
        finally:
            conn.close()

        statement["gross_profit"] = statement["revenue"] - statement["cogs"]
        statement["operating_profit"] = statement["gross_profit"] - statement["operating_expenses"]
        statement["net_income"] = statement["operating_profit"]
        return statement

    def fetch_quarterly_income_statement(self, year, quarter):
        start_date, end_date = self.get_quarter_date_bounds(year, quarter)
        payload = self.fetch_income_statement_for_range(start_date, end_date)
        payload["start_date"] = start_date
        payload["end_date"] = end_date
        return payload

    def fetch_annual_income_statement(self, year):
        start_date, end_date = self.get_year_date_bounds(year)
        payload = self.fetch_income_statement_for_range(start_date, end_date)
        payload["start_date"] = start_date
        payload["end_date"] = end_date
        return payload

    def fetch_balance_sheet_for_range(self, start_date, end_date):
        inventory = self.fetch_inventory_snapshot_as_of(end_date)
        income_cumulative = self.fetch_income_statement_for_range("1900-01-01", end_date)

        conn = sqlite3.connect(FINANCIAL_DB)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT COALESCE(SUM(vat_amount), 0)
                FROM Sales
                WHERE sale_date <= ?
                """,
                (end_date,),
            )
            sales_vat_total = float((cursor.fetchone() or [0])[0] or 0)

            cursor.execute(
                """
                SELECT COALESCE(SUM(COALESCE(vat_amount, 0)), 0)
                FROM Costs
                WHERE cost_date <= ?
                """,
                (end_date,),
            )
            costs_vat_total = float((cursor.fetchone() or [0])[0] or 0)

            cursor.execute(
                """
                SELECT COALESCE(SUM(tax_amount), 0)
                FROM Stock
                WHERE date <= ?
                """,
                (end_date,),
            )
            stock_vat_total = float((cursor.fetchone() or [0])[0] or 0)
        finally:
            conn.close()

        vat_payable = max(0.0, sales_vat_total - (costs_vat_total + stock_vat_total))
        accounts_payable = self.get_accounts_payable_as_of(end_date)
        total_assets = float(inventory["total_value"])
        total_liabilities = vat_payable + accounts_payable
        retained_earnings = float(income_cumulative["net_income"])
        owner_equity = total_assets - total_liabilities - retained_earnings
        total_equity = owner_equity + retained_earnings
        equation_delta = total_assets - (total_liabilities + total_equity)

        warnings = []
        if abs(equation_delta) > 0.01:
            warnings.append("Balance Sheet equation mismatch detected.")
        warnings.extend(income_cumulative.get("warnings", []))

        return {
            "start_date": start_date,
            "end_date": end_date,
            "inventory_units": inventory["total_units"],
            "inventory_value": inventory["total_value"],
            "vat_payable": vat_payable,
            "accounts_payable": accounts_payable,
            "total_assets": total_assets,
            "total_liabilities": total_liabilities,
            "retained_earnings": retained_earnings,
            "owner_equity": owner_equity,
            "total_equity": total_equity,
            "equation_delta": equation_delta,
            "warnings": warnings,
        }

    def fetch_quarterly_balance_sheet(self, year, quarter):
        start_date, end_date = self.get_quarter_date_bounds(year, quarter)
        return self.fetch_balance_sheet_for_range(start_date, end_date)

    def fetch_annual_balance_sheet(self, year):
        start_date, end_date = self.get_year_date_bounds(year)
        return self.fetch_balance_sheet_for_range(start_date, end_date)

    def fetch_cash_flow_for_range(self, start_date, end_date, period_label="period"):
        conn = sqlite3.connect(FINANCIAL_DB)
        try:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT COALESCE(SUM(cash_in), 0), COALESCE(SUM(cash_out), 0)
                FROM Timeline
                WHERE event_date BETWEEN ? AND ?
                """,
                (start_date, end_date),
            )
            row = cursor.fetchone() or (0, 0)
            cash_in = float(row[0] or 0)
            cash_out = float(row[1] or 0)

            cursor.execute(
                """
                SELECT balance
                FROM Timeline
                WHERE event_date < ?
                ORDER BY event_date DESC, id DESC
                LIMIT 1
                """,
                (start_date,),
            )
            row = cursor.fetchone()
            beginning_cash = float(row[0]) if row and row[0] is not None else 0.0

            if beginning_cash == 0.0:
                try:
                    ob = self.get_opening_balance_for_year(int(start_date[:4]))
                    beginning_cash = float(ob.get("opening_cash", 0.0))
                except Exception:
                    pass

            cursor.execute(
                """
                SELECT balance
                FROM Timeline
                WHERE event_date <= ?
                ORDER BY event_date DESC, id DESC
                LIMIT 1
                """,
                (end_date,),
            )
            row = cursor.fetchone()
            ending_cash = float(row[0]) if row and row[0] is not None else (beginning_cash + cash_in - cash_out)

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM Timeline
                WHERE event_date BETWEEN ? AND ?
                """,
                (start_date, end_date),
            )
            events_count = int((cursor.fetchone() or [0])[0] or 0)
        finally:
            conn.close()

        net_cash = cash_in - cash_out
        warnings = []
        if events_count == 0:
            warnings.append(f"No Timeline cash events found for this {period_label}.")

        return {
            "start_date": start_date,
            "end_date": end_date,
            "cash_in": cash_in,
            "cash_out": cash_out,
            "net_cash": net_cash,
            "beginning_cash": beginning_cash,
            "ending_cash": ending_cash,
            "events_count": events_count,
            "warnings": warnings,
        }

    def fetch_quarterly_cash_flow(self, year, quarter):
        start_date, end_date = self.get_quarter_date_bounds(year, quarter)
        return self.fetch_cash_flow_for_range(start_date, end_date, period_label="quarter")

    def fetch_annual_cash_flow(self, year):
        start_date, end_date = self.get_year_date_bounds(year)
        return self.fetch_cash_flow_for_range(start_date, end_date, period_label="year")

    def fetch_vat_totals_as_of(self, end_date):
        conn = sqlite3.connect(FINANCIAL_DB)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT COALESCE(SUM(vat_amount), 0)
                FROM Sales
                WHERE sale_date <= ?
                """,
                (end_date,),
            )
            sales_vat = float((cursor.fetchone() or [0])[0] or 0)

            cursor.execute(
                """
                SELECT COALESCE(SUM(COALESCE(vat_amount, 0)), 0)
                FROM Costs
                WHERE cost_date <= ?
                """,
                (end_date,),
            )
            costs_vat = float((cursor.fetchone() or [0])[0] or 0)

            cursor.execute(
                """
                SELECT COALESCE(SUM(COALESCE(tax_amount, 0)), 0)
                FROM Stock
                WHERE date <= ?
                """,
                (end_date,),
            )
            stock_vat = float((cursor.fetchone() or [0])[0] or 0)
        finally:
            conn.close()

        deductible_vat = costs_vat + stock_vat
        payable_vat = max(0.0, sales_vat - deductible_vat)
        return {
            "sales_vat": sales_vat,
            "deductible_vat": deductible_vat,
            "costs_vat": costs_vat,
            "stock_vat": stock_vat,
            "payable_vat": payable_vat,
        }

    def estimate_credit_receivables_as_of(self, end_date):
        conn = sqlite3.connect(FINANCIAL_DB)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT COALESCE(SUM(gross_sales + COALESCE(vat_amount, 0)), 0)
                FROM Sales
                WHERE sale_date <= ?
                  AND LOWER(COALESCE(channel, '')) LIKE '%credit%'
                """,
                (end_date,),
            )
            return float((cursor.fetchone() or [0])[0] or 0)
        finally:
            conn.close()

    def fetch_cash_flow_breakdown_for_range(self, start_date, end_date):
        conn = sqlite3.connect(FINANCIAL_DB)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT COALESCE(event_name, ''), COALESCE(note, ''),
                       COALESCE(cash_in, 0), COALESCE(cash_out, 0)
                FROM Timeline
                WHERE event_date BETWEEN ? AND ?
                ORDER BY event_date ASC, id ASC
                """,
                (start_date, end_date),
            )
            rows = cursor.fetchall()
        finally:
            conn.close()

        financing_keywords = (
            "von", "capital", "owner", "equity", "phat hanh", "contribution", "gop von"
        )
        investing_keywords = (
            "dau tu", "investment", "asset", "tscd", "thanh ly", "xay dung", "fixed asset"
        )
        wages_keywords = ("luong", "salary", "payroll", "nhan vien", "wage")
        supplier_keywords = (
            "nha cung cap", "supplier", "vendor", "mua hang", "stock", "nhap hang", "purchase", "chi phi"
        )
        sales_keywords = ("sale", "ban hang", "customer", "receipt", "thu tien")

        def has_keyword(text, keywords):
            return any(word in text for word in keywords)

        breakdown = {
            "operating_sales_in": 0.0,
            "operating_other_in": 0.0,
            "operating_supplier_out": 0.0,
            "operating_wages_out": 0.0,
            "operating_other_out": 0.0,
            "investing_in": 0.0,
            "investing_out": 0.0,
            "financing_in": 0.0,
            "financing_out": 0.0,
            "uncategorized_events": 0,
        }

        for event_name, note, cash_in, cash_out in rows:
            event_text = f"{event_name} {note}".strip().lower()
            cash_in = float(cash_in or 0.0)
            cash_out = float(cash_out or 0.0)

            if has_keyword(event_text, financing_keywords):
                breakdown["financing_in"] += cash_in
                breakdown["financing_out"] += cash_out
                continue

            if has_keyword(event_text, investing_keywords):
                breakdown["investing_in"] += cash_in
                breakdown["investing_out"] += cash_out
                continue

            categorized = False
            if cash_in > 0:
                if has_keyword(event_text, sales_keywords):
                    breakdown["operating_sales_in"] += cash_in
                else:
                    breakdown["operating_other_in"] += cash_in
                categorized = True

            if cash_out > 0:
                if has_keyword(event_text, wages_keywords):
                    breakdown["operating_wages_out"] += cash_out
                    categorized = True
                elif has_keyword(event_text, supplier_keywords):
                    breakdown["operating_supplier_out"] += cash_out
                    categorized = True
                else:
                    breakdown["operating_other_out"] += cash_out
                    categorized = True

            if not categorized and (cash_in > 0 or cash_out > 0):
                breakdown["uncategorized_events"] += 1

        breakdown["operating_in"] = breakdown["operating_sales_in"] + breakdown["operating_other_in"]
        breakdown["operating_out"] = (
            breakdown["operating_supplier_out"]
            + breakdown["operating_wages_out"]
            + breakdown["operating_other_out"]
        )
        breakdown["operating_net"] = breakdown["operating_in"] - breakdown["operating_out"]
        breakdown["investing_net"] = breakdown["investing_in"] - breakdown["investing_out"]
        breakdown["financing_net"] = breakdown["financing_in"] - breakdown["financing_out"]
        breakdown["total_net"] = breakdown["operating_net"] + breakdown["investing_net"] + breakdown["financing_net"]
        return breakdown

    def fetch_annual_cash_flow_breakdown(self, year):
        start_date, end_date = self.get_year_date_bounds(year)
        return self.fetch_cash_flow_breakdown_for_range(start_date, end_date)

    def get_annual_export_checks(self, year):
        income = self.fetch_annual_income_statement(year)
        balance = self.fetch_annual_balance_sheet(year)
        cash = self.fetch_annual_cash_flow(year)
        cash_breakdown = self.fetch_annual_cash_flow_breakdown(year)
        vat = self.fetch_vat_totals_as_of(balance["end_date"])
        receivables = self.estimate_credit_receivables_as_of(balance["end_date"])
        opening = self.get_opening_balance_for_year(year)

        checks = []
        cash_ending = float(cash.get("ending_cash", 0.0))
        if cash_ending == 0.0:
            cash_ending = float(opening.get("opening_cash", 0.0))
        b01_assets = (
            cash_ending
            + receivables
            + float(opening.get("opening_receivables", 0.0))
            + float(balance.get("inventory_value", 0.0))
            + float(vat.get("deductible_vat", 0.0))
            + float(opening.get("opening_vat_deductible", 0.0))
        )
        b01_liabilities = float(balance.get("total_liabilities", 0.0)) + float(opening.get("opening_payables", 0.0))
        b01_retained = float(balance.get("retained_earnings", 0.0)) + float(opening.get("opening_retained_earnings", 0.0))
        ob_owner_capital = float(opening.get("opening_owner_capital", 0.0))
        b01_owner = ob_owner_capital if ob_owner_capital != 0.0 else (b01_assets - b01_liabilities - b01_retained)
        b01_equity = b01_owner + b01_retained
        b01_delta = b01_assets - (b01_liabilities + b01_equity)
        checks.append(("B01a equation delta", b01_delta, abs(b01_delta) <= 1.0))

        b03_net = float(cash_breakdown.get("total_net", 0.0))
        net_delta = float(cash.get("net_cash", 0.0)) - b03_net
        checks.append(("B03 net tie-out delta", net_delta, abs(net_delta) <= 1.0))

        roll_delta = float(cash.get("ending_cash", 0.0)) - (
            float(cash.get("beginning_cash", 0.0)) + float(cash.get("net_cash", 0.0))
        )
        checks.append(("Cash roll-forward delta", roll_delta, abs(roll_delta) <= 1.0))

        profit_delta = float(income.get("net_income", 0.0)) - float(balance.get("retained_earnings", 0.0))
        checks.append(("B02 vs retained earnings delta", profit_delta, abs(profit_delta) <= 1.0))

        active_adj = self.get_export_adjustments_for_year(year)
        if active_adj:
            adj_summary = ", ".join(f"{fc}-{lc}" for fc, lc in sorted(active_adj.keys()))
            checks.append((f"ADJUSTED lines ({len(active_adj)})", 0.0, True))
            checks.append((f"  -> {adj_summary[:120]}", 0.0, True))

        return checks

    def _asp_money(self, value):
        try:
            return f"{float(value or 0):,.0f}"
        except (TypeError, ValueError):
            return "0"

    def _append_asp_header(self, rows, form_code, report_title, period_text, text_adj=None):
        ta = text_adj or {}
        company_name = ta.get(("HEADER", "company", "company_name"), "CONG TY TNHH VICINITY SAFETY")
        company_address = ta.get(("HEADER", "company", "company_address"), "267 Nguyen Van Dau, Phuong Binh Loi Trung, Ho Chi Minh")
        period_text = ta.get((form_code, "header", "period_text"), period_text)
        rows.append([company_name])
        rows.append([company_address])
        rows.append([])
        rows.append([f"Mau so: {form_code}"])
        rows.append([report_title])
        rows.append([period_text])
        rows.append(["Don vi tinh: VND"])
        rows.append([])

    def build_annual_b01a_rows(self, year):
        annual = self.fetch_annual_balance_sheet(year)
        cash_annual = self.fetch_annual_cash_flow(year)
        vat_totals = self.fetch_vat_totals_as_of(annual["end_date"])
        receivables = self.estimate_credit_receivables_as_of(annual["end_date"])
        opening = self.get_opening_balance_for_year(year)
        text_adj = self.get_export_text_adjustments_for_year(year)
        period_text = f"Tai ngay 31 thang 12 nam {year}"
        rows = []
        self._append_asp_header(rows, "B01a-DNN", "BAO CAO TINH HINH TAI CHINH", period_text, text_adj)
        rows.append(["Chi tieu", "Ma so", "Thuyet minh", "So cuoi nam", "So dau nam"])

        cash_ending = float(cash_annual.get("ending_cash", 0.0))
        if cash_ending == 0.0:
            cash_ending = float(opening.get("opening_cash", 0.0))
        inventory = float(annual.get("inventory_value", 0.0))
        vat_asset = float(vat_totals.get("deductible_vat", 0.0)) + float(opening.get("opening_vat_deductible", 0.0))
        receivables = receivables + float(opening.get("opening_receivables", 0.0))
        liabilities = float(annual.get("total_liabilities", 0.0)) + float(opening.get("opening_payables", 0.0))
        retained = float(annual.get("retained_earnings", 0.0)) + float(opening.get("opening_retained_earnings", 0.0))
        ob_owner_capital = float(opening.get("opening_owner_capital", 0.0))
        total_assets = cash_ending + receivables + inventory + vat_asset
        owner_equity = ob_owner_capital if ob_owner_capital != 0.0 else (total_assets - liabilities - retained)
        total_equity = owner_equity + retained
        total_capital = liabilities + total_equity

        # Prior-year comparatives (So dau nam)
        prior_bal = self.fetch_annual_balance_sheet(year - 1)
        prior_cash = self.fetch_annual_cash_flow(year - 1)
        prior_vat = self.fetch_vat_totals_as_of(prior_bal["end_date"])
        prior_recv = self.estimate_credit_receivables_as_of(prior_bal["end_date"])
        prior_ob = self.get_opening_balance_for_year(year - 1)
        p_cash_end = float(prior_cash.get("ending_cash", 0.0))
        if p_cash_end == 0.0:
            p_cash_end = float(prior_ob.get("opening_cash", 0.0))
        p_inventory = float(prior_bal.get("inventory_value", 0.0))
        p_vat_asset = float(prior_vat.get("deductible_vat", 0.0)) + float(prior_ob.get("opening_vat_deductible", 0.0))
        p_receivables = prior_recv + float(prior_ob.get("opening_receivables", 0.0))
        p_liabilities = float(prior_bal.get("total_liabilities", 0.0)) + float(prior_ob.get("opening_payables", 0.0))
        p_retained = float(prior_bal.get("retained_earnings", 0.0)) + float(prior_ob.get("opening_retained_earnings", 0.0))
        p_ob_owner = float(prior_ob.get("opening_owner_capital", 0.0))
        p_total_assets = p_cash_end + p_receivables + p_inventory + p_vat_asset
        p_owner_equity = p_ob_owner if p_ob_owner != 0.0 else (p_total_assets - p_liabilities - p_retained)
        p_total_equity = p_owner_equity + p_retained
        p_total_capital = p_liabilities + p_total_equity

        b01_rows = [
            ("TAI SAN", "", "", "", ""),
            ("I. Tien va cac khoan tuong duong tien", "110", "V.01", cash_ending, p_cash_end),
            ("II. Dau tu tai chinh", "120", "V.02", 0, 0),
            ("III. Cac khoan phai thu", "130", "V.03", receivables, p_receivables),
            ("IV. Hang ton kho", "140", "V.04", inventory, p_inventory),
            ("1. Hang ton kho", "141", "", inventory, p_inventory),
            ("V. Tai san co dinh", "150", "V.05", 0, 0),
            ("VI. Bat dong san dau tu", "160", "V.06", 0, 0),
            ("VII. XDCB do dang", "170", "V.07", 0, 0),
            ("VIII. Tai san khac", "180", "V.08", vat_asset, p_vat_asset),
            ("1. Thue GTGT duoc khau tru", "181", "", vat_asset, p_vat_asset),
            ("TONG CONG TAI SAN", "200", "", total_assets, p_total_assets),
            ("", "", "", "", ""),
            ("NGUON VON", "", "", "", ""),
            ("I. No phai tra", "300", "", liabilities, p_liabilities),
            ("1. Phai tra nguoi ban", "311", "V.09.a", float(annual.get("accounts_payable", 0.0)), float(prior_bal.get("accounts_payable", 0.0))),
            ("2. Nguoi mua tra tien truoc", "312", "V.09.b", 0, 0),
            ("3. Thue va cac khoan phai nop Nha nuoc", "313", "V.10", float(annual.get("vat_payable", 0.0)), float(prior_bal.get("vat_payable", 0.0))),
            ("4. Phai tra nguoi lao dong", "314", "", 0, 0),
            ("5. Phai tra khac", "315", "V.09.c", 0, 0),
            ("II. Von chu so huu", "400", "V.13", total_equity, p_total_equity),
            ("1. Von gop cua chu so huu", "411", "", owner_equity, p_owner_equity),
            ("7. Loi nhuan sau thue chua phan phoi", "417", "", retained, p_retained),
            ("TONG CONG NGUON VON", "500", "", total_capital, p_total_capital),
        ]

        adj_b01 = self.get_export_adjustments_for_year(year)
        for line_item, code, note, end_value, begin_value in b01_rows:
            if code:
                end_value = adj_b01.get(("B01a", code), end_value)
                line_item = text_adj.get(("B01a", code, "label"), line_item)
                note = text_adj.get(("B01a", code, "note_code"), note)
            rows.append([
                line_item,
                code,
                note,
                self._asp_money(end_value) if end_value != "" else "",
                self._asp_money(begin_value) if begin_value != "" else "",
            ])

        rows.append([])
        return rows

    def build_annual_b02_rows(self, year):
        annual = self.fetch_annual_income_statement(year)
        text_adj = self.get_export_text_adjustments_for_year(year)
        rows = []
        self._append_asp_header(rows, "B02-DNN", "BAO CAO KET QUA HOAT DONG KINH DOANH", f"Nam {year}", text_adj)
        rows.append(["Chi tieu", "Ma so", "Thuyet minh", "Nam nay", "Nam truoc"])

        revenue = float(annual.get("revenue", 0.0))
        cogs = float(annual.get("cogs", 0.0))
        gross_profit = float(annual.get("gross_profit", 0.0))
        operating_expenses = float(annual.get("operating_expenses", 0.0))
        operating_profit = float(annual.get("operating_profit", 0.0))
        net_income = float(annual.get("net_income", 0.0))

        # Prior-year comparatives (Nam truoc)
        prior_inc = self.fetch_annual_income_statement(year - 1)
        p_revenue = float(prior_inc.get("revenue", 0.0))
        p_cogs = float(prior_inc.get("cogs", 0.0))
        p_gross_profit = float(prior_inc.get("gross_profit", 0.0))
        p_operating_expenses = float(prior_inc.get("operating_expenses", 0.0))
        p_operating_profit = float(prior_inc.get("operating_profit", 0.0))
        p_net_income = float(prior_inc.get("net_income", 0.0))

        b02_rows = [
            ("1. Doanh thu ban hang va cung cap dich vu", "01", "VI.1", revenue, p_revenue),
            ("2. Cac khoan giam tru doanh thu", "02", "VI.2", 0, 0),
            ("3. Doanh thu thuan", "10", "", revenue, p_revenue),
            ("4. Gia von hang ban", "11", "VI.3", cogs, p_cogs),
            ("5. Loi nhuan gop", "20", "", gross_profit, p_gross_profit),
            ("6. Doanh thu hoat dong tai chinh", "21", "VI.4", 0, 0),
            ("7. Chi phi tai chinh", "22", "VI.5", 0, 0),
            ("8. Chi phi quan ly kinh doanh", "24", "VI.6", operating_expenses, p_operating_expenses),
            ("9. Loi nhuan thuan tu hoat dong kinh doanh", "30", "", operating_profit, p_operating_profit),
            ("10. Thu nhap khac", "31", "VI.7", 0, 0),
            ("11. Chi phi khac", "32", "VI.8", 0, 0),
            ("12. Loi nhuan khac", "40", "", 0, 0),
            ("13. Tong loi nhuan ke toan truoc thue", "50", "", operating_profit, p_operating_profit),
            ("14. Chi phi thue TNDN", "51", "VI.9", 0, 0),
            ("15. Loi nhuan sau thue TNDN", "60", "", net_income, p_net_income),
        ]

        adj_b02 = self.get_export_adjustments_for_year(year)
        for line_item, code, note, current_year, prev_year in b02_rows:
            if code:
                current_year = adj_b02.get(("B02", code), current_year)
                line_item = text_adj.get(("B02", code, "label"), line_item)
                note = text_adj.get(("B02", code, "note_code"), note)
            rows.append([line_item, code, note, self._asp_money(current_year), self._asp_money(prev_year)])

        rows.append([])
        return rows

    def build_annual_b03_rows(self, year):
        annual = self.fetch_annual_cash_flow(year)
        breakdown = self.fetch_annual_cash_flow_breakdown(year)
        text_adj = self.get_export_text_adjustments_for_year(year)
        rows = []
        self._append_asp_header(rows, "B03-DNN", "BAO CAO LUU CHUYEN TIEN TE", f"Nam {year}", text_adj)
        rows.append(["(Theo phuong phap truc tiep)"])
        rows.append([])
        rows.append(["Chi tieu", "Ma so", "Thuyet minh", "Nam nay", "Nam truoc"])

        operating_in = float(breakdown.get("operating_in", 0.0))
        supplier_out = float(breakdown.get("operating_supplier_out", 0.0))
        wages_out = float(breakdown.get("operating_wages_out", 0.0))
        other_out = float(breakdown.get("operating_other_out", 0.0))
        operating_net = float(breakdown.get("operating_net", 0.0))
        investing_net = float(breakdown.get("investing_net", 0.0))
        financing_in = float(breakdown.get("financing_in", 0.0))
        financing_net = float(breakdown.get("financing_net", 0.0))
        net_cash = float(annual.get("net_cash", 0.0))
        begin_cash = float(annual.get("beginning_cash", 0.0))
        end_cash = float(annual.get("ending_cash", 0.0))

        # Prior-year comparatives (Nam truoc)
        prior_cf = self.fetch_annual_cash_flow(year - 1)
        prior_bd = self.fetch_annual_cash_flow_breakdown(year - 1)
        p_operating_in = float(prior_bd.get("operating_in", 0.0))
        p_supplier_out = float(prior_bd.get("operating_supplier_out", 0.0))
        p_wages_out = float(prior_bd.get("operating_wages_out", 0.0))
        p_other_out = float(prior_bd.get("operating_other_out", 0.0))
        p_operating_net = float(prior_bd.get("operating_net", 0.0))
        p_investing_net = float(prior_bd.get("investing_net", 0.0))
        p_financing_in = float(prior_bd.get("financing_in", 0.0))
        p_financing_net = float(prior_bd.get("financing_net", 0.0))
        p_net_cash = float(prior_cf.get("net_cash", 0.0))
        p_begin_cash = float(prior_cf.get("beginning_cash", 0.0))
        p_end_cash = float(prior_cf.get("ending_cash", 0.0))

        b03_rows = [
            ("I. Luu chuyen tien tu hoat dong kinh doanh", "", "", "", ""),
            ("1. Tien thu tu ban hang, cung cap dich vu", "01", "", operating_in, p_operating_in),
            ("2. Tien chi tra cho nguoi cung cap", "02", "", supplier_out, p_supplier_out),
            ("3. Tien chi tra cho nguoi lao dong", "03", "", wages_out, p_wages_out),
            ("7. Tien chi khac cho hoat dong kinh doanh", "07", "", other_out, p_other_out),
            ("Luu chuyen tien thuan tu HDKD", "20", "", operating_net, p_operating_net),
            ("II. Luu chuyen tien tu hoat dong dau tu", "", "", "", ""),
            ("Luu chuyen tien thuan tu HDDT", "30", "", investing_net, p_investing_net),
            ("III. Luu chuyen tien tu hoat dong tai chinh", "", "", "", ""),
            ("1. Tien thu tu phat hanh co phieu, nhan von gop", "31", "", financing_in, p_financing_in),
            ("Luu chuyen tien thuan tu HDTC", "40", "", financing_net, p_financing_net),
            ("Luu chuyen tien thuan trong ky", "50", "", net_cash, p_net_cash),
            ("Tien va tuong duong tien dau ky", "60", "", begin_cash, p_begin_cash),
            ("Anh huong cua thay doi ty gia", "61", "", 0, 0),
            ("Tien va tuong duong tien cuoi ky", "70", "VII", end_cash, p_end_cash),
        ]

        adj_b03 = self.get_export_adjustments_for_year(year)
        for line_item, code, note, current_year, prev_year in b03_rows:
            if code:
                current_year = adj_b03.get(("B03", code), current_year)
                line_item = text_adj.get(("B03", code, "label"), line_item)
                note = text_adj.get(("B03", code, "note_code"), note)
            cur_text = self._asp_money(current_year) if current_year != "" else ""
            prev_text = self._asp_money(prev_year) if prev_year != "" else ""
            rows.append([line_item, code, note, cur_text, prev_text])

        rows.append([])
        return rows

    def build_annual_f01_rows(self, year):
        start_date, end_date = self.get_year_date_bounds(year)
        text_adj = self.get_export_text_adjustments_for_year(year)

        account_lines = {
            "111": "Tien mat",
            "1111": "Tien Viet Nam",
            "112": "Tien gui Ngan hang",
            "1121": "Tien Viet Nam",
            "131": "Phai thu cua khach hang",
            "133": "Thue GTGT duoc khau tru",
            "1331": "Thue GTGT duoc khau tru cua hang hoa, dich vu",
            "156": "Hang hoa",
            "331": "Phai tra cho nguoi ban",
            "333": "Thue va cac khoan phai nop Nha nuoc",
            "3331": "Thue GTGT phai nop",
            "33311": "Thue GTGT dau ra",
            "334": "Phai tra nguoi lao dong",
            "411": "Von dau tu cua chu so huu",
            "4111": "Von gop cua chu so huu",
            "421": "Loi nhuan sau thue chua phan phoi",
            "4212": "Loi nhuan sau thue chua phan phoi nam nay",
            "511": "Doanh thu ban hang va cung cap dich vu",
            "5111": "Doanh thu ban hang hoa",
            "632": "Gia von hang ban",
            "642": "Chi phi quan ly kinh doanh",
            "6422": "Chi phi quan ly doanh nghiep",
            "911": "Xac dinh ket qua kinh doanh",
        }

        balances = {code: {"opening_dr": 0.0, "opening_cr": 0.0, "mov_dr": 0.0, "mov_cr": 0.0} for code in account_lines}

        def post(code, debit=0.0, credit=0.0):
            if code not in balances:
                return
            balances[code]["mov_dr"] += float(debit or 0.0)
            balances[code]["mov_cr"] += float(credit or 0.0)

        income = self.fetch_annual_income_statement(year)
        net_income = float(income.get("net_income", 0.0))
        cogs = float(income.get("cogs", 0.0))
        operating_expenses = float(income.get("operating_expenses", 0.0))

        conn = sqlite3.connect(FINANCIAL_DB)
        try:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT COALESCE(SUM(gross_sales), 0), COALESCE(SUM(vat_amount), 0)
                FROM Sales
                WHERE sale_date BETWEEN ? AND ?
                """,
                (start_date, end_date),
            )
            sales_gross, sales_vat = cursor.fetchone() or (0.0, 0.0)
            sales_gross = float(sales_gross or 0.0)
            sales_vat = float(sales_vat or 0.0)

            post("131", debit=sales_gross + sales_vat)
            post("511", credit=sales_gross)
            post("5111", credit=sales_gross)
            post("333", credit=sales_vat)
            post("3331", credit=sales_vat)
            post("33311", credit=sales_vat)

            cursor.execute(
                """
                SELECT COALESCE(SUM(amount), 0), COALESCE(SUM(COALESCE(vat_amount, 0)), 0)
                FROM Costs
                WHERE cost_date BETWEEN ? AND ?
                """,
                (start_date, end_date),
            )
            cost_amt, cost_vat = cursor.fetchone() or (0.0, 0.0)
            cost_amt = float(cost_amt or 0.0)
            cost_vat = float(cost_vat or 0.0)

            post("642", debit=cost_amt)
            post("6422", debit=cost_amt)
            post("133", debit=cost_vat)
            post("1331", debit=cost_vat)
            post("331", credit=cost_amt + cost_vat)

            cursor.execute(
                """
                SELECT COALESCE(SUM(total), 0), COALESCE(SUM(COALESCE(tax_amount, 0)), 0)
                FROM Stock
                WHERE date BETWEEN ? AND ?
                """,
                (start_date, end_date),
            )
            stock_amt, stock_vat = cursor.fetchone() or (0.0, 0.0)
            stock_amt = float(stock_amt or 0.0)
            stock_vat = float(stock_vat or 0.0)

            post("156", debit=stock_amt)
            post("133", debit=stock_vat)
            post("1331", debit=stock_vat)
            post("331", credit=stock_amt + stock_vat)

            cursor.execute(
                """
                SELECT balance
                FROM Timeline
                WHERE event_date < ?
                ORDER BY event_date DESC, id DESC
                LIMIT 1
                """,
                (start_date,),
            )
            opening_cash_row = cursor.fetchone()
            opening_cash = float(opening_cash_row[0]) if opening_cash_row and opening_cash_row[0] is not None else 0.0

            cursor.execute(
                """
                SELECT COALESCE(SUM(cash_in), 0), COALESCE(SUM(cash_out), 0)
                FROM Timeline
                WHERE event_date BETWEEN ? AND ?
                """,
                (start_date, end_date),
            )
            cash_in, cash_out = cursor.fetchone() or (0.0, 0.0)
            cash_in = float(cash_in or 0.0)
            cash_out = float(cash_out or 0.0)
        finally:
            conn.close()

        if opening_cash == 0.0:
            try:
                ob_fallback = self.get_opening_balance_for_year(year)
                opening_cash = float(ob_fallback.get("opening_cash", 0.0))
            except Exception:
                pass

        balances["111"]["opening_dr"] = max(0.0, opening_cash)
        balances["1111"]["opening_dr"] = max(0.0, opening_cash)

        ob = self.get_opening_balance_for_year(year)
        balances["131"]["opening_dr"] += float(ob.get("opening_receivables", 0.0))
        balances["133"]["opening_dr"] += float(ob.get("opening_vat_deductible", 0.0))
        balances["1331"]["opening_dr"] += float(ob.get("opening_vat_deductible", 0.0))
        balances["331"]["opening_cr"] += float(ob.get("opening_payables", 0.0))
        balances["411"]["opening_cr"] += float(ob.get("opening_owner_capital", 0.0))
        balances["4111"]["opening_cr"] += float(ob.get("opening_owner_capital", 0.0))
        ob_retained = float(ob.get("opening_retained_earnings", 0.0))
        if ob_retained >= 0:
            balances["421"]["opening_cr"] += ob_retained
            balances["4212"]["opening_cr"] += ob_retained
        else:
            balances["421"]["opening_dr"] += abs(ob_retained)
            balances["4212"]["opening_dr"] += abs(ob_retained)

        post("111", debit=cash_in, credit=cash_out)
        post("1111", debit=cash_in, credit=cash_out)

        post("632", debit=cogs)
        post("156", credit=cogs)

        post("911", debit=cogs + operating_expenses)
        post("911", credit=float(income.get("revenue", 0.0)))
        if net_income >= 0:
            post("421", credit=net_income)
            post("4212", credit=net_income)
        else:
            post("421", debit=abs(net_income))
            post("4212", debit=abs(net_income))

        rows = []
        self._append_asp_header(rows, "F01-DNN", "BANG CAN DOI TAI KHOAN", f"Nam {year}", text_adj)
        rows.append([
            "So hieu tai khoan",
            "Ten tai khoan",
            "Dau ky No",
            "Dau ky Co",
            "Phat sinh No",
            "Phat sinh Co",
            "Cuoi ky No",
            "Cuoi ky Co",
        ])

        total = {
            "opening_dr": 0.0,
            "opening_cr": 0.0,
            "mov_dr": 0.0,
            "mov_cr": 0.0,
            "closing_dr": 0.0,
            "closing_cr": 0.0,
        }

        adj_f01 = self.get_export_adjustments_for_year(year)
        for code, name in account_lines.items():
            payload = balances[code]
            opening_dr = payload["opening_dr"]
            opening_cr = payload["opening_cr"]
            mov_dr = payload["mov_dr"]
            mov_cr = payload["mov_cr"]

            closing_balance = (opening_dr - opening_cr) + (mov_dr - mov_cr)
            closing_dr = max(closing_balance, 0.0)
            closing_cr = max(-closing_balance, 0.0)

            if ("F01", code) in adj_f01:
                adj_val = adj_f01[("F01", code)]
                if adj_val >= 0:
                    closing_dr = adj_val
                    closing_cr = 0.0
                else:
                    closing_dr = 0.0
                    closing_cr = abs(adj_val)

            total["opening_dr"] += opening_dr
            total["opening_cr"] += opening_cr
            total["mov_dr"] += mov_dr
            total["mov_cr"] += mov_cr
            total["closing_dr"] += closing_dr
            total["closing_cr"] += closing_cr

            rows.append([
                code,
                text_adj.get(("F01", code, "label"), name),
                self._asp_money(opening_dr),
                self._asp_money(opening_cr),
                self._asp_money(mov_dr),
                self._asp_money(mov_cr),
                self._asp_money(closing_dr),
                self._asp_money(closing_cr),
            ])

        rows.append([
            "Cong",
            "",
            self._asp_money(total["opening_dr"]),
            self._asp_money(total["opening_cr"]),
            self._asp_money(total["mov_dr"]),
            self._asp_money(total["mov_cr"]),
            self._asp_money(total["closing_dr"]),
            self._asp_money(total["closing_cr"]),
        ])
        rows.append([])
        return rows

    def fetch_monthly_chart_data(self, year):
        """Return per-month revenue, cogs, cash-balance, and inventory data for charting."""
        import calendar
        # Prior year-end inventory value for running inventory total
        try:
            prior_snap = self.fetch_inventory_snapshot_as_of(f"{year - 1}-12-31")
            prior_inv_value = float(prior_snap.get("total_value", 0.0))
        except Exception:
            prior_inv_value = 0.0

        # Weighted average unit cost per SKU (used for COGS calculation)
        weighted_cost = self.fetch_weighted_unit_cost_by_sku_as_of(f"{year}-12-31")

        conn = sqlite3.connect(FINANCIAL_DB)
        try:
            cursor = conn.cursor()
            # Monthly revenue
            cursor.execute(
                """
                SELECT strftime('%m', sale_date) AS mon,
                       COALESCE(SUM(gross_sales), 0)
                FROM Sales
                WHERE strftime('%Y', sale_date) = ?
                GROUP BY mon
                """,
                (str(year),),
            )
            rev_by_month = {int(r[0]): float(r[1]) for r in cursor.fetchall()}

            # Monthly costs (operating expenses)
            cursor.execute(
                """
                SELECT strftime('%m', cost_date) AS mon,
                       COALESCE(SUM(amount), 0)
                FROM Costs
                WHERE strftime('%Y', cost_date) = ?
                GROUP BY mon
                """,
                (str(year),),
            )
            cost_by_month = {int(r[0]): float(r[1]) for r in cursor.fetchall()}

            # Monthly COGS via units_sold × weighted average unit cost per SKU
            cursor.execute(
                """
                SELECT strftime('%m', sale_date) AS mon,
                       product_sku,
                       COALESCE(SUM(units_sold), 0)
                FROM Sales
                WHERE strftime('%Y', sale_date) = ?
                GROUP BY mon, product_sku
                """,
                (str(year),),
            )
            cogs_by_month = {}
            for _mon, _sku, _units in cursor.fetchall():
                uc = float(weighted_cost.get(str(_sku or ""), 0.0))
                cogs_by_month[int(_mon)] = cogs_by_month.get(int(_mon), 0.0) + float(_units or 0) * uc

            # Monthly stock additions (unit_in * unit_cost)
            cursor.execute(
                """
                SELECT strftime('%m', date) AS mon,
                       COALESCE(SUM(unit_in * COALESCE(unit_cost, 0)), 0)
                FROM Stock
                WHERE strftime('%Y', date) = ?
                GROUP BY mon
                """,
                (str(year),),
            )
            stock_add_by_month = {int(r[0]): float(r[1]) for r in cursor.fetchall()}

            # Month-end cash balance from Timeline
            cursor.execute(
                """
                SELECT strftime('%m', event_date) AS mon,
                       balance
                FROM Timeline
                WHERE strftime('%Y', event_date) = ?
                  AND balance IS NOT NULL
                ORDER BY event_date ASC, id ASC
                """,
                (str(year),),
            )
            cash_by_month = {}
            for row in cursor.fetchall():
                cash_by_month[int(row[0])] = float(row[1])
        finally:
            conn.close()

        months = list(range(1, 13))
        labels = [calendar.month_abbr[m] for m in months]
        revenue = [rev_by_month.get(m, 0.0) for m in months]
        cogs = [cogs_by_month.get(m, 0.0) for m in months]
        op_expenses = [cost_by_month.get(m, 0.0) for m in months]
        gross_margin_pct = [
            (revenue[i] - cogs[i]) / revenue[i] * 100 if revenue[i] > 0 else 0.0
            for i in range(12)
        ]
        # Carry forward cash balance for months with no entry
        cash_balance = []
        last_cash = 0.0
        for m in months:
            if m in cash_by_month:
                last_cash = cash_by_month[m]
            cash_balance.append(last_cash)

        # Running inventory value: start from prior year-end, add stock-in, subtract COGS each month
        inventory_value = []
        running_inv = prior_inv_value
        for m in months:
            running_inv += stock_add_by_month.get(m, 0.0) - cogs_by_month.get(m, 0.0)
            running_inv = max(0.0, running_inv)
            inventory_value.append(running_inv)

        return {
            "labels": labels,
            "revenue": revenue,
            "cogs": cogs,
            "op_expenses": op_expenses,
            "gross_margin_pct": gross_margin_pct,
            "cash_balance": cash_balance,
            "inventory_value": inventory_value,
        }

    def build_charts_tab(self, parent, year):
        """Build a 5-chart matplotlib panel inside `parent` with its own year selector."""
        for widget in parent.winfo_children():
            widget.destroy()

        if not MATPLOTLIB_OK:
            tk.Label(
                parent,
                text="matplotlib is not available. Install it to enable charts.",
                bg=self.ui_palette["bg"],
                fg=self.ui_palette["muted"],
                font=("Segoe UI", 11),
            ).pack(expand=True)
            return

        try:
            quarter_pairs = self.get_business_finance_quarters()
            available_years = sorted({y for y, _ in quarter_pairs}, reverse=True)
        except Exception:
            available_years = [year]
        if year not in available_years:
            available_years.insert(0, year)

        toolbar = tk.Frame(parent, bg=self.ui_palette["bg"])
        toolbar.pack(fill="x", padx=8, pady=(6, 2))
        tk.Label(
            toolbar, text="Chart Year:",
            bg=self.ui_palette["bg"], fg=self.ui_palette["text"],
            font=self.ui_typography["label_bold"],
        ).pack(side="left")
        chart_year_var = tk.StringVar(value=str(year))
        year_combo = ttk.Combobox(
            toolbar,
            textvariable=chart_year_var,
            values=[str(y) for y in available_years],
            state="readonly",
            width=9,
        )
        year_combo.pack(side="left", padx=(6, 12))

        hover_var = tk.StringVar(value="Hover a chart point/bar to inspect values.")
        tk.Label(
            toolbar,
            textvariable=hover_var,
            bg=self.ui_palette["bg"],
            fg=self.ui_palette["muted"],
            font=self.ui_typography["status"],
        ).pack(side="right")

        chart_frame = tk.Frame(parent, bg=self.ui_palette["bg"])
        chart_frame.pack(expand=True, fill="both")

        def _draw_charts():
            for w in chart_frame.winfo_children():
                w.destroy()
            try:
                _year = int(chart_year_var.get())
                data = self.fetch_monthly_chart_data(_year)
            except Exception as exc:
                tk.Label(
                    chart_frame,
                    text=f"Could not load chart data: {exc}",
                    bg=self.ui_palette["bg"],
                    fg="#c00",
                    font=("Segoe UI", 10),
                ).pack(expand=True)
                return

            labels = data["labels"]
            revenue = data["revenue"]
            cogs = data["cogs"]
            op_expenses = data["op_expenses"]
            gross_margin_pct = data["gross_margin_pct"]
            cash_balance = data["cash_balance"]
            inventory_value = data["inventory_value"]

            bg_color = self.ui_palette.get("bg", "#1e1e2e")
            is_dark = self._is_dark_color(bg_color)
            plt_style = "dark_background" if is_dark else "seaborn-v0_8-whitegrid"
            try:
                plt.style.use(plt_style)
            except Exception:
                pass

            fig = Figure(figsize=(13, 7.5), dpi=96, tight_layout=True)
            fig.patch.set_facecolor(bg_color)
            panel_bg = self.ui_palette.get("panel", bg_color)
            text_color = self.ui_palette.get("text", "#ffffff" if is_dark else "#1a1a2e")
            x = list(range(12))
            month_labels = [f"{lbl} '{str(_year)[-2:]}" for lbl in labels]
            bar_w = 0.38

            # Shared scales for better cross-chart comparability.
            max_value_main = max(max(revenue or [0.0]), max(op_expenses or [0.0]), max(cogs or [0.0]), 1.0)
            max_cash = max(max(cash_balance or [0.0]), 1.0)
            max_inventory = max(max(inventory_value or [0.0]), 1.0)
            margin_pad = 5.0

            fig.suptitle(
                f"Financial Visual Analytics - Year {_year}",
                color=text_color,
                fontsize=11,
                fontweight="bold",
                y=0.99,
            )

            # Chart 1: Revenue vs Op. Expenses
            ax1 = fig.add_subplot(2, 3, 1)
            ax1.set_facecolor(panel_bg)
            bars_rev = ax1.bar([i - bar_w / 2 for i in x], revenue, width=bar_w, label="Revenue", color="#4caf50", alpha=0.85)
            bars_exp = ax1.bar([i + bar_w / 2 for i in x], op_expenses, width=bar_w, label="Op. Expenses", color="#f44336", alpha=0.85)
            ax1.set_ylim(0, max_value_main * 1.12)
            ax1.set_xticks(x)
            ax1.set_xticklabels(month_labels, fontsize=7, color=text_color, rotation=20, ha="right")
            ax1.set_title(f"Revenue vs Expenses ({_year})", color=text_color, fontsize=9)
            ax1.tick_params(axis="y", labelcolor=text_color, labelsize=7)
            ax1.legend(fontsize=7, facecolor=panel_bg, labelcolor=text_color)
            ax1.grid(axis="y", alpha=0.2)
            ax1.spines["top"].set_visible(False); ax1.spines["right"].set_visible(False)

            # Chart 2: Cash Balance trend
            ax2 = fig.add_subplot(2, 3, 2)
            ax2.set_facecolor(panel_bg)
            ax2.plot(x, cash_balance, color="#2196f3", linewidth=2, marker="o", markersize=4)
            ax2.fill_between(x, cash_balance, alpha=0.15, color="#2196f3")
            ax2.set_ylim(0, max_cash * 1.12)
            ax2.set_xticks(x)
            ax2.set_xticklabels(month_labels, fontsize=7, color=text_color, rotation=20, ha="right")
            ax2.set_title(f"Cash Balance ({_year})", color=text_color, fontsize=9)
            ax2.tick_params(axis="y", labelcolor=text_color, labelsize=7)
            ax2.grid(axis="y", alpha=0.2)
            ax2.spines["top"].set_visible(False); ax2.spines["right"].set_visible(False)

            # Chart 3: Gross Margin %
            ax3 = fig.add_subplot(2, 3, 3)
            ax3.set_facecolor(panel_bg)
            ax3.plot(x, gross_margin_pct, color="#ff9800", linewidth=2, marker="s", markersize=4)
            ax3.axhline(y=0, color=text_color, linewidth=0.5, linestyle="--", alpha=0.4)
            gm_min = min(gross_margin_pct or [0.0])
            gm_max = max(gross_margin_pct or [0.0])
            ax3.set_ylim(gm_min - margin_pad, gm_max + margin_pad)
            ax3.set_xticks(x)
            ax3.set_xticklabels(month_labels, fontsize=7, color=text_color, rotation=20, ha="right")
            ax3.set_title(f"Gross Margin % ({_year})", color=text_color, fontsize=9)
            ax3.set_ylabel("%", color=text_color, fontsize=8)
            ax3.tick_params(axis="y", labelcolor=text_color, labelsize=7)
            ax3.grid(axis="y", alpha=0.2)
            ax3.spines["top"].set_visible(False); ax3.spines["right"].set_visible(False)

            # Chart 4: COGS vs Revenue
            ax4 = fig.add_subplot(2, 3, 4)
            ax4.set_facecolor(panel_bg)
            bars_rev_overlay = ax4.bar(x, revenue, label="Revenue", color="#4caf50", alpha=0.5, width=0.6)
            bars_cogs = ax4.bar(x, cogs, label="COGS", color="#9c27b0", alpha=0.75, width=0.6)
            ax4.set_ylim(0, max_value_main * 1.12)
            ax4.set_xticks(x)
            ax4.set_xticklabels(month_labels, fontsize=7, color=text_color, rotation=20, ha="right")
            ax4.set_title(f"COGS vs Revenue ({_year})", color=text_color, fontsize=9)
            ax4.tick_params(axis="y", labelcolor=text_color, labelsize=7)
            ax4.legend(fontsize=7, facecolor=panel_bg, labelcolor=text_color)
            ax4.grid(axis="y", alpha=0.2)
            ax4.spines["top"].set_visible(False); ax4.spines["right"].set_visible(False)

            # Chart 5: Inventory Value trend
            ax5 = fig.add_subplot(2, 3, 5)
            ax5.set_facecolor(panel_bg)
            bars_inv = ax5.bar(x, inventory_value, color="#00bcd4", alpha=0.8, width=0.65)
            ax5.set_ylim(0, max_inventory * 1.12)
            ax5.set_xticks(x)
            ax5.set_xticklabels(month_labels, fontsize=7, color=text_color, rotation=20, ha="right")
            ax5.set_title(f"Inventory Value ({_year})", color=text_color, fontsize=9)
            ax5.tick_params(axis="y", labelcolor=text_color, labelsize=7)
            ax5.grid(axis="y", alpha=0.2)
            ax5.spines["top"].set_visible(False); ax5.spines["right"].set_visible(False)

            # Slot 6: KPI summary panel for quick analyst scan.
            ax6 = fig.add_subplot(2, 3, 6)
            ax6.set_facecolor(panel_bg)
            ax6.axis("off")
            total_revenue = sum(revenue)
            total_exp = sum(op_expenses)
            total_cogs = sum(cogs)
            gross_profit = total_revenue - total_cogs
            avg_margin = (gross_profit / total_revenue * 100) if total_revenue > 0 else 0.0
            end_cash = cash_balance[-1] if cash_balance else 0.0
            end_inventory = inventory_value[-1] if inventory_value else 0.0
            kpi_lines = [
                f"Total Revenue: {total_revenue:,.0f} VND",
                f"Total Op. Expenses: {total_exp:,.0f} VND",
                f"Gross Profit: {gross_profit:,.0f} VND",
                f"Gross Margin: {avg_margin:,.1f}%",
                f"Year-end Cash: {end_cash:,.0f} VND",
                f"Year-end Inventory: {end_inventory:,.0f} VND",
            ]
            ax6.text(
                0.02,
                0.95,
                "Year KPI Snapshot",
                fontsize=9,
                fontweight="bold",
                color=text_color,
                va="top",
            )
            ax6.text(
                0.02,
                0.84,
                "\n".join(kpi_lines),
                fontsize=8,
                color=text_color,
                va="top",
                linespacing=1.5,
            )

            canvas = FigureCanvasTkAgg(fig, master=chart_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(expand=True, fill="both", padx=6, pady=6)

            # Lightweight hover feedback for data-first analysis.
            bar_artists = []
            for collection, series_name in (
                (bars_rev, "Revenue"),
                (bars_exp, "Op. Expenses"),
                (bars_rev_overlay, "Revenue"),
                (bars_cogs, "COGS"),
                (bars_inv, "Inventory"),
            ):
                for i, b in enumerate(collection):
                    bar_artists.append((b, series_name, i))

            def on_move(event):
                if event.inaxes is None:
                    hover_var.set("Hover a chart point/bar to inspect values.")
                    return

                for bar, label_name, idx in bar_artists:
                    contains, _ = bar.contains(event)
                    if contains:
                        val = bar.get_height()
                        hover_var.set(f"{label_name} | {month_labels[idx]}: {val:,.0f} VND")
                        return

                if event.inaxes == ax2 and event.xdata is not None:
                    idx = int(round(event.xdata))
                    if 0 <= idx < len(cash_balance):
                        hover_var.set(f"Cash | {month_labels[idx]}: {cash_balance[idx]:,.0f} VND")
                        return

                if event.inaxes == ax3 and event.xdata is not None:
                    idx = int(round(event.xdata))
                    if 0 <= idx < len(gross_margin_pct):
                        hover_var.set(f"Gross Margin | {month_labels[idx]}: {gross_margin_pct[idx]:,.1f}%")
                        return

                hover_var.set("Hover a chart point/bar to inspect values.")

            fig.canvas.mpl_connect("motion_notify_event", on_move)

        tk.Button(
            toolbar,
            text="Refresh Charts",
            command=_draw_charts,
            bg=self.ui_palette["accent"],
            fg="white",
            relief="flat",
            padx=10,
        ).pack(side="left")
        year_combo.bind("<<ComboboxSelected>>", lambda e: _draw_charts())
        _draw_charts()

    def _is_dark_color(self, hex_color):
        try:
            hex_color = hex_color.lstrip("#")
            r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
            return (0.299 * r + 0.587 * g + 0.114 * b) < 128
        except Exception:
            return True

    def export_annual_asp_report_csv(self, year, output_path=None):
        if not output_path:
            export_dir = BASE_DIR / "artifacts" / "exports"
            export_dir.mkdir(parents=True, exist_ok=True)
            output_path = export_dir / f"annual_financial_report_{int(year)}.csv"
        else:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

        rows = []
        rows.extend(self.build_annual_b01a_rows(year))
        rows.extend(self.build_annual_b02_rows(year))
        rows.extend(self.build_annual_b03_rows(year))
        rows.extend(self.build_annual_f01_rows(year))

        with open(output_path, "w", newline="", encoding="utf-8-sig") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerows(rows)

        self.last_annual_export_checks = self.get_annual_export_checks(year)

        return output_path

    def export_annual_pdf_report(self, year, output_path=None):
        if not REPORTLAB_OK:
            raise RuntimeError("reportlab is not installed. Run: pip install reportlab")

        if not output_path:
            export_dir = BASE_DIR / "artifacts" / "exports"
            export_dir.mkdir(parents=True, exist_ok=True)
            output_path = str(export_dir / f"annual_financial_report_{int(year)}.pdf")
        else:
            from pathlib import Path as _P
            output_path = str(output_path)
            _P(output_path).parent.mkdir(parents=True, exist_ok=True)

        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=15 * mm,
            rightMargin=15 * mm,
            topMargin=18 * mm,
            bottomMargin=18 * mm,
        )
        styles = getSampleStyleSheet()
        normal = styles["Normal"]
        normal.fontName = "Helvetica"
        normal.fontSize = 8

        h1 = ParagraphStyle("H1", parent=normal, fontSize=13, fontName="Helvetica-Bold",
                             spaceAfter=4, alignment=1)
        h2 = ParagraphStyle("H2", parent=normal, fontSize=10, fontName="Helvetica-Bold",
                             spaceAfter=3, spaceBefore=6, alignment=1)
        sub = ParagraphStyle("Sub", parent=normal, fontSize=8, alignment=1, spaceAfter=2)
        cell_style = ParagraphStyle("Cell", parent=normal, fontSize=7.5)

        company_name = "CONG TY TNHH VICINITY SAFETY"
        company_addr = "267 Nguyen Van Dau, Phuong Binh Loi Trung, Ho Chi Minh"

        # Attempt to read text adjustments for the header
        try:
            ta = self.get_export_text_adjustments_for_year(year)
            company_name = ta.get(("HEADER", "company", "company_name"), company_name)
            company_addr = ta.get(("HEADER", "company", "company_address"), company_addr)
        except Exception:
            pass

        accent = rl_colors.HexColor("#1e3a5f")
        light_grey = rl_colors.HexColor("#f0f0f0")
        mid_grey = rl_colors.HexColor("#d0d0d0")

        def _header_block(form_code, title, period):
            return [
                Paragraph(company_name, h1),
                Paragraph(company_addr, sub),
                Spacer(1, 4 * mm),
                Paragraph(f"Mau so: {form_code}", sub),
                Paragraph(title, h2),
                Paragraph(period, sub),
                Paragraph("Don vi tinh: VND", sub),
                Spacer(1, 3 * mm),
            ]

        def _money(v):
            try:
                return f"{float(v or 0):,.0f}"
            except (TypeError, ValueError):
                return "0"

        def _build_form_table(header_row, data_rows, col_widths):
            table_data = [header_row]
            for row in data_rows:
                table_data.append([Paragraph(str(c or ""), cell_style) for c in row])
            t = Table(table_data, colWidths=col_widths, repeatRows=1)
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), accent),
                ("TEXTCOLOR", (0, 0), (-1, 0), rl_colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                ("FONTNAME", (1, 1), (-1, -1), "Helvetica"),
                ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [rl_colors.white, light_grey]),
                ("GRID", (0, 0), (-1, -1), 0.3, mid_grey),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]))
            return t

        story = []
        page_w = A4[0] - 30 * mm  # usable width

        # ── B01a ─────────────────────────────────────────────────────────────
        b01_rows = self.build_annual_b01a_rows(year)
        story += _header_block("B01a-DNN", "BAO CAO TINH HINH TAI CHINH",
                                f"Tai ngay 31 thang 12 nam {year}")
        col_w = [page_w * 0.46, page_w * 0.08, page_w * 0.10, page_w * 0.18, page_w * 0.18]
        hdr = [Paragraph(h, ParagraphStyle("H", parent=cell_style, fontName="Helvetica-Bold"))
               for h in ["Chi tieu", "Ma so", "TM", "So cuoi nam", "So dau nam"]]
        data_rows = [r for r in b01_rows if len(r) == 5]
        story.append(_build_form_table(hdr, data_rows, col_w))
        story.append(PageBreak())

        # ── B02 ──────────────────────────────────────────────────────────────
        b02_rows = self.build_annual_b02_rows(year)
        story += _header_block("B02-DNN", "BAO CAO KET QUA HOAT DONG KINH DOANH",
                                f"Nam {year}")
        hdr2 = [Paragraph(h, ParagraphStyle("H", parent=cell_style, fontName="Helvetica-Bold"))
                for h in ["Chi tieu", "Ma so", "TM", "Nam nay", "Nam truoc"]]
        data_rows2 = [r for r in b02_rows if len(r) == 5]
        story.append(_build_form_table(hdr2, data_rows2, col_w))
        story.append(PageBreak())

        # ── B03 ──────────────────────────────────────────────────────────────
        b03_rows = self.build_annual_b03_rows(year)
        story += _header_block("B03-DNN", "BAO CAO LUU CHUYEN TIEN TE", f"Nam {year}")
        data_rows3 = [r for r in b03_rows if len(r) == 5]
        story.append(_build_form_table(hdr2, data_rows3, col_w))
        story.append(PageBreak())

        # ── F01 ──────────────────────────────────────────────────────────────
        f01_rows = self.build_annual_f01_rows(year)
        story += _header_block("F01-DNN", "BANG CAN DOI SO PHAT SINH", f"Nam {year}")
        f_col_w = [page_w * 0.08, page_w * 0.30,
                   page_w * 0.155, page_w * 0.155,
                   page_w * 0.155, page_w * 0.155]
        f_hdr = [Paragraph(h, ParagraphStyle("H", parent=cell_style, fontName="Helvetica-Bold"))
                 for h in ["TK", "Ten tai khoan",
                            "Du no dau", "Du co dau",
                            "Du no cuoi", "Du co cuoi"]]
        data_rows_f = [r for r in f01_rows if len(r) == 6]
        story.append(_build_form_table(f_hdr, data_rows_f, f_col_w))

        doc.build(story)
        return output_path

    def show_business_finance_report(self):
        for widget in self.content_area.winfo_children():
            widget.destroy()

        tk.Label(
            self.content_area,
            text="Business Finance Report",
            font=self.ui_typography["title"],
            bg=self.ui_palette["bg"],
            fg=self.ui_palette["text"],
        ).pack(pady=(self.ui_spacing["lg"], self.ui_spacing["sm"]))

        tk.Label(
            self.content_area,
            text="Quarterly and Annual Balance Sheet, Income Statement, and Cash Flow (separate from Financial Data)",
            bg=self.ui_palette["bg"],
            fg=self.ui_palette["muted"],
            font=self.ui_typography["subtitle"],
        ).pack(pady=(0, self.ui_spacing["sm"]))

        controls = tk.Frame(self.content_area, bg=self.ui_palette["bg"])
        controls.pack(fill="x", padx=self.ui_spacing["md"], pady=(self.ui_spacing["xs"], self.ui_spacing["sm"]))

        filter_row = tk.Frame(controls, bg=self.ui_palette["bg"])
        filter_row.pack(fill="x")

        action_row = tk.Frame(controls, bg=self.ui_palette["bg"])
        action_row.pack(fill="x", pady=(self.ui_spacing["xs"], 0))

        quarter_pairs = self.get_business_finance_quarters()
        year_to_quarters = {}
        for year, quarter in quarter_pairs:
            year_to_quarters.setdefault(int(year), set()).add(int(quarter))

        years = sorted(year_to_quarters.keys(), reverse=True)
        selected_year = years[0] if years else datetime.now().year
        selected_quarter = sorted(year_to_quarters.get(selected_year, {1}), reverse=True)[0]

        tk.Label(filter_row, text="Year:", bg=self.ui_palette["bg"], fg=self.ui_palette["text"], font=self.ui_typography["label_bold"]).pack(side="left")
        year_var = tk.StringVar(value=str(selected_year))
        year_combo = ttk.Combobox(
            filter_row,
            textvariable=year_var,
            values=[str(y) for y in years] if years else [str(selected_year)],
            state="readonly",
            width=10,
        )
        year_combo.pack(side="left", padx=(6, 14))

        tk.Label(filter_row, text="Period Type:", bg=self.ui_palette["bg"], fg=self.ui_palette["text"], font=self.ui_typography["label_bold"]).pack(side="left")
        period_type_var = tk.StringVar(value="Quarterly")
        period_type_combo = ttk.Combobox(
            filter_row,
            textvariable=period_type_var,
            values=["Quarterly", "Annual"],
            state="readonly",
            width=11,
        )
        period_type_combo.pack(side="left", padx=(6, 14))

        tk.Label(filter_row, text="Quarter:", bg=self.ui_palette["bg"], fg=self.ui_palette["text"], font=self.ui_typography["label_bold"]).pack(side="left")
        quarter_var = tk.StringVar(value=f"Q{selected_quarter}")
        quarter_combo = ttk.Combobox(filter_row, textvariable=quarter_var, state="readonly", width=8)
        quarter_combo.pack(side="left", padx=(6, 12))

        status_var = tk.StringVar(value="Ready")
        tk.Label(
            filter_row,
            textvariable=status_var,
            bg=self.ui_palette["bg"],
            fg=self.ui_palette["muted"],
            font=self.ui_typography["status"],
        ).pack(side="right")

        body = tk.Frame(self.content_area, bg=self.ui_palette["bg"])
        body.pack(expand=True, fill="both", padx=self.ui_spacing["sm"], pady=self.ui_spacing["sm"])

        notebook = ttk.Notebook(body, style="App.TNotebook")
        notebook.pack(expand=True, fill="both")

        income_tab = tk.Frame(notebook, bg=self.ui_palette["bg"])
        balance_tab = tk.Frame(notebook, bg=self.ui_palette["bg"])
        cash_tab = tk.Frame(notebook, bg=self.ui_palette["bg"])
        charts_tab = tk.Frame(notebook, bg=self.ui_palette["bg"])
        notebook.add(income_tab, text="Income Statement")
        notebook.add(balance_tab, text="Balance Sheet")
        notebook.add(cash_tab, text="Cash Flow")
        notebook.add(charts_tab, text="Charts")

        def build_statement_tree(parent):
            frame = tk.Frame(parent, bg=self.ui_palette["bg"])
            frame.pack(expand=True, fill="both", padx=self.ui_spacing["sm"], pady=self.ui_spacing["sm"])
            tree = ttk.Treeview(frame, columns=("Line Item", "Amount", "Notes"), show="headings", style="App.Treeview")
            tree.heading("Line Item", text="Line Item")
            tree.heading("Amount", text="Amount (VND)")
            tree.heading("Notes", text="Notes")
            tree.column("Line Item", anchor="w", width=340, stretch=True)
            tree.column("Amount", anchor="e", width=180, stretch=False)
            tree.column("Notes", anchor="w", width=540, stretch=True)
            tree.tag_configure("section", font=self.ui_typography["label_bold"])

            sort_state = {"column": None, "descending": False}

            def sort_tree_by(column_name, numeric=False):
                rows = []
                for item in tree.get_children(""):
                    value = tree.set(item, column_name)
                    if numeric:
                        cleaned = str(value).replace(",", "").replace(" VND", "").strip()
                        try:
                            key = float(cleaned)
                        except ValueError:
                            key = float("-inf")
                    else:
                        key = str(value).lower()
                    rows.append((item, key))

                descending = sort_state["column"] == column_name and not sort_state["descending"]
                rows.sort(key=lambda x: x[1], reverse=descending)
                for idx, (item, _key) in enumerate(rows):
                    tree.move(item, "", idx)

                sort_state["column"] = column_name
                sort_state["descending"] = descending

            tree.heading("Line Item", command=lambda: sort_tree_by("Line Item", numeric=False))
            tree.heading("Amount", command=lambda: sort_tree_by("Amount", numeric=True))
            tree.heading("Notes", command=lambda: sort_tree_by("Notes", numeric=False))

            y_scroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
            x_scroll = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
            tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
            tree.grid(row=0, column=0, sticky="nsew")
            y_scroll.grid(row=0, column=1, sticky="ns")
            x_scroll.grid(row=1, column=0, sticky="ew")
            frame.grid_rowconfigure(0, weight=1)
            frame.grid_columnconfigure(0, weight=1)
            return tree

        income_tree = build_statement_tree(income_tab)
        balance_tree = build_statement_tree(balance_tab)
        cash_tree = build_statement_tree(cash_tab)

        warning_panel = tk.Frame(
            self.content_area,
            bg=self.ui_state_colors["warning_bg"],
            highlightbackground=self.ui_state_colors["warning_border"],
            highlightthickness=1,
            bd=0,
        )
        warning_panel.pack(fill="x", padx=self.ui_spacing["md"], pady=(0, self.ui_spacing["sm"]))
        tk.Label(
            warning_panel,
            text="Reconciliation Warnings",
            bg=self.ui_state_colors["warning_bg"],
            fg=self.ui_state_colors["warning_text"],
            font=self.ui_typography["label_bold"],
            anchor="w",
        ).pack(fill="x", padx=self.ui_spacing["sm"], pady=(self.ui_spacing["xs"], 0))

        warnings_box = tk.Text(
            warning_panel,
            height=4,
            wrap="word",
            bg=self.ui_state_colors["warning_bg"],
            fg=self.ui_state_colors["warning_text"],
            relief="flat",
            borderwidth=0,
        )
        warnings_box.pack(fill="x", padx=self.ui_spacing["sm"], pady=(0, self.ui_spacing["xs"]))

        def set_quarters_for_year():
            chosen_year = int(year_var.get())
            choices = sorted(year_to_quarters.get(chosen_year, {1}), reverse=True)
            labels = [f"Q{q}" for q in choices]
            quarter_combo.configure(values=labels)
            if quarter_var.get() not in labels:
                quarter_var.set(labels[0])

        def update_period_controls():
            if period_type_var.get() == "Annual":
                quarter_combo.configure(state="disabled")
            else:
                quarter_combo.configure(state="readonly")

        def set_tree_rows(tree, rows):
            for item in tree.get_children():
                tree.delete(item)
            for line_item, amount, note in rows:
                tags = ("section",) if amount is None else ()
                tree.insert(
                    "",
                    "end",
                    values=(line_item, self.format_cell(amount, "money") if amount is not None else "", note or ""),
                    tags=tags,
                )

        def refresh_report():
            try:
                year = int(year_var.get())
                period_type = period_type_var.get()
                if period_type == "Annual":
                    label = f"{year} (Annual)"
                    income = self.fetch_annual_income_statement(year)
                    balance = self.fetch_annual_balance_sheet(year)
                    cash = self.fetch_annual_cash_flow(year)
                else:
                    quarter = int(str(quarter_var.get()).replace("Q", "").strip())
                    label = f"{year} Q{quarter}"
                    income = self.fetch_quarterly_income_statement(year, quarter)
                    balance = self.fetch_quarterly_balance_sheet(year, quarter)
                    cash = self.fetch_quarterly_cash_flow(year, quarter)

                income_rows = [
                    ("Period", None, label),
                    ("Revenue", income["revenue"], "Sales gross amount"),
                    ("Service Fee", income["service_fee"], "Supplementary service income"),
                    ("Shipping Fee", income["shipping_fee"], "Shipping income"),
                    ("Cost of Goods Sold (Estimated)", income["cogs"], "Weighted average stock cost for sold units"),
                    ("Gross Profit", income["gross_profit"], "Revenue - COGS"),
                    ("Operating Expenses", income["operating_expenses"], "From Costs table"),
                    ("Operating Profit", income["operating_profit"], "Gross Profit - Operating Expenses"),
                    ("Net Income", income["net_income"], "Current implementation uses operating profit"),
                ]
                set_tree_rows(income_tree, income_rows)

                balance_rows = [
                    ("Period End", None, balance["end_date"]),
                    ("Inventory Assets (Stocks)", balance["inventory_value"], f"On-hand units: {balance['inventory_units']}"),
                    ("Total Assets", balance["total_assets"], "Current company asset model"),
                    ("Accounts Payable", balance["accounts_payable"], "Open supplier invoices from Payables tab"),
                    ("VAT Payable", balance["vat_payable"], "Sales VAT minus purchase VAT"),
                    ("Total Liabilities", balance["total_liabilities"], "Basic liabilities"),
                    ("Retained Earnings", balance["retained_earnings"], "Cumulative net income to quarter end"),
                    ("Owner Equity (Auto-Balance)", balance["owner_equity"], "Balancing equity component"),
                    ("Total Equity", balance["total_equity"], "Owner Equity + Retained Earnings"),
                    ("Balance Check Delta", balance["equation_delta"], "Should be 0.00"),
                ]
                set_tree_rows(balance_tree, balance_rows)

                cash_rows = [
                    ("Period", None, label),
                    ("Beginning Cash", cash["beginning_cash"], "From latest timeline balance before quarter"),
                    ("Cash In", cash["cash_in"], "Timeline inflows during quarter"),
                    ("Cash Out", cash["cash_out"], "Timeline outflows during quarter"),
                    ("Net Cash Movement", cash["net_cash"], "Cash In - Cash Out"),
                    ("Ending Cash", cash["ending_cash"], "From latest timeline balance at quarter end"),
                ]
                set_tree_rows(cash_tree, cash_rows)

                # Rebuild charts for the selected year (annual data always used for charts)
                self.build_charts_tab(charts_tab, year)

                warnings = []
                warnings.extend(income.get("warnings", []))
                warnings.extend(balance.get("warnings", []))
                warnings.extend(cash.get("warnings", []))
                warnings = sorted(set(warnings))

                warnings_box.configure(state="normal")
                warnings_box.delete("1.0", "end")
                if warnings:
                    warnings_box.insert("end", "\n".join([f"- {item}" for item in warnings]))
                    status_var.set(f"Loaded {label} with {len(warnings)} warning(s)")
                else:
                    warnings_box.insert("end", "No reconciliation warnings for the selected period.")
                    status_var.set(f"Loaded {label} successfully")
                warnings_box.configure(state="disabled")
            except Exception as exc:
                status_var.set("Failed to load report")
                messagebox.showerror("Business Finance Report", f"Failed to load statements: {exc}")

        def export_annual_report():
            try:
                year = int(year_var.get())
                if period_type_var.get() != "Annual":
                    messagebox.showinfo(
                        "Annual Export",
                        "Switch Period Type to Annual before exporting the ASP-style annual CSV report.",
                    )
                    return

                default_name = f"annual_financial_report_{year}.csv"
                save_path = filedialog.asksaveasfilename(
                    title="Export Annual ASP-style CSV",
                    defaultextension=".csv",
                    filetypes=[("CSV files", "*.csv")],
                    initialfile=default_name,
                )
                if not save_path:
                    return

                output_path = self.export_annual_asp_report_csv(year, output_path=save_path)
                status_var.set(f"Exported annual CSV for {year}")

                checks = self.last_annual_export_checks or []
                passed = [item for item in checks if item[2]]
                failed = [item for item in checks if not item[2]]
                check_lines = [
                    f"- {name}: {'PASS' if ok else 'WARN'} (delta={delta:,.2f})"
                    for name, delta, ok in checks
                ]

                messagebox.showinfo(
                    "Annual Export",
                    "\n".join(
                        [
                            f"Annual ASP-style CSV exported successfully:\n{output_path}",
                            "",
                            f"Validation checks: {len(passed)} pass, {len(failed)} warning",
                            *check_lines,
                        ]
                    ),
                )
            except Exception as exc:
                messagebox.showerror("Annual Export", f"Failed to export annual CSV: {exc}")

        year_combo.bind("<<ComboboxSelected>>", lambda event: (set_quarters_for_year(), refresh_report()))
        period_type_combo.bind("<<ComboboxSelected>>", lambda event: (update_period_controls(), refresh_report()))
        quarter_combo.bind("<<ComboboxSelected>>", lambda event: refresh_report())

        tk.Button(
            action_row,
            text="Refresh",
            command=refresh_report,
            bg=self.ui_palette["accent"],
            fg="white",
            relief="flat",
            padx=12,
        ).pack(side="left", padx=(0, 6))

        tk.Button(
            action_row,
            text="Export Annual CSV",
            command=export_annual_report,
            bg=self.ui_palette["accent_alt"],
            fg="white",
            relief="flat",
            padx=12,
        ).pack(side="left", padx=6)

        tk.Button(
            action_row,
            text="Opening Balances",
            command=lambda: self.open_opening_balances_dialog(
                int(year_var.get()), on_saved=refresh_report
            ),
            bg="#607d8b",
            fg="white",
            relief="flat",
            padx=12,
        ).pack(side="left", padx=6)

        tk.Button(
            action_row,
            text="Adjust Values",
            command=lambda: self.open_export_adjustments_dialog(
                int(year_var.get()), on_saved=refresh_report
            ),
            bg="#e65100",
            fg="white",
            relief="flat",
            padx=12,
        ).pack(side="left", padx=6)

        def export_annual_pdf():
            try:
                year = int(year_var.get())
                if not REPORTLAB_OK:
                    messagebox.showwarning("PDF Export",
                        "reportlab is not installed. Run: pip install reportlab")
                    return
                default_name = f"annual_financial_report_{year}.pdf"
                save_path = filedialog.asksaveasfilename(
                    title="Export Annual PDF",
                    defaultextension=".pdf",
                    filetypes=[("PDF files", "*.pdf")],
                    initialfile=default_name,
                )
                if not save_path:
                    return
                output_path = self.export_annual_pdf_report(year, output_path=save_path)
                messagebox.showinfo("PDF Export",
                    f"Annual PDF exported successfully:\n{output_path}")
                status_var.set(f"PDF exported for {year}")
            except Exception as exc:
                messagebox.showerror("PDF Export", f"Failed to export PDF: {exc}")

        tk.Button(
            action_row,
            text="Export Annual PDF",
            command=export_annual_pdf,
            bg="#6a1b9a",
            fg="white",
            relief="flat",
            padx=12,
        ).pack(side="left", padx=6)

        set_quarters_for_year()
        update_period_controls()
        refresh_report()

    def format_cell(self, value, fmt_type):
        if value is None:
            return ""
        if fmt_type == "date":
            return str(value)
        if fmt_type == "int":
            try:
                return f"{int(value):,}"
            except (ValueError, TypeError):
                return str(value)
        if fmt_type == "money":
            try:
                return f"{float(value):,.2f}"
            except (ValueError, TypeError):
                return str(value)
        return str(value)

    def create_data_tab(self, notebook, title, columns, query, formatters=None):
        frame = tk.Frame(notebook, bg=self.ui_palette["bg"])
        notebook.add(frame, text=title)

        filter_frame = tk.Frame(frame, bg=self.ui_palette["bg"])
        filter_frame.pack(fill="x", padx=10, pady=(10, 0))
        tk.Label(
            filter_frame,
            text="Search:",
            bg=self.ui_palette["bg"],
            fg=self.ui_palette["text"],
            font=self.ui_typography["label"],
        ).pack(side="left")
        filter_var = tk.StringVar()
        filter_entry = tk.Entry(filter_frame, textvariable=filter_var, width=40)
        filter_entry.pack(side="left", padx=8)

        tk.Label(
            filter_frame,
            text="In:",
            bg=self.ui_palette["bg"],
            fg=self.ui_palette["text"],
            font=self.ui_typography["label"],
        ).pack(side="left", padx=(4, 4))
        search_columns = ["All Columns", *columns]
        search_col_var = tk.StringVar(value="All Columns")
        search_col_combo = ttk.Combobox(
            filter_frame,
            textvariable=search_col_var,
            values=search_columns,
            state="readonly",
            width=18,
        )
        search_col_combo.pack(side="left", padx=(0, 8))

        table_frame = tk.Frame(frame, bg=self.ui_palette["bg"])
        table_frame.pack(expand=True, fill="both", padx=10, pady=10)

        tree = ttk.Treeview(table_frame, columns=columns, show="headings", style="App.Treeview")
        y_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
        x_scroll = ttk.Scrollbar(table_frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        formatters = formatters or {}
        all_rows = []
        current_rows = []
        sort_state = {"column": None, "descending": False}

        for col in columns:
            tree.heading(col, text=col)
            col_name = str(col).strip().lower()
            is_numeric = any(token in col_name for token in (
                "amount", "price", "gross", "tax", "fee", "units", "total", "%"
            ))
            is_date_id = any(token in col_name for token in ("date", "id", "order"))
            if is_numeric:
                tree.column(col, width=130, anchor="e", stretch=False)
            elif is_date_id:
                tree.column(col, width=130, anchor="w", stretch=False)
            else:
                tree.column(col, width=180, anchor="w", stretch=True)

        tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")

        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        sku_col_indexes = {
            idx + 1
            for idx, col in enumerate(columns)
            if "sku" in str(col).strip().lower()
        }

        try:
            conn = sqlite3.connect(FINANCIAL_DB)
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            conn.close()

            for row in rows:
                formatted = []
                for col_name, value in zip(columns, row):
                    fmt = formatters.get(col_name)
                    formatted.append(self.format_cell(value, fmt) if fmt else ("" if value is None else value))
                all_rows.append(formatted)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load {title} data: {e}")

        def render_rows(filtered_rows):
            current_rows.clear()
            current_rows.extend(filtered_rows)
            for item in tree.get_children():
                tree.delete(item)
            for row in filtered_rows:
                tree.insert("", "end", values=row)

        def on_filter(*args):
            term = filter_var.get().strip().lower()
            selected_col = search_col_var.get()
            if not term:
                render_rows(all_rows)
                return
            filtered = []
            for row in all_rows:
                if selected_col == "All Columns":
                    haystack = " ".join([str(v).lower() for v in row if v is not None])
                else:
                    idx = columns.index(selected_col)
                    haystack = str(row[idx]).lower() if idx < len(row) and row[idx] is not None else ""
                if term in haystack:
                    filtered.append(row)
            render_rows(filtered)

        def sort_rows_by_column(col_name):
            if col_name not in columns:
                return
            col_idx = columns.index(col_name)
            descending = sort_state["column"] == col_name and not sort_state["descending"]

            def sort_key(row):
                val = row[col_idx] if col_idx < len(row) else ""
                txt = str(val).replace(",", "").replace(" VND", "").strip()
                try:
                    return (0, float(txt))
                except ValueError:
                    return (1, str(val).lower())

            all_rows.sort(key=sort_key, reverse=descending)
            sort_state["column"] = col_name
            sort_state["descending"] = descending
            on_filter()

        for col in columns:
            tree.heading(col, text=col, command=lambda c=col: sort_rows_by_column(c))

        def export_visible_rows_csv():
            try:
                default_name = f"{str(title).strip().lower().replace(' ', '_')}_view.csv"
                save_path = filedialog.asksaveasfilename(
                    title=f"Export {title} table",
                    defaultextension=".csv",
                    filetypes=[("CSV files", "*.csv")],
                    initialfile=default_name,
                )
                if not save_path:
                    return
                with open(save_path, "w", newline="", encoding="utf-8-sig") as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(columns)
                    writer.writerows(current_rows)
                messagebox.showinfo("Export CSV", f"Exported {len(current_rows)} row(s) to:\n{save_path}")
            except Exception as exc:
                messagebox.showerror("Export CSV", f"Failed to export table: {exc}")

        def on_tree_hover(event):
            if not sku_col_indexes:
                return
            row_id = tree.identify_row(event.y)
            if not row_id:
                self.schedule_sku_preview_hide()
                return
            column_id = tree.identify_column(event.x)
            try:
                col_index = int(str(column_id).replace("#", ""))
            except Exception:
                self.schedule_sku_preview_hide()
                return
            if col_index not in sku_col_indexes:
                self.schedule_sku_preview_hide()
                return
            values = tree.item(row_id).get("values", [])
            if col_index - 1 >= len(values):
                self.schedule_sku_preview_hide()
                return
            sku = str(values[col_index - 1]).strip()
            if not sku:
                self.schedule_sku_preview_hide()
                return
            self.show_sku_preview(sku, event.x_root, event.y_root)

        tree.bind("<Motion>", on_tree_hover)
        tree.bind("<Leave>", lambda event: self.schedule_sku_preview_hide())

        filter_var.trace_add("write", on_filter)
        search_col_combo.bind("<<ComboboxSelected>>", lambda event: on_filter())

        tk.Button(
            filter_frame,
            text="Export View CSV",
            command=export_visible_rows_csv,
            bg=self.ui_palette["accent_alt"],
            fg="white",
            relief="flat",
            padx=10,
        ).pack(side="right")

        render_rows(all_rows)

    def build_sales_records_panel(self, frame, enable_edit=False, palette=None, period_filter_provider=None):
        palette = palette or self.ui_palette
        filter_frame = tk.Frame(frame, bg=palette["bg"])
        filter_frame.pack(fill="x", padx=10, pady=(10, 0))
        tk.Label(
            filter_frame,
            text="Search:",
            bg=palette["bg"],
            fg=palette["text"],
            font=("Segoe UI", 9),
        ).pack(side="left")
        filter_var = tk.StringVar()
        filter_entry = tk.Entry(filter_frame, textvariable=filter_var, width=40)
        filter_entry.pack(side="left", padx=8)

        table_frame = tk.Frame(frame, bg=palette["bg"])
        table_frame.pack(expand=True, fill="both", padx=10, pady=10)

        columns = (
            "ID", "Date", "Order ID", "Channel", "SKU", "Units", "Unit Price", "Gross",
            "Tax %", "Tax Amount", "Service Fee", "Shipping", "Total Price", "Note", "Approved By", "Approved At"
        )
        tree = ttk.Treeview(table_frame, columns=columns, show="headings", style="App.Treeview")
        y_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
        x_scroll = ttk.Scrollbar(table_frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=120, anchor="w")

        tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")

        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        all_rows = []
        _hide_on_reload = [None]  # set to hide_edit_btn_now when enable_edit=True

        def load_sales_rows():
            all_rows.clear()
            fn = _hide_on_reload[0]
            if fn:
                fn()
            try:
                conn = sqlite3.connect(FINANCIAL_DB)
                cursor = conn.cursor()
                query = """
                    SELECT id, sale_date, order_id, channel, product_sku, units_sold, unit_price,
                           gross_sales, vat_rate, vat_amount, service_fee, shipping_fee, note, approved_by, approved_at
                    FROM Sales
                """
                params = []
                if callable(period_filter_provider):
                    period_filter = period_filter_provider() or {}
                    start_date = period_filter.get("start_date")
                    end_date = period_filter.get("end_date")
                    if start_date and end_date:
                        query += " WHERE sale_date BETWEEN ? AND ?"
                        params.extend([start_date, end_date])
                query += " ORDER BY sale_date DESC, id DESC"
                cursor.execute(query, tuple(params))
                rows = cursor.fetchall()
                conn.close()

                # Build username lookup for approved_by from SECURITY_DB
                approver_ids = list({row[13] for row in rows if row[13] is not None})
                user_map = {}
                if approver_ids:
                    try:
                        sec_conn = sqlite3.connect(SECURITY_DB)
                        sec_cursor = sec_conn.cursor()
                        placeholders = ",".join("?" * len(approver_ids))
                        sec_cursor.execute(
                            f"SELECT user_id, username FROM Users WHERE user_id IN ({placeholders})",
                            approver_ids,
                        )
                        user_map = {r[0]: r[1] for r in sec_cursor.fetchall()}
                        sec_conn.close()
                    except Exception:
                        pass

                for row in rows:
                    approved_by_display = user_map.get(row[13], str(row[13]) if row[13] is not None else "")
                    tax_rate_display = f"{row[8]:.1f}%" if row[8] is not None else ""
                    total_price = (row[7] or 0.0) + (row[10] or 0.0) + (row[11] or 0.0)
                    all_rows.append([
                        row[0],
                        self.format_cell(row[1], "date"),
                        "" if row[2] is None else row[2],
                        "" if row[3] is None else row[3],
                        "" if row[4] is None else row[4],
                        self.format_cell(row[5], "int"),
                        self.format_cell(row[6], "money"),
                        self.format_cell(row[7], "money"),
                        tax_rate_display,
                        self.format_cell(row[9], "money"),
                        self.format_cell(row[10], "money"),
                        self.format_cell(row[11], "money"),
                        self.format_cell(total_price, "money"),
                        "" if row[12] is None else row[12],
                        approved_by_display,
                        "" if row[14] is None else str(row[14]),
                    ])
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load Sales data: {e}")

            on_filter()

        def render_rows(filtered_rows):
            for item in tree.get_children():
                tree.delete(item)
            for row in filtered_rows:
                tree.insert("", "end", values=row)

        def on_filter(*args):
            term = filter_var.get().strip().lower()
            if not term:
                render_rows(all_rows)
                return
            filtered = []
            for row in all_rows:
                joined = " ".join([str(v).lower() for v in row if v is not None])
                if term in joined:
                    filtered.append(row)
            render_rows(filtered)

        # Base hover handler (SKU preview only); overridden below when enable_edit=True
        def on_tree_hover(event):
            row_id = tree.identify_row(event.y)
            if not row_id:
                self.schedule_sku_preview_hide()
                return
            column_id = tree.identify_column(event.x)
            try:
                col_index = int(str(column_id).replace("#", ""))
            except Exception:
                self.schedule_sku_preview_hide()
                return
            if col_index != 5:
                self.schedule_sku_preview_hide()
                return
            values = tree.item(row_id).get("values", [])
            if col_index - 1 >= len(values):
                self.schedule_sku_preview_hide()
                return
            sku = str(values[col_index - 1]).strip()
            if not sku:
                self.schedule_sku_preview_hide()
                return
            self.show_sku_preview(sku, event.x_root, event.y_root)

        if enable_edit:
            edit_btn = None
            edit_btn_hide_job = {"id": None}

            def cancel_edit_btn_hide():
                if edit_btn_hide_job["id"] is not None:
                    try:
                        self.root.after_cancel(edit_btn_hide_job["id"])
                    except Exception:
                        pass
                    edit_btn_hide_job["id"] = None

            def hide_edit_btn_now():
                cancel_edit_btn_hide()
                if edit_btn is not None:
                    edit_btn.place_forget()

            _hide_on_reload[0] = hide_edit_btn_now

            def schedule_edit_btn_hide(delay_ms=120):
                if edit_btn is None:
                    return
                cancel_edit_btn_hide()
                edit_btn_hide_job["id"] = self.root.after(delay_ms, hide_edit_btn_now)

            def open_sales_edit_for_id(sid):
                if not self.can_request_sales_log_edit():
                    messagebox.showerror("Access Denied", "Only Level 2, 3, or 4 can submit Sales edit requests.")
                    return
                self.open_sales_edit_dialog(sid, on_submitted=load_sales_rows)

            def show_edit_btn_for_row(row_id, fallback_y=None):
                if edit_btn is None:
                    return False
                values = tree.item(row_id).get("values", []) if row_id else []
                sale_id = self.parse_int_input(values[0]) if values else None
                if not sale_id:
                    return False
                edit_btn.configure(
                    text=f"Edit #{sale_id}",
                    command=lambda sid=sale_id: open_sales_edit_for_id(sid),
                )
                bbox = tree.bbox(row_id, "#1")
                if bbox:
                    _, y, _, h = bbox
                    y_pos = max(0, y + (h - 24) // 2)
                else:
                    y_pos = max(0, (fallback_y or 0) - 12)
                edit_btn.place(x=4, y=y_pos)
                return True

            if self.can_request_sales_log_edit():
                edit_btn = tk.Button(
                    table_frame,
                    text="Edit",
                    bg="#4CAF50",
                    fg="white",
                    font=("Segoe UI", 8, "bold"),
                    relief="flat",
                    padx=6,
                    pady=2,
                    cursor="hand2",
                )
                edit_btn.bind("<Enter>", lambda e: cancel_edit_btn_hide())
                edit_btn.bind("<Leave>", lambda e: schedule_edit_btn_hide())

            # Override hover handler to also drive floating edit button
            def on_tree_hover(event):
                row_id = tree.identify_row(event.y)
                if not row_id:
                    self.schedule_sku_preview_hide()
                    schedule_edit_btn_hide()
                    return
                cancel_edit_btn_hide()
                show_edit_btn_for_row(row_id, event.y)
                column_id = tree.identify_column(event.x)
                try:
                    col_index = int(str(column_id).replace("#", ""))
                except Exception:
                    self.schedule_sku_preview_hide()
                    return
                if col_index != 5:
                    self.schedule_sku_preview_hide()
                    return
                values = tree.item(row_id).get("values", [])
                if col_index - 1 >= len(values):
                    self.schedule_sku_preview_hide()
                    return
                sku = str(values[col_index - 1]).strip()
                if not sku:
                    self.schedule_sku_preview_hide()
                    return
                self.show_sku_preview(sku, event.x_root, event.y_root)

            # --- context menu ---
            context_target = {"sale_id": None, "sku": "", "order_id": ""}

            def set_context_target(row_id):
                if not row_id:
                    return
                values = tree.item(row_id).get("values", [])
                if not values or len(values) < 5:
                    return
                sale_id = self.parse_int_input(values[0])
                if not sale_id:
                    return
                context_target["sale_id"] = sale_id
                context_target["order_id"] = str(values[2]).strip() if values[2] is not None else ""
                context_target["sku"] = str(values[4]).strip() if values[4] is not None else ""

            def edit_sale_from_context():
                sid = context_target.get("sale_id")
                if not sid:
                    return
                open_sales_edit_for_id(sid)

            def view_sku_image_from_context():
                sku = context_target.get("sku", "")
                if not sku:
                    messagebox.showinfo("No SKU", "No SKU available for this row.")
                    return
                self.show_sku_preview(sku, self.root.winfo_pointerx(), self.root.winfo_pointery())

            def copy_sku_from_context():
                sku = context_target.get("sku", "")
                try:
                    self.root.clipboard_clear()
                    self.root.clipboard_append(sku)
                except tk.TclError:
                    pass

            def copy_sale_id_from_context():
                sid = context_target.get("sale_id")
                if sid is None:
                    return
                try:
                    self.root.clipboard_clear()
                    self.root.clipboard_append(str(sid))
                except tk.TclError:
                    pass

            def copy_order_id_from_context():
                oid = context_target.get("order_id", "")
                try:
                    self.root.clipboard_clear()
                    self.root.clipboard_append(oid)
                except tk.TclError:
                    pass

            context_menu = tk.Menu(tree, tearoff=0)
            context_menu.add_command(label="Edit Sale (Submit for Approval)", command=edit_sale_from_context)
            context_menu.add_separator()
            context_menu.add_command(label="View SKU Image", command=view_sku_image_from_context)
            context_menu.add_command(label="Copy SKU", command=copy_sku_from_context)
            context_menu.add_command(label="Copy Order ID", command=copy_order_id_from_context)
            context_menu.add_command(label="Copy Sale ID", command=copy_sale_id_from_context)

            def on_detail_right_click(event):
                hide_edit_btn_now()
                row_id = tree.identify_row(event.y)
                if row_id:
                    tree.selection_set(row_id)
                    tree.focus(row_id)
                    set_context_target(row_id)
                can_edit = self.can_request_sales_log_edit() and context_target.get("sale_id") is not None
                context_menu.entryconfig(
                    "Edit Sale (Submit for Approval)",
                    state="normal" if can_edit else "disabled",
                )
                try:
                    context_menu.tk_popup(event.x_root, event.y_root)
                finally:
                    context_menu.grab_release()

            def on_detail_select(event):
                selection = tree.selection()
                if selection:
                    set_context_target(selection[0])

            def on_wheel_scroll(event):
                schedule_edit_btn_hide(0)

            tree.bind("<<TreeviewSelect>>", on_detail_select)
            tree.bind("<Button-3>", on_detail_right_click)
            tree.bind("<Button-2>", on_detail_right_click)
            tree.bind("<Control-Button-1>", on_detail_right_click)
            tree.bind("<MouseWheel>", on_wheel_scroll)
            tree.bind("<Button-4>", on_wheel_scroll)
            tree.bind("<Button-5>", on_wheel_scroll)
            tree.bind("<Leave>", lambda event: (self.schedule_sku_preview_hide(), schedule_edit_btn_hide()))

        filter_var.trace_add("write", on_filter)
        tree.bind("<Motion>", on_tree_hover)
        if not enable_edit:
            tree.bind("<Leave>", lambda event: self.schedule_sku_preview_hide())
        load_sales_rows()
        return {"refresh": load_sales_rows, "tree": tree}

    def build_cost_records_panel(self, frame, enable_edit=False, palette=None, period_filter_provider=None):
        palette = palette or self.ui_palette
        filter_frame = tk.Frame(frame, bg=palette["bg"])
        filter_frame.pack(fill="x", padx=10, pady=(10, 0))
        tk.Label(
            filter_frame,
            text="Search:",
            bg=palette["bg"],
            fg=palette["text"],
            font=("Segoe UI", 9),
        ).pack(side="left")
        filter_var = tk.StringVar()
        filter_entry = tk.Entry(filter_frame, textvariable=filter_var, width=40)
        filter_entry.pack(side="left", padx=8)

        table_frame = tk.Frame(frame, bg=palette["bg"])
        table_frame.pack(expand=True, fill="both", padx=10, pady=10)

        columns = ("ID", "Date", "Type", "Amount", "VAT %", "VAT Amount", "Total Incl. VAT", "Note")
        tree = ttk.Treeview(table_frame, columns=columns, show="headings", style="App.Treeview")
        y_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
        x_scroll = ttk.Scrollbar(table_frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=140, anchor="w")
        tree.column("Amount", anchor="e")
        tree.column("VAT %", anchor="e")
        tree.column("VAT Amount", anchor="e")
        tree.column("Total Incl. VAT", anchor="e")

        tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")

        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        all_rows = []

        def load_cost_rows():
            all_rows.clear()
            try:
                conn = sqlite3.connect(FINANCIAL_DB)
                cursor = conn.cursor()
                query = """
                    SELECT id, cost_date, cost_type, amount, vat_rate, vat_amount, note
                    FROM Costs
                """
                params = []
                if callable(period_filter_provider):
                    period_filter = period_filter_provider() or {}
                    start_date = period_filter.get("start_date")
                    end_date = period_filter.get("end_date")
                    if start_date and end_date:
                        query += " WHERE cost_date BETWEEN ? AND ?"
                        params.extend([start_date, end_date])
                query += " ORDER BY cost_date DESC, id DESC"
                cursor.execute(query, tuple(params))
                rows = cursor.fetchall()
                conn.close()

                for row in rows:
                    amount = self.parse_float_input(row[3]) or 0.0
                    vat_rate = self.parse_float_input(row[4])
                    vat_amount = self.parse_float_input(row[5])
                    if vat_amount is None and vat_rate is not None:
                        vat_amount = round(amount * vat_rate / 100.0, 2)
                    vat_amount = vat_amount or 0.0
                    total_incl = amount + vat_amount
                    all_rows.append([
                        row[0],
                        self.format_cell(row[1], "date"),
                        "" if row[2] is None else row[2],
                        self.format_cell(amount, "money"),
                        "" if vat_rate is None else f"{vat_rate:.2f}%",
                        self.format_cell(vat_amount, "money"),
                        self.format_cell(total_incl, "money"),
                        "" if row[6] is None else row[6],
                    ])
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load Costs data: {e}")

            on_filter()

        def render_rows(filtered_rows):
            for item in tree.get_children():
                tree.delete(item)
            for row in filtered_rows:
                tree.insert("", "end", values=row)

        def on_filter(*args):
            term = filter_var.get().strip().lower()
            if not term:
                render_rows(all_rows)
                return
            filtered = []
            for row in all_rows:
                joined = " ".join([str(v).lower() for v in row if v is not None])
                if term in joined:
                    filtered.append(row)
            render_rows(filtered)

        if enable_edit:
            context_target = {"cost_id": None, "cost_type": "", "amount": "", "note": ""}

            def set_context_target(row_id):
                if not row_id:
                    context_target["cost_id"] = None
                    context_target["cost_type"] = ""
                    context_target["amount"] = ""
                    context_target["note"] = ""
                    return
                values = tree.item(row_id).get("values", [])
                if not values or len(values) < 8:
                    context_target["cost_id"] = None
                    context_target["cost_type"] = ""
                    context_target["amount"] = ""
                    context_target["note"] = ""
                    return
                cost_id = self.parse_int_input(values[0])
                if not cost_id:
                    context_target["cost_id"] = None
                    context_target["cost_type"] = ""
                    context_target["amount"] = ""
                    context_target["note"] = ""
                    return
                context_target["cost_id"] = cost_id
                context_target["cost_type"] = str(values[2]).strip() if values[2] is not None else ""
                context_target["amount"] = str(values[3]).strip() if values[3] is not None else ""
                context_target["note"] = str(values[7]).strip() if values[7] is not None else ""

            def submit_cost_edit_request():
                if not self.can_request_cost_log_edit():
                    messagebox.showerror("Access Denied", "Only Level 2, 3, or 4 can submit Cost edit requests.")
                    return
                selection = tree.selection()
                if not selection:
                    messagebox.showwarning("Warning", "Select a Cost row to edit.")
                    return
                item = tree.item(selection[0])
                cost_id = self.parse_int_input(item["values"][0])
                if not cost_id:
                    messagebox.showerror("Error", "Unable to determine Cost record ID.")
                    return
                self.open_cost_edit_dialog(cost_id, on_submitted=load_cost_rows)

            def edit_cost_from_context():
                cost_id = context_target.get("cost_id")
                if not cost_id:
                    return
                if not self.can_request_cost_log_edit():
                    messagebox.showerror("Access Denied", "Only Level 2, 3, or 4 can submit Cost edit requests.")
                    return
                self.open_cost_edit_dialog(cost_id, on_submitted=load_cost_rows)

            def view_note_from_context():
                note = context_target.get("note", "")
                if not note:
                    messagebox.showinfo("Note", "No note available for this row.")
                    return
                messagebox.showinfo("Cost Note", note)

            def copy_cost_id_from_context():
                cost_id = context_target.get("cost_id")
                if cost_id is None:
                    return
                try:
                    self.root.clipboard_clear()
                    self.root.clipboard_append(str(cost_id))
                except tk.TclError:
                    pass

            def copy_cost_type_from_context():
                cost_type = context_target.get("cost_type", "")
                try:
                    self.root.clipboard_clear()
                    self.root.clipboard_append(cost_type)
                except tk.TclError:
                    pass

            def copy_amount_from_context():
                amount = context_target.get("amount", "")
                try:
                    self.root.clipboard_clear()
                    self.root.clipboard_append(amount)
                except tk.TclError:
                    pass

            context_menu = tk.Menu(tree, tearoff=0)
            context_menu.add_command(label="Edit Cost (Submit for Approval)", command=edit_cost_from_context)
            context_menu.add_separator()
            context_menu.add_command(label="View Note", command=view_note_from_context)
            context_menu.add_command(label="Copy Cost ID", command=copy_cost_id_from_context)
            context_menu.add_command(label="Copy Cost Type", command=copy_cost_type_from_context)
            context_menu.add_command(label="Copy Amount", command=copy_amount_from_context)

            def on_cost_right_click(event):
                row_id = tree.identify_row(event.y)
                if row_id:
                    tree.selection_set(row_id)
                    tree.focus(row_id)
                    set_context_target(row_id)
                can_edit = self.can_request_cost_log_edit() and context_target.get("cost_id") is not None
                context_menu.entryconfig(
                    "Edit Cost (Submit for Approval)",
                    state="normal" if can_edit else "disabled",
                )
                try:
                    context_menu.tk_popup(event.x_root, event.y_root)
                finally:
                    context_menu.grab_release()

            def on_cost_select(event=None):
                selection = tree.selection()
                if selection:
                    set_context_target(selection[0])

            tree.bind("<<TreeviewSelect>>", on_cost_select)
            tree.bind("<Button-3>", on_cost_right_click)
            tree.bind("<Button-2>", on_cost_right_click)
            tree.bind("<Control-Button-1>", on_cost_right_click)

            action_frame = tk.Frame(frame, bg=palette["bg"])
            action_frame.pack(fill="x", padx=10, pady=(0, 10))
            edit_btn = tk.Button(
                action_frame,
                text="Edit Selected Cost (Submit for Approval)",
                command=submit_cost_edit_request,
                bg="#4CAF50",
                fg="white",
                width=34,
            )
            if self.can_request_cost_log_edit():
                edit_btn.pack(side="left")
            else:
                edit_btn.configure(state="disabled")
                edit_btn.pack(side="left")

        filter_var.trace_add("write", on_filter)
        load_cost_rows()
        return {"refresh": load_cost_rows, "tree": tree}

    def create_sales_records_tab(self, notebook):
        frame = tk.Frame(notebook, bg=self.ui_palette["bg"])
        notebook.add(frame, text="Sales")
        self.build_sales_records_panel(frame, enable_edit=False)

    def open_sales_edit_dialog(self, sale_id, on_submitted=None):
        sale = self.get_sales_row_by_id(sale_id)
        if not sale:
            messagebox.showerror("Error", f"Sales record #{sale_id} not found.")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title(f"Edit Sales #{sale_id}")
        dialog.configure(bg="#f5f6f8")
        dialog.transient(self.root)
        dialog.grab_set()

        form_frame = tk.Frame(dialog, bg="#f5f6f8")
        form_frame.pack(fill="both", expand=True, padx=12, pady=12)

        def _sales_section(text, row):
            tk.Frame(form_frame, bg=self.ui_state_colors["neutral_border"], height=1).grid(
                row=row, column=0, columnspan=2, sticky="ew", padx=4, pady=(8, 0))
            tk.Label(form_frame, text=text, bg="#f5f6f8", fg=self.ui_palette["accent"],
                     font=("Segoe UI", 8, "bold")).grid(
                row=row+1, column=0, columnspan=2, sticky="w", padx=4, pady=(2, 4))

        managed_sales_tax_rates = (0.0, 8.0, 10.0)
        field_vars = {}
        row_idx = 0

        _sales_section("SALE INFO", row_idx);  row_idx += 2
        sale_info_specs = [("Sale Date *", "sale_date"), ("Order ID", "order_id"), ("Channel", "channel")]
        for label, key in sale_info_specs:
            tk.Label(form_frame, text=f"{label}:", bg="#f5f6f8").grid(row=row_idx, column=0, sticky="e", padx=6, pady=3)
            value = sale.get(key)
            var = tk.StringVar(value="" if value is None else str(value))
            tk.Entry(form_frame, textvariable=var, width=24).grid(row=row_idx, column=1, sticky="w", padx=6, pady=3)
            field_vars[key] = var
            row_idx += 1

        _sales_section("PRODUCT & PRICING", row_idx);  row_idx += 2
        pricing_specs = [("Product SKU *", "product_sku"), ("Units Sold *", "units_sold"), ("Unit Price *", "unit_price")]
        for label, key in pricing_specs:
            tk.Label(form_frame, text=f"{label}:", bg="#f5f6f8").grid(row=row_idx, column=0, sticky="e", padx=6, pady=3)
            value = sale.get(key)
            var = tk.StringVar(value="" if value is None else str(value))
            tk.Entry(form_frame, textvariable=var, width=24).grid(row=row_idx, column=1, sticky="w", padx=6, pady=3)
            field_vars[key] = var
            row_idx += 1
        # Tax %
        tk.Label(form_frame, text="Tax % *:", bg="#f5f6f8").grid(row=row_idx, column=0, sticky="e", padx=6, pady=3)
        vat_val = sale.get("vat_rate")
        vat_var = tk.StringVar(value="8.0" if vat_val is None else str(vat_val))
        ttk.Combobox(form_frame, textvariable=vat_var,
                     values=[str(r) for r in managed_sales_tax_rates],
                     state="readonly", width=10).grid(row=row_idx, column=1, sticky="w", padx=6, pady=3)
        field_vars["vat_rate"] = vat_var
        row_idx += 1
        # Gross Sales (readonly, auto-computed)
        tk.Label(form_frame, text="Gross Sales (auto):", bg="#f5f6f8").grid(row=row_idx, column=0, sticky="e", padx=6, pady=3)
        gs_var = tk.StringVar(value="" if sale.get("gross_sales") is None else str(sale.get("gross_sales")))
        gs_entry = tk.Entry(form_frame, textvariable=gs_var, width=24, state="readonly",
                            readonlybackground="#f3f4f6", fg="#64748b")
        gs_entry.grid(row=row_idx, column=1, sticky="w", padx=6, pady=3)
        field_vars["gross_sales"] = gs_var
        row_idx += 1

        _sales_section("FEES & NOTE", row_idx);  row_idx += 2
        fee_specs = [("Service Fee", "service_fee"), ("Shipping Fee", "shipping_fee"), ("Note", "note")]
        for label, key in fee_specs:
            tk.Label(form_frame, text=f"{label}:", bg="#f5f6f8").grid(row=row_idx, column=0, sticky="e", padx=6, pady=3)
            value = sale.get(key)
            var = tk.StringVar(value="" if value is None else str(value))
            width = 48 if key == "note" else 24
            tk.Entry(form_frame, textvariable=var, width=width).grid(row=row_idx, column=1, sticky="w", padx=6, pady=3)
            field_vars[key] = var
            row_idx += 1

        _sales_section("REASON", row_idx);  row_idx += 2
        reason_var = tk.StringVar()
        tk.Label(form_frame, text="Edit Reason *:", bg="#f5f6f8").grid(row=row_idx, column=0, sticky="e", padx=6, pady=3)
        tk.Entry(form_frame, textvariable=reason_var, width=48).grid(row=row_idx, column=1, sticky="w", padx=6, pady=3)
        row_idx += 1

        # Gross Sales is tax-inclusive and derived from Unit Price, Units Sold, and Tax %.
        def recompute_gross_sales(*_args):
            unit_price = self.parse_float_input(field_vars["unit_price"].get())
            units_sold = self.parse_int_input(field_vars["units_sold"].get())
            vat_rate = self.parse_float_input(field_vars["vat_rate"].get())
            if unit_price is None or units_sold is None or vat_rate is None:
                field_vars["gross_sales"].set("")
                return
            if vat_rate not in managed_sales_tax_rates:
                field_vars["gross_sales"].set("")
                return
            pre_tax_total = unit_price * units_sold
            gross_sales = round(pre_tax_total * (100.0 + vat_rate) / 100.0, 2)
            field_vars["gross_sales"].set(f"{gross_sales:.2f}")

        field_vars["unit_price"].trace_add("write", recompute_gross_sales)
        field_vars["units_sold"].trace_add("write", recompute_gross_sales)
        field_vars["vat_rate"].trace_add("write", recompute_gross_sales)
        recompute_gross_sales()

        def submit_request():
            sale_date = self.parse_date_input(field_vars["sale_date"].get())
            if not sale_date:
                messagebox.showerror("Error", "Sale Date is required and must be YYYY-MM-DD.")
                return

            sku = field_vars["product_sku"].get().strip()
            if sku and not self.product_exists(sku):
                messagebox.showerror("Error", f"Product SKU '{sku}' does not exist.")
                return

            units_sold = self.parse_int_input(field_vars["units_sold"].get())
            if units_sold is None:
                messagebox.showerror("Error", "Units Sold must be a valid integer.")
                return

            numeric_keys = ["unit_price", "vat_rate", "service_fee", "shipping_fee"]
            parsed_numeric = {}
            for key in numeric_keys:
                parsed = self.parse_float_input(field_vars[key].get())
                if parsed is None:
                    messagebox.showerror("Error", f"{key.replace('_', ' ').title()} must be a valid number.")
                    return
                parsed_numeric[key] = parsed

            vat_rate = parsed_numeric["vat_rate"]
            if vat_rate not in managed_sales_tax_rates:
                allowed_text = ", ".join([f"{int(rate)}%" if float(rate).is_integer() else f"{rate}%" for rate in managed_sales_tax_rates])
                messagebox.showerror("Error", f"Tax % must be one of: {allowed_text}.")
                return

            pre_tax_total = parsed_numeric["unit_price"] * units_sold
            gross_sales = round(pre_tax_total * (100.0 + vat_rate) / 100.0, 2)
            vat_amount = round(gross_sales * vat_rate / (100.0 + vat_rate), 2) if vat_rate > 0 else 0.0

            reason = reason_var.get().strip()
            if not reason:
                messagebox.showerror("Error", "Edit Reason is required.")
                return

            before = {
                "sale_date": sale.get("sale_date"),
                "order_id": sale.get("order_id"),
                "channel": sale.get("channel"),
                "product_sku": sale.get("product_sku"),
                "units_sold": sale.get("units_sold"),
                "unit_price": sale.get("unit_price"),
                "gross_sales": sale.get("gross_sales"),
                "vat_rate": sale.get("vat_rate"),
                "vat_amount": sale.get("vat_amount"),
                "service_fee": sale.get("service_fee"),
                "shipping_fee": sale.get("shipping_fee"),
                "note": sale.get("note"),
                "total_price": (sale.get("gross_sales") or 0.0) + (sale.get("service_fee") or 0.0) + (sale.get("shipping_fee") or 0.0),
            }
            after = {
                "sale_date": sale_date,
                "order_id": field_vars["order_id"].get().strip() or None,
                "channel": field_vars["channel"].get().strip() or None,
                "product_sku": sku or None,
                "units_sold": units_sold,
                "unit_price": parsed_numeric["unit_price"],
                "gross_sales": gross_sales,
                "vat_rate": parsed_numeric["vat_rate"],
                "vat_amount": vat_amount,
                "service_fee": parsed_numeric["service_fee"],
                "shipping_fee": parsed_numeric["shipping_fee"],
                "note": field_vars["note"].get().strip() or None,
                "total_price": gross_sales + parsed_numeric["service_fee"] + parsed_numeric["shipping_fee"],
            }
            changed_fields = [key for key in after.keys() if str(before.get(key)) != str(after.get(key))]
            if not changed_fields:
                messagebox.showinfo("No Changes", "No field was changed.")
                return

            payload = {
                "sale_id": sale_id,
                "before": before,
                "after": after,
                "changed_fields": changed_fields,
                "reason": reason,
                "submitted_by_level": self.current_level,
                "submitted_at": datetime.now().isoformat(timespec="seconds"),
            }
            pending_id = self.submit_pending_entry("SalesEdit", payload)
            self.log_action(
                "SUBMIT_SALES_EDIT",
                f"SalesEdit pending #{pending_id} for sale #{sale_id}; changed={','.join(changed_fields)}",
            )
            messagebox.showinfo("Submitted", f"Sales edit request submitted for approval (ID #{pending_id}).")
            dialog.destroy()
            if callable(on_submitted):
                on_submitted()

        btn_row = tk.Frame(dialog, bg="#f5f6f8")
        btn_row.pack(fill="x", padx=12, pady=(0, 12))
        tk.Button(btn_row, text="Submit for Approval", bg="#4CAF50", fg="white", command=submit_request, width=20).pack(side="left", padx=4)
        tk.Button(btn_row, text="Cancel", command=dialog.destroy, width=10).pack(side="left", padx=4)

    def open_cost_edit_dialog(self, cost_id, on_submitted=None):
        cost = self.get_cost_row_by_id(cost_id)
        if not cost:
            messagebox.showerror("Error", f"Cost record #{cost_id} not found.")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title(f"Edit Cost #{cost_id}")
        dialog.configure(bg="#f5f6f8")
        dialog.transient(self.root)
        dialog.grab_set()

        form_frame = tk.Frame(dialog, bg="#f5f6f8")
        form_frame.pack(fill="both", expand=True, padx=12, pady=12)

        field_specs = [
            ("Cost Date", "cost_date"),
            ("Cost Type", "cost_type"),
            ("Amount", "amount"),
            ("VAT %", "vat_rate"),
            ("Note", "note"),
        ]
        field_vars = {}
        for idx, (label, key) in enumerate(field_specs):
            tk.Label(form_frame, text=f"{label}:", bg="#f5f6f8").grid(row=idx, column=0, sticky="e", padx=6, pady=4)
            value = cost.get(key)
            if key == "vat_rate" and value is None:
                value = 0.0
            var = tk.StringVar(value="" if value is None else str(value))
            width = 48 if key == "note" else 24
            tk.Entry(form_frame, textvariable=var, width=width).grid(row=idx, column=1, sticky="w", padx=6, pady=4)
            field_vars[key] = var

        reason_var = tk.StringVar()
        tk.Label(form_frame, text="Edit Reason:", bg="#f5f6f8").grid(row=len(field_specs), column=0, sticky="e", padx=6, pady=4)
        tk.Entry(form_frame, textvariable=reason_var, width=48).grid(row=len(field_specs), column=1, sticky="w", padx=6, pady=4)

        def submit_request():
            cost_date = self.parse_date_input(field_vars["cost_date"].get())
            if not cost_date:
                messagebox.showerror("Error", "Cost Date is required and must be YYYY-MM-DD.")
                return

            cost_type = field_vars["cost_type"].get().strip()
            if not cost_type:
                messagebox.showerror("Error", "Cost Type is required.")
                return

            amount = self.parse_float_input(field_vars["amount"].get())
            if amount is None:
                messagebox.showerror("Error", "Amount must be a valid number.")
                return

            vat_rate = self.parse_float_input(field_vars["vat_rate"].get())
            if vat_rate is None or vat_rate < 0 or vat_rate > 100:
                messagebox.showerror("Error", "VAT % must be between 0 and 100.")
                return
            vat_amount = round(amount * vat_rate / 100.0, 2)
            total_incl_vat = round(amount + vat_amount, 2)

            reason = reason_var.get().strip()
            if not reason:
                messagebox.showerror("Error", "Edit Reason is required.")
                return

            before = {
                "cost_date": cost.get("cost_date"),
                "cost_type": cost.get("cost_type"),
                "amount": cost.get("amount"),
                "vat_rate": cost.get("vat_rate"),
                "vat_amount": cost.get("vat_amount"),
                "note": cost.get("note"),
                "total_incl_vat": (cost.get("amount") or 0.0) + (cost.get("vat_amount") or 0.0),
            }
            after = {
                "cost_date": cost_date,
                "cost_type": cost_type,
                "amount": amount,
                "vat_rate": vat_rate,
                "vat_amount": vat_amount,
                "note": field_vars["note"].get().strip() or None,
                "total_incl_vat": total_incl_vat,
            }
            changed_fields = [key for key in after.keys() if str(before.get(key)) != str(after.get(key))]
            if not changed_fields:
                messagebox.showinfo("No Changes", "No field was changed.")
                return

            payload = {
                "cost_id": cost_id,
                "before": before,
                "after": after,
                "changed_fields": changed_fields,
                "reason": reason,
                "submitted_by_level": self.current_level,
                "submitted_at": datetime.now().isoformat(timespec="seconds"),
            }
            pending_id = self.submit_pending_entry("CostEdit", payload)
            self.log_action(
                "SUBMIT_COST_EDIT",
                f"CostEdit pending #{pending_id} for cost #{cost_id}; changed={','.join(changed_fields)}",
            )
            messagebox.showinfo("Submitted", f"Cost edit request submitted for approval (ID #{pending_id}).")
            dialog.destroy()
            if callable(on_submitted):
                on_submitted()

        btn_row = tk.Frame(dialog, bg="#f5f6f8")
        btn_row.pack(fill="x", padx=12, pady=(0, 12))
        tk.Button(btn_row, text="Submit for Approval", bg="#4CAF50", fg="white", command=submit_request, width=20).pack(side="left", padx=4)
        tk.Button(btn_row, text="Cancel", command=dialog.destroy, width=10).pack(side="left", padx=4)

    def open_stock_edit_dialog(self, stock_id, on_submitted=None):
        stock = self.get_stock_row_by_id(stock_id)
        if not stock:
            messagebox.showerror("Error", f"Stock record #{stock_id} not found.")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title(f"Edit Stock #{stock_id}")
        dialog.configure(bg="#f5f6f8")
        dialog.transient(self.root)
        dialog.grab_set()

        form_frame = tk.Frame(dialog, bg="#f5f6f8")
        form_frame.pack(fill="both", expand=True, padx=12, pady=12)

        def _stock_section(text, row):
            tk.Frame(form_frame, bg=self.ui_state_colors["neutral_border"], height=1).grid(
                row=row, column=0, columnspan=2, sticky="ew", padx=4, pady=(8, 0))
            tk.Label(form_frame, text=text, bg="#f5f6f8", fg=self.ui_palette["accent"],
                     font=("Segoe UI", 8, "bold")).grid(
                row=row+1, column=0, columnspan=2, sticky="w", padx=4, pady=(2, 4))

        field_vars = {}
        row_idx = 0

        _stock_section("PRODUCT", row_idx);  row_idx += 2
        for label, key in [("Date *", "date"), ("Product SKU *", "product_sku")]:
            tk.Label(form_frame, text=f"{label}:", bg="#f5f6f8").grid(row=row_idx, column=0, sticky="e", padx=6, pady=3)
            var = tk.StringVar(value="" if stock.get(key) is None else str(stock.get(key)))
            tk.Entry(form_frame, textvariable=var, width=24).grid(row=row_idx, column=1, sticky="w", padx=6, pady=3)
            field_vars[key] = var
            row_idx += 1

        _stock_section("QUANTITIES & COSTS", row_idx);  row_idx += 2
        for label, key in [("Unit Cost *", "unit_cost"), ("Current Unit Price *", "current_unit_price"),
                           ("Unit In *", "unit_in")]:
            tk.Label(form_frame, text=f"{label}:", bg="#f5f6f8").grid(row=row_idx, column=0, sticky="e", padx=6, pady=3)
            var = tk.StringVar(value="" if stock.get(key) is None else str(stock.get(key)))
            tk.Entry(form_frame, textvariable=var, width=24).grid(row=row_idx, column=1, sticky="w", padx=6, pady=3)
            field_vars[key] = var
            row_idx += 1

        _stock_section("TAX & NOTE", row_idx);  row_idx += 2
        tk.Label(form_frame, text="Tax % *:", bg="#f5f6f8").grid(row=row_idx, column=0, sticky="e", padx=6, pady=3)
        var = tk.StringVar(value="" if stock.get("tax_rate") is None else str(stock.get("tax_rate")))
        tk.Entry(form_frame, textvariable=var, width=24).grid(row=row_idx, column=1, sticky="w", padx=6, pady=3)
        field_vars["tax_rate"] = var
        row_idx += 1
        tk.Label(form_frame, text="Note:", bg="#f5f6f8").grid(row=row_idx, column=0, sticky="e", padx=6, pady=3)
        var = tk.StringVar(value="" if stock.get("note") is None else str(stock.get("note")))
        tk.Entry(form_frame, textvariable=var, width=48).grid(row=row_idx, column=1, sticky="w", padx=6, pady=3)
        field_vars["note"] = var
        row_idx += 1

        _stock_section("REASON", row_idx);  row_idx += 2
        reason_var = tk.StringVar()
        tk.Label(form_frame, text="Edit Reason *:", bg="#f5f6f8").grid(row=row_idx, column=0, sticky="e", padx=6, pady=3)
        tk.Entry(form_frame, textvariable=reason_var, width=48).grid(row=row_idx, column=1, sticky="w", padx=6, pady=3)

        def submit_request():
            stock_date = self.parse_date_input(field_vars["date"].get())
            if not stock_date:
                messagebox.showerror("Error", "Date is required and must be YYYY-MM-DD.")
                return

            sku = field_vars["product_sku"].get().strip()
            if not sku:
                messagebox.showerror("Error", "Product SKU is required.")
                return
            if not self.product_exists(sku):
                messagebox.showerror("Error", f"Product SKU '{sku}' does not exist.")
                return

            unit_cost = self.parse_float_input(field_vars["unit_cost"].get())
            if unit_cost is None:
                messagebox.showerror("Error", "Unit Cost must be a valid number.")
                return

            current_unit_price = self.parse_float_input(field_vars["current_unit_price"].get())
            if current_unit_price is None or current_unit_price <= 0:
                messagebox.showerror("Error", "Current Unit Price is required and must be greater than 0.")
                return

            unit_in = self.parse_int_input(field_vars["unit_in"].get())
            if unit_in is None or unit_in <= 0:
                messagebox.showerror("Error", "Unit In must be a valid integer greater than 0.")
                return

            tax_rate = self.parse_float_input(field_vars["tax_rate"].get())
            if tax_rate not in {8.0, 10.0}:
                messagebox.showerror("Error", "Tax % must be either 8 or 10.")
                return

            reason = reason_var.get().strip()
            if not reason:
                messagebox.showerror("Error", "Edit Reason is required.")
                return

            pre_tax_total = unit_cost * unit_in
            tax_amount = round(pre_tax_total * tax_rate / 100.0, 2)
            total = round(pre_tax_total, 2)

            before = {
                "date": stock.get("date"),
                "product_sku": stock.get("product_sku"),
                "unit_cost": stock.get("unit_cost"),
                "current_unit_price": stock.get("current_unit_price"),
                "unit_in": stock.get("unit_in"),
                "tax_rate": stock.get("tax_rate"),
                "tax_amount": stock.get("tax_amount"),
                "total": stock.get("total"),
                "note": stock.get("note"),
            }
            after = {
                "date": stock_date,
                "product_sku": sku,
                "unit_cost": unit_cost,
                "current_unit_price": current_unit_price,
                "unit_in": unit_in,
                "tax_rate": tax_rate,
                "tax_amount": tax_amount,
                "total": total,
                "note": field_vars["note"].get().strip() or None,
            }

            changed_fields = [key for key in after.keys() if str(before.get(key)) != str(after.get(key))]
            if not changed_fields:
                messagebox.showinfo("No Changes", "No field was changed.")
                return

            payload = {
                "stock_id": stock_id,
                "before": before,
                "after": after,
                "changed_fields": changed_fields,
                "reason": reason,
                "submitted_by_level": self.current_level,
                "submitted_at": datetime.now().isoformat(timespec="seconds"),
            }
            pending_id = self.submit_pending_entry("StockEdit", payload)
            self.log_action(
                "SUBMIT_STOCK_EDIT",
                f"StockEdit pending #{pending_id} for stock #{stock_id}; changed={','.join(changed_fields)}",
            )
            messagebox.showinfo("Submitted", f"Stock edit request submitted for approval (ID #{pending_id}).")
            dialog.destroy()
            if callable(on_submitted):
                on_submitted()

        btn_row = tk.Frame(dialog, bg="#f5f6f8")
        btn_row.pack(fill="x", padx=12, pady=(0, 12))
        tk.Button(btn_row, text="Submit for Approval", bg="#4CAF50", fg="white", command=submit_request, width=20).pack(side="left", padx=4)
        tk.Button(btn_row, text="Cancel", command=dialog.destroy, width=10).pack(side="left", padx=4)

    def create_stock_summary_tab(self, notebook):
        """Create Stock tab showing current inventory summary instead of transaction history"""
        frame = tk.Frame(notebook, bg=self.ui_palette["bg"])
        notebook.add(frame, text="Stock")

        filter_frame = tk.Frame(frame, bg=self.ui_palette["bg"])
        filter_frame.pack(fill="x", padx=10, pady=(10, 0))
        tk.Label(
            filter_frame,
            text="Search:",
            bg=self.ui_palette["bg"],
            fg=self.ui_palette["text"],
            font=("Segoe UI", 9),
        ).pack(side="left")
        filter_var = tk.StringVar()
        filter_entry = tk.Entry(filter_frame, textvariable=filter_var, width=40)
        filter_entry.pack(side="left", padx=8)

        table_frame = tk.Frame(frame, bg=self.ui_palette["bg"])
        table_frame.pack(expand=True, fill="both", padx=10, pady=10)

        tree = ttk.Treeview(table_frame, columns=("SKU", "Product Name", "On-hand Qty"), show="headings", style="App.Treeview")
        y_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
        x_scroll = ttk.Scrollbar(table_frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        tree.heading("SKU", text="SKU")
        tree.column("SKU", width=150, anchor="w")
        tree.heading("Product Name", text="Product Name")
        tree.column("Product Name", width=250, anchor="w")
        tree.heading("On-hand Qty", text="On-hand Qty")
        tree.column("On-hand Qty", width=120, anchor="e")

        tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")

        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        all_rows = []
        try:
            rows = self.fetch_stock_current_summary()
            for sku, product_name, available_qty in rows:
                all_rows.append([sku, product_name, f"{int(available_qty):,}"])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load Stock data: {e}")

        def render_rows(filtered_rows):
            for item in tree.get_children():
                tree.delete(item)
            for row in filtered_rows:
                tree.insert("", "end", values=row)

        def on_filter(*args):
            term = filter_var.get().strip().lower()
            if not term:
                render_rows(all_rows)
                return
            filtered = []
            for row in all_rows:
                joined = " ".join([str(v).lower() for v in row if v is not None])
                if term in joined:
                    filtered.append(row)
            render_rows(filtered)

        def on_tree_hover(event):
            row_id = tree.identify_row(event.y)
            if not row_id:
                self.schedule_sku_preview_hide()
                return
            column_id = tree.identify_column(event.x)
            try:
                col_index = int(str(column_id).replace("#", ""))
            except Exception:
                self.schedule_sku_preview_hide()
                return
            if col_index != 1:  # SKU column
                self.schedule_sku_preview_hide()
                return
            values = tree.item(row_id).get("values", [])
            if not values:
                self.schedule_sku_preview_hide()
                return
            sku = str(values[0]).strip()
            if not sku:
                self.schedule_sku_preview_hide()
                return
            self.show_sku_preview(sku, event.x_root, event.y_root)

        tree.bind("<Motion>", on_tree_hover)
        tree.bind("<Leave>", lambda event: self.schedule_sku_preview_hide())

        filter_var.trace_add("write", on_filter)
        render_rows(all_rows)

    def create_records_tab(self, notebook):
        frame = tk.Frame(notebook, bg=self.ui_palette["bg"])
        notebook.add(frame, text="Records")

        inner = ttk.Notebook(frame, style="App.TNotebook")
        inner.pack(expand=True, fill="both", padx=10, pady=10)

        self.create_sales_records_tab(inner)

        self.create_stock_summary_tab(inner)

        self.create_data_tab(
            inner,
            "Costs",
            ("ID", "Type", "Date", "Amount", "Note"),
            """
            SELECT id, cost_type, cost_date, amount, note
            FROM Costs ORDER BY cost_date DESC, id DESC
            """,
            formatters={
                "Date": "date",
                "Amount": "money",
            },
        )

        self.create_data_tab(
            inner,
            "Timeline",
            ("ID", "Date", "Event", "Cash In", "Cash Out", "Balance", "Note"),
            """
            SELECT id, event_date, event_name, cash_in, cash_out, balance, note
            FROM Timeline ORDER BY event_date DESC, id DESC
            """,
            formatters={
                "Date": "date",
                "Cash In": "money",
                "Cash Out": "money",
                "Balance": "money",
            },
        )

        self.create_data_tab(
            inner,
            "Product Catalog",
            ("SKU", "Name", "Category", "Unit Cost", "Current Unit Price"),
            """
            SELECT sku, name, category, unit_cost, current_unit_price
            FROM Products ORDER BY sku
            """,
            formatters={
                "Unit Cost": "money",
                "Current Unit Price": "money",
            },
        )

        self.create_data_tab(
            inner,
            "Logs",
            ("ID", "Date", "Type", "SKU", "Details"),
            """
            SELECT id, log_date, log_type, product_sku, details
            FROM Logs ORDER BY log_date DESC, id DESC
            """,
            formatters={
                "Date": "date",
            },
        )

    def create_stock_reports_tab(self, notebook):
        """Create Stock Reports tab showing period-based inventory summary and drill-down"""
        frame = tk.Frame(notebook, bg=self.ui_palette["bg"])
        notebook.add(frame, text="Reports")

        access_text = "Stock Reports"
        tk.Label(frame, text=f"{access_text} - Inventory by Period", bg=self.ui_palette["bg"],
            fg=self.ui_palette["muted"], font=("Segoe UI", 10, "italic")).pack(pady=5, padx=10)

        self.build_stock_reports_workspace(frame, palette=self.ui_palette)

    def parse_currency_text(self, value):
        if value is None:
            return 0.0
        text = str(value).strip()
        if not text:
            return 0.0
        cleaned = "".join(ch for ch in text if ch.isdigit() or ch in "-.")
        if not cleaned or cleaned == "-":
            return 0.0
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    def parse_vat_return_csv(self, file_path):
        results = {
            "sales_value": None,
            "sales_vat": None,
            "purchase_value": None,
            "purchase_vat": None,
        }
        encodings = ["utf-8-sig", "cp1258", "utf-16", "latin-1"]
        lines = None
        for encoding in encodings:
            try:
                with open(file_path, "r", encoding=encoding, errors="ignore") as handle:
                    lines = handle.read().splitlines()
                if lines:
                    break
            except OSError:
                continue

        if not lines:
            return results

        for line in lines:
            if "[34]" in line or "[35]" in line:
                nums = [self.parse_currency_text(part) for part in line.split(",")]
                nums = [n for n in nums if n != 0]
                if "[34]" in line and "[35]" in line and len(nums) >= 2:
                    results["sales_value"] = nums[-2]
                    results["sales_vat"] = nums[-1]
                elif "[34]" in line and nums:
                    results["sales_value"] = nums[-1]
                elif "[35]" in line and nums:
                    results["sales_vat"] = nums[-1]

            if "[23]" in line or "[24]" in line:
                nums = [self.parse_currency_text(part) for part in line.split(",")]
                nums = [n for n in nums if n != 0]
                if "[23]" in line and "[24]" in line and len(nums) >= 2:
                    results["purchase_value"] = nums[-2]
                    results["purchase_vat"] = nums[-1]
                elif "[23]" in line and nums:
                    results["purchase_value"] = nums[-1]
                elif "[24]" in line and nums:
                    results["purchase_vat"] = nums[-1]

        return results

    def parse_cash_flow_q4(self, file_path):
        totals = {"sales": 0.0, "cost": 0.0, "net": 0.0}
        try:
            with open(file_path, "r", encoding="utf-8-sig", errors="ignore") as handle:
                rows = [row.strip().split(",") for row in handle.read().splitlines() if row.strip()]
            if len(rows) < 3:
                return totals
            header_years = rows[0]
            header_months = rows[1]
            indices = [
                idx for idx, (year, month) in enumerate(zip(header_years, header_months))
                if year.strip() == "2025" and month.strip() in {"Oct", "Nov", "Dec"}
            ]
            row_map = {row[0].strip(): row for row in rows[2:] if row and row[0].strip()}
            for key, target in (
                ("Total Sales", "sales"),
                ("Total Cost", "cost"),
                ("Net Cashflow", "net"),
            ):
                row = row_map.get(key, [])
                totals[target] = sum(self.parse_currency_text(row[i]) for i in indices if i < len(row))
        except OSError:
            return totals
        return totals

    def fetch_db_q4_totals(self):
        totals = {"sales": 0.0, "vat": 0.0, "cost": 0.0}
        try:
            conn = sqlite3.connect(FINANCIAL_DB)
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT COALESCE(SUM(gross_sales), 0), COALESCE(SUM(vat_amount), 0)
                FROM Sales
                WHERE strftime('%Y', sale_date) = '2025'
                  AND CAST(strftime('%m', sale_date) AS INTEGER) IN (10, 11, 12)
                """
            )
            row = cursor.fetchone()
            if row:
                totals["sales"], totals["vat"] = row
            cursor.execute(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM Costs
                WHERE strftime('%Y', cost_date) = '2025'
                  AND CAST(strftime('%m', cost_date) AS INTEGER) IN (10, 11, 12)
                """
            )
            row = cursor.fetchone()
            if row:
                totals["cost"] = row[0]
            conn.close()
        except Exception as exc:
            print(f"Q4 totals error: {exc}")
        return totals

    def fetch_financial_statement_summary(self, year=None):
        summary = {
            "revenue": 0.0,
            "gross_sales": 0.0,
            "base_sales": 0.0,
            "service_fee": 0.0,
            "shipping_fee": 0.0,
            "costs": 0.0,
            "inventory": 0.0,
            "cash_balance": 0.0,
            "cash_in": 0.0,
            "cash_out": 0.0,
        }
        try:
            conn = sqlite3.connect(FINANCIAL_DB)
            cursor = conn.cursor()
            year_filter = ""
            params = ()
            if year:
                year_filter = "WHERE strftime('%Y', sale_date) = ?"
                params = (str(year),)
            cursor.execute(
                """
                SELECT
                    COALESCE(SUM(CASE
                        WHEN units_sold IS NOT NULL AND unit_price IS NOT NULL THEN units_sold * unit_price
                        ELSE gross_sales
                    END), 0),
                    COALESCE(SUM(gross_sales), 0),
                    COALESCE(SUM(service_fee), 0),
                    COALESCE(SUM(shipping_fee), 0)
                FROM Sales
                """ + year_filter,
                params,
            )
            row = cursor.fetchone()
            if row:
                summary["base_sales"], summary["gross_sales"], summary["service_fee"], summary["shipping_fee"] = row
                summary["revenue"] = summary["gross_sales"]

            year_filter = ""
            params = ()
            if year:
                year_filter = "WHERE strftime('%Y', cost_date) = ?"
                params = (str(year),)
            cursor.execute("SELECT COALESCE(SUM(amount), 0) FROM Costs " + year_filter, params)
            row = cursor.fetchone()
            if row:
                summary["costs"] = row[0]

            snapshot = self.get_inventory_snapshot(year=year)
            inventory_value = 0.0
            for item in snapshot.values():
                on_hand = item["available"]
                if on_hand <= 0:
                    continue
                unit_cost = item["unit_cost"]
                inventory_value += on_hand * unit_cost
            summary["inventory"] = inventory_value

            year_filter = ""
            params = ()
            if year:
                year_filter = "WHERE strftime('%Y', event_date) = ?"
                params = (str(year),)
            cursor.execute(
                "SELECT balance FROM Timeline " + year_filter + " ORDER BY event_date DESC, id DESC LIMIT 1",
                params,
            )
            row = cursor.fetchone()
            if row and row[0] is not None:
                summary["cash_balance"] = row[0]

            cursor.execute(
                "SELECT COALESCE(SUM(cash_in), 0), COALESCE(SUM(cash_out), 0) FROM Timeline " + year_filter,
                params,
            )
            row = cursor.fetchone()
            if row:
                summary["cash_in"], summary["cash_out"] = row
        except Exception as exc:
            print(f"Financial statement summary error: {exc}")
        finally:
            try:
                conn.close()
            except Exception:
                pass
        return summary

    def create_payables_tab(self, notebook):
        """Accounts Payable management tab inside Financial Data."""
        frame = tk.Frame(notebook, bg=self.ui_palette["bg"])
        notebook.add(frame, text="Payables")

        # ── toolbar ──────────────────────────────────────────────────────────
        top = tk.Frame(frame, bg=self.ui_palette["bg"])
        top.pack(fill="x", padx=10, pady=(10, 4))

        summary_var = tk.StringVar(value="Total Outstanding: 0.00")
        tk.Label(top, textvariable=summary_var, bg=self.ui_palette["bg"],
                 fg=self.ui_palette["text"], font=("Segoe UI", 10, "bold")).pack(side="left")

        def _refresh():
            for item in tree.get_children():
                tree.delete(item)
            rows = self.get_all_accounts_payable_entries()
            today = datetime.now().strftime("%Y-%m-%d")
            total_out = 0.0
            for row in rows:
                eid, vendor, inv_ref, inv_date, due_date, amount, paid_amt, paid_date, note = row
                outstanding = max(0.0, float(amount or 0) - float(paid_amt or 0))
                if paid_date and paid_date <= today and paid_amt >= amount:
                    status = "PAID"
                elif due_date and due_date < today and outstanding > 0:
                    status = "OVERDUE"
                elif outstanding > 0:
                    status = "OPEN"
                else:
                    status = "PAID"
                total_out += outstanding if status != "PAID" else 0.0
                tree.insert("", "end", iid=str(eid), values=(
                    eid,
                    vendor,
                    inv_ref or "",
                    inv_date,
                    due_date or "",
                    f"{float(amount or 0):,.2f}",
                    f"{float(paid_amt or 0):,.2f}",
                    f"{outstanding:,.2f}",
                    paid_date or "",
                    status,
                    note or "",
                ))
            summary_var.set(f"Total Outstanding: {total_out:,.2f} VND")

        def _open_dialog(entry_id=None):
            existing = {}
            if entry_id:
                rows = self.get_all_accounts_payable_entries()
                match = [r for r in rows if r[0] == entry_id]
                if match:
                    r = match[0]
                    existing = dict(zip(
                        ["id","vendor","inv_ref","inv_date","due_date","amount","paid_amt","paid_date","note"], r
                    ))

            dlg = tk.Toplevel(self.root)
            dlg.title("Edit Invoice" if entry_id else "Add Invoice")
            dlg.geometry("460x460")
            dlg.grab_set()
            dlg.configure(bg=self.ui_palette["bg"])
            bg_dlg = self.ui_palette["bg"]

            def _ap_section(text, row):
                tk.Frame(dlg, bg=self.ui_state_colors["neutral_border"], height=1).grid(
                    row=row, column=0, columnspan=2, sticky="ew", padx=12, pady=(8, 0))
                tk.Label(dlg, text=text, bg=bg_dlg, fg=self.ui_palette["accent"],
                         font=("Segoe UI", 8, "bold")).grid(
                    row=row+1, column=0, columnspan=2, sticky="w", padx=12, pady=(2, 4))

            entries = {}
            row_idx = 0
            _ap_section("INVOICE DETAILS", row_idx);  row_idx += 2
            invoice_fields = [
                ("Vendor Name *", "vendor", existing.get("vendor", "")),
                ("Invoice Ref", "inv_ref", existing.get("inv_ref", "")),
                ("Invoice Date * (YYYY-MM-DD)", "inv_date", existing.get("inv_date", "")),
                ("Due Date (YYYY-MM-DD)", "due_date", existing.get("due_date", "")),
                ("Amount *", "amount", existing.get("amount", "")),
            ]
            for label, key, default in invoice_fields:
                tk.Label(dlg, text=label, bg=bg_dlg, fg=self.ui_palette["text"],
                         font=("Segoe UI", 9)).grid(row=row_idx, column=0, sticky="w", padx=16, pady=3)
                var = tk.StringVar(value=str(default))
                tk.Entry(dlg, textvariable=var, width=28).grid(row=row_idx, column=1, padx=8, pady=3)
                entries[key] = var
                row_idx += 1

            _ap_section("PAYMENT STATUS", row_idx);  row_idx += 2
            payment_fields = [
                ("Paid Amount", "paid_amt", existing.get("paid_amt", "")),
                ("Paid Date (YYYY-MM-DD)", "paid_date", existing.get("paid_date", "")),
                ("Note", "note", existing.get("note", "")),
            ]
            for label, key, default in payment_fields:
                tk.Label(dlg, text=label, bg=bg_dlg, fg=self.ui_palette["text"],
                         font=("Segoe UI", 9)).grid(row=row_idx, column=0, sticky="w", padx=16, pady=3)
                var = tk.StringVar(value=str(default))
                tk.Entry(dlg, textvariable=var, width=28).grid(row=row_idx, column=1, padx=8, pady=3)
                entries[key] = var
                row_idx += 1

            # Live outstanding display
            outstanding_var = tk.StringVar(value="Outstanding: —")
            outstanding_lbl = tk.Label(dlg, textvariable=outstanding_var,
                                       bg=bg_dlg, fg=self.ui_palette["accent"],
                                       font=("Segoe UI", 9, "bold"))
            outstanding_lbl.grid(row=row_idx, column=0, columnspan=2, sticky="w", padx=16, pady=4)
            row_idx += 1

            def _update_outstanding(*_):
                try:
                    amt = float(entries["amount"].get().replace(",", ""))
                    paid = float(entries["paid_amt"].get().replace(",", "") or "0")
                    owed = max(0.0, amt - paid)
                    outstanding_var.set(f"Outstanding: {owed:,.2f} VND")
                except Exception:
                    outstanding_var.set("Outstanding: —")
            entries["amount"].trace_add("write", _update_outstanding)
            entries["paid_amt"].trace_add("write", _update_outstanding)
            _update_outstanding()

            err_var = tk.StringVar()
            tk.Label(dlg, textvariable=err_var, bg=bg_dlg, fg="#dc2626",
                     font=("Segoe UI", 8, "italic"), wraplength=360).grid(
                row=row_idx, column=0, columnspan=2, sticky="w", padx=16)
            row_idx += 1

            def _save():
                vendor = entries["vendor"].get().strip()
                inv_date = entries["inv_date"].get().strip()
                amount_str = entries["amount"].get().strip()
                if not vendor:
                    err_var.set("Vendor Name is required.");  return
                if not inv_date:
                    err_var.set("Invoice Date is required (YYYY-MM-DD).");  return
                if not amount_str:
                    err_var.set("Amount is required.");  return
                err_var.set("")
                try:
                    amount = float(amount_str.replace(",", ""))
                except ValueError:
                    err_var.set("Amount must be a number.");  return
                paid_str = entries["paid_amt"].get().strip()
                paid_amount = float(paid_str.replace(",", "")) if paid_str else 0.0
                self.save_accounts_payable_entry(
                    entry_id,
                    vendor,
                    entries["inv_ref"].get().strip(),
                    inv_date,
                    entries["due_date"].get().strip() or None,
                    amount,
                    paid_amount,
                    entries["paid_date"].get().strip() or None,
                    entries["note"].get().strip(),
                )
                dlg.destroy()
                _refresh()

            btn_frame_dlg = tk.Frame(dlg, bg=bg_dlg)
            btn_frame_dlg.grid(row=row_idx, column=0, columnspan=2, pady=12)
            tk.Button(btn_frame_dlg, text="Save", command=_save, bg=self.ui_palette["accent"],
                      fg="white", relief="flat", width=12).pack(side="left", padx=8)
            tk.Button(btn_frame_dlg, text="Cancel", command=dlg.destroy, bg="#78909c",
                      fg="white", relief="flat", width=12).pack(side="left", padx=8)

        def _edit_selected():
            sel = tree.selection()
            if not sel:
                messagebox.showinfo("Edit", "Select a row to edit.")
                return
            _open_dialog(entry_id=int(sel[0]))

        def _delete_selected():
            sel = tree.selection()
            if not sel:
                return
            if messagebox.askyesno("Delete", "Delete the selected invoice entry?"):
                self.delete_accounts_payable_entry(int(sel[0]))
                _refresh()

        btn_frame = tk.Frame(top, bg=self.ui_palette["bg"])
        btn_frame.pack(side="right")
        for label, cmd, color in [
            ("Add Invoice", lambda: _open_dialog(), self.ui_palette["accent"]),
            ("Edit", _edit_selected, "#607d8b"),
            ("Delete", _delete_selected, self.ui_palette["danger"]),
            ("Refresh", _refresh, "#455a64"),
        ]:
            tk.Button(btn_frame, text=label, command=cmd, bg=color, fg="white",
                      relief="flat", padx=10).pack(side="left", padx=4)

        # ── treeview ─────────────────────────────────────────────────────────
        cols = ("ID", "Vendor", "Inv Ref", "Invoice Date", "Due Date",
                "Amount", "Paid", "Outstanding", "Paid Date", "Status", "Note")
        tree_frame = tk.Frame(frame, bg=self.ui_palette["bg"])
        tree_frame.pack(expand=True, fill="both", padx=10, pady=(4, 10))
        tree = ttk.Treeview(tree_frame, columns=cols, show="headings", style="App.Treeview")
        widths = [40, 160, 100, 100, 100, 110, 110, 110, 100, 80, 180]
        for col, w in zip(cols, widths):
            tree.heading(col, text=col)
            tree.column(col, width=w, anchor="e" if col in ("Amount", "Paid", "Outstanding") else "w")
        ys = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        xs = ttk.Scrollbar(tree_frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
        tree.grid(row=0, column=0, sticky="nsew")
        ys.grid(row=0, column=1, sticky="ns")
        xs.grid(row=1, column=0, sticky="ew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        tree.bind("<Double-1>", lambda e: _edit_selected())
        _refresh()

    def create_summary_tab(self, notebook):
        frame = tk.Frame(notebook, bg="white")
        notebook.add(frame, text="Summary")

        control_frame = tk.Frame(frame, bg="white")
        control_frame.pack(fill="x", padx=10, pady=10)

        tk.Label(control_frame, text="View:", bg="white").pack(side="left")
        view_var = tk.StringVar(value="Quarterly")
        view_combo = ttk.Combobox(
            control_frame,
            textvariable=view_var,
            values=["Quarterly", "Yearly"],
            state="readonly",
            width=12,
        )
        view_combo.pack(side="left", padx=8)

        table_frame = tk.Frame(frame, bg="white")
        table_frame.pack(expand=True, fill="both", padx=10, pady=10)

        tree = ttk.Treeview(table_frame, columns=("Period", "Sales", "Costs", "Net Cash"), show="headings")
        for col in ("Period", "Sales", "Costs", "Net Cash"):
            tree.heading(col, text=col)
            tree.column(col, width=150, anchor="w")

        tree.grid(row=0, column=0, sticky="nsew")
        y_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
        y_scroll.grid(row=0, column=1, sticky="ns")
        tree.configure(yscrollcommand=y_scroll.set)
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        def load_summary():
            for item in tree.get_children():
                tree.delete(item)
            try:
                for period, sales_val, cost_val, net_cash in self.fetch_financial_summary_rows(view_var.get()):
                    tree.insert(
                        "", "end",
                        values=(
                            period,
                            self.format_cell(sales_val, "money"),
                            self.format_cell(cost_val, "money"),
                            self.format_cell(net_cash, "money"),
                        ),
                    )
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load summary: {e}")

        view_combo.bind("<<ComboboxSelected>>", lambda event: load_summary())
        load_summary()

    def fetch_financial_summary_rows(self, view):
        conn = sqlite3.connect(FINANCIAL_DB)
        try:
            cursor = conn.cursor()
            if view == "Yearly":
                cursor.execute(
                    """
                    SELECT strftime('%Y', sale_date) AS period, SUM(gross_sales)
                    FROM Sales GROUP BY period ORDER BY period DESC
                    """
                )
                sales = {row[0]: row[1] for row in cursor.fetchall() if row[0]}
                cursor.execute(
                    """
                    SELECT strftime('%Y', cost_date) AS period, SUM(amount)
                    FROM Costs
                    WHERE cost_date IS NOT NULL AND TRIM(cost_date) <> ''
                    GROUP BY period ORDER BY period DESC
                    """
                )
                costs = {row[0]: row[1] for row in cursor.fetchall() if row[0]}
                cursor.execute(
                    """
                    SELECT strftime('%Y', event_date) AS period, SUM(cash_in), SUM(cash_out)
                    FROM Timeline GROUP BY period ORDER BY period DESC
                    """
                )
                cash = {row[0]: (row[1] or 0, row[2] or 0) for row in cursor.fetchall() if row[0]}
            else:
                cursor.execute(
                    """
                    SELECT strftime('%Y', sale_date) AS y,
                           ((CAST(strftime('%m', sale_date) AS INTEGER) + 2) / 3) AS q,
                           SUM(gross_sales)
                    FROM Sales GROUP BY y, q ORDER BY y DESC, q DESC
                    """
                )
                sales = {f"{row[0]} Q{int(row[1])}": row[2] for row in cursor.fetchall() if row[0]}
                cursor.execute(
                    """
                    SELECT strftime('%Y', cost_date) AS y,
                           ((CAST(strftime('%m', cost_date) AS INTEGER) + 2) / 3) AS q,
                           SUM(amount)
                    FROM Costs
                    WHERE cost_date IS NOT NULL AND TRIM(cost_date) <> ''
                    GROUP BY y, q ORDER BY y DESC, q DESC
                    """
                )
                costs = {f"{row[0]} Q{int(row[1])}": row[2] for row in cursor.fetchall() if row[0]}
                cursor.execute(
                    """
                    SELECT strftime('%Y', event_date) AS y,
                           ((CAST(strftime('%m', event_date) AS INTEGER) + 2) / 3) AS q,
                           SUM(cash_in), SUM(cash_out)
                    FROM Timeline GROUP BY y, q ORDER BY y DESC, q DESC
                    """
                )
                cash = {f"{row[0]} Q{int(row[1])}": (row[2] or 0, row[3] or 0) for row in cursor.fetchall() if row[0]}

            rows = []
            periods = sorted(set(list(sales.keys()) + list(costs.keys()) + list(cash.keys())), reverse=True)
            for period in periods:
                sales_val = sales.get(period, 0) or 0
                cost_val = costs.get(period, 0) or 0
                cash_in, cash_out = cash.get(period, (0, 0))
                rows.append((period, sales_val, cost_val, (cash_in or 0) - (cash_out or 0)))
            return rows
        finally:
            conn.close()

    def get_period_date_range(self, view, period_label):
        period_label = str(period_label or "").strip()
        if not period_label:
            return None, None
        if view == "Yearly":
            return f"{period_label}-01-01", f"{period_label}-12-31"
        match = re.match(r"^(\d{4})\s+Q([1-4])$", period_label)
        if not match:
            return None, None
        year = int(match.group(1))
        quarter = int(match.group(2))
        start_month = (quarter - 1) * 3 + 1
        end_month = start_month + 2
        end_day = 31 if end_month in {3, 12} else 30
        return f"{year:04d}-{start_month:02d}-01", f"{year:04d}-{end_month:02d}-{end_day:02d}"

    def fetch_stock_current_summary(self):
        """Fetch current inventory summary: (sku, product_name, available_qty)"""
        conn = sqlite3.connect(FINANCIAL_DB)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                WITH stock_totals AS (
                    SELECT product_sku, COALESCE(SUM(unit_in), 0) AS stock_in
                    FROM Stock
                    GROUP BY product_sku
                ),
                sales_totals AS (
                    SELECT product_sku, COALESCE(SUM(units_sold), 0) AS sold
                    FROM Sales
                    GROUP BY product_sku
                )
                SELECT p.sku, p.name,
                       COALESCE(st.stock_in, 0) - COALESCE(sa.sold, 0) AS available_qty
                FROM Products p
                LEFT JOIN stock_totals st ON p.sku = st.product_sku
                LEFT JOIN sales_totals sa ON p.sku = sa.product_sku
                ORDER BY p.sku
                """
            )
            return cursor.fetchall()
        finally:
            conn.close()

    def fetch_stock_summary_by_period(self, view):
        """Fetch stock summary grouped by period: (period, total_unit_in, total_sold, available_qty, grand_cost)"""
        conn = sqlite3.connect(FINANCIAL_DB)
        try:
            cursor = conn.cursor()
            if view == "Yearly":
                cursor.execute(
                    """
                    WITH stock_by_period AS (
                        SELECT strftime('%Y', date) AS period,
                               COALESCE(SUM(unit_in), 0) AS stock_in,
                               COALESCE(SUM(total), 0) AS grand_cost
                        FROM Stock
                        GROUP BY period
                    ),
                    sales_by_period AS (
                        SELECT strftime('%Y', sale_date) AS period,
                               COALESCE(SUM(units_sold), 0) AS stock_sold
                        FROM Sales
                        GROUP BY period
                    ),
                    periods AS (
                        SELECT period FROM stock_by_period
                        UNION
                        SELECT period FROM sales_by_period
                    )
                    SELECT p.period,
                           COALESCE(sb.stock_in, 0) AS stock_in,
                           COALESCE(sa.stock_sold, 0) AS stock_sold,
                           COALESCE(sb.stock_in, 0) - COALESCE(sa.stock_sold, 0) AS available,
                           COALESCE(sb.grand_cost, 0) AS grand_cost
                    FROM periods p
                    LEFT JOIN stock_by_period sb ON p.period = sb.period
                    LEFT JOIN sales_by_period sa ON p.period = sa.period
                    WHERE p.period IS NOT NULL
                    ORDER BY p.period DESC
                    """
                )
            else:  # Quarterly
                cursor.execute(
                    """
                    WITH stock_by_period AS (
                        SELECT strftime('%Y', date) AS y,
                               ((CAST(strftime('%m', date) AS INTEGER) + 2) / 3) AS q,
                               COALESCE(SUM(unit_in), 0) AS stock_in,
                               COALESCE(SUM(total), 0) AS grand_cost
                        FROM Stock
                        GROUP BY y, q
                    ),
                    sales_by_period AS (
                        SELECT strftime('%Y', sale_date) AS y,
                               ((CAST(strftime('%m', sale_date) AS INTEGER) + 2) / 3) AS q,
                               COALESCE(SUM(units_sold), 0) AS stock_sold
                        FROM Sales
                        GROUP BY y, q
                    ),
                    periods AS (
                        SELECT y, q FROM stock_by_period
                        UNION
                        SELECT y, q FROM sales_by_period
                    )
                    SELECT p.y,
                           p.q,
                           COALESCE(sb.stock_in, 0) AS stock_in,
                           COALESCE(sa.stock_sold, 0) AS stock_sold,
                           COALESCE(sb.stock_in, 0) - COALESCE(sa.stock_sold, 0) AS available,
                           COALESCE(sb.grand_cost, 0) AS grand_cost
                    FROM periods p
                    LEFT JOIN stock_by_period sb ON p.y = sb.y AND p.q = sb.q
                    LEFT JOIN sales_by_period sa ON p.y = sa.y AND p.q = sa.q
                    WHERE p.y IS NOT NULL
                    ORDER BY p.y DESC, p.q DESC
                    """
                )
                rows = cursor.fetchall()
                return [(f"{int(row[0])} Q{int(row[1])}", row[2], row[3], row[4], row[5]) for row in rows]
            
            return cursor.fetchall()
        finally:
            conn.close()

    def fetch_stock_records_by_period(self, start_date, end_date):
        """Fetch stock records for a date range: (id, date, sku, unit_cost, current_unit_price, unit_in, tax_rate, tax_amount, total, note)"""
        conn = sqlite3.connect(FINANCIAL_DB)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, date, product_sku, unit_cost, current_unit_price, unit_in, tax_rate, tax_amount, total, note
                FROM Stock
                WHERE date BETWEEN ? AND ?
                ORDER BY date ASC, id ASC
                """,
                (start_date, end_date)
            )
            return cursor.fetchall()
        finally:
            conn.close()

    def fetch_cost_summary_by_period(self, view):
        """Fetch cost summary grouped by period: (period, cost_count, amount_total, vat_total, total_incl_vat)"""
        conn = sqlite3.connect(FINANCIAL_DB)
        try:
            cursor = conn.cursor()
            if view == "Yearly":
                cursor.execute(
                    """
                    SELECT strftime('%Y', cost_date) AS period,
                           COUNT(*) AS cost_count,
                           COALESCE(SUM(amount), 0) AS amount_total,
                           COALESCE(SUM(COALESCE(vat_amount, 0)), 0) AS vat_total,
                           COALESCE(SUM(amount + COALESCE(vat_amount, 0)), 0) AS total_incl_vat
                    FROM Costs
                    WHERE cost_date IS NOT NULL AND TRIM(cost_date) <> ''
                    GROUP BY period
                    ORDER BY period DESC
                    """
                )
                return cursor.fetchall()

            cursor.execute(
                """
                SELECT strftime('%Y', cost_date) AS y,
                       ((CAST(strftime('%m', cost_date) AS INTEGER) + 2) / 3) AS q,
                       COUNT(*) AS cost_count,
                       COALESCE(SUM(amount), 0) AS amount_total,
                       COALESCE(SUM(COALESCE(vat_amount, 0)), 0) AS vat_total,
                       COALESCE(SUM(amount + COALESCE(vat_amount, 0)), 0) AS total_incl_vat
                FROM Costs
                WHERE cost_date IS NOT NULL AND TRIM(cost_date) <> ''
                GROUP BY y, q
                ORDER BY y DESC, q DESC
                """
            )
            rows = cursor.fetchall()
            return [(f"{int(row[0])} Q{int(row[1])}", row[2], row[3], row[4], row[5]) for row in rows]
        finally:
            conn.close()

    def fetch_cost_records_by_period(self, start_date, end_date):
        """Fetch cost records for a date range: (id, cost_date, cost_type, amount, vat_rate, vat_amount, note)"""
        conn = sqlite3.connect(FINANCIAL_DB)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, cost_date, cost_type, amount, vat_rate, vat_amount, note
                FROM Costs
                WHERE cost_date BETWEEN ? AND ?
                ORDER BY cost_date ASC, id ASC
                """,
                (start_date, end_date),
            )
            return cursor.fetchall()
        finally:
            conn.close()

    def build_sales_reports_workspace(self, frame, palette=None):
        palette = palette or self.ui_palette
        selected_period = {"value": None}

        control_frame = tk.Frame(frame, bg=palette["surface"])
        control_frame.pack(fill="x", padx=10, pady=(10, 6))
        tk.Label(control_frame, text="View:", bg=palette["surface"], fg=palette["text"], font=("Segoe UI", 9)).pack(side="left")
        view_var = tk.StringVar(value="Quarterly")
        view_combo = ttk.Combobox(control_frame, textvariable=view_var, values=["Quarterly", "Yearly"], state="readonly", width=12)
        view_combo.pack(side="left", padx=8)
        selected_var = tk.StringVar(value="Selected Period: (none)")
        tk.Label(control_frame, textvariable=selected_var, bg=palette["surface"], fg=palette["muted"], font=("Segoe UI", 9, "italic")).pack(side="left", padx=12)

        summary_frame = tk.Frame(frame, bg=palette["surface"])
        summary_frame.pack(fill="x", padx=10, pady=(0, 8))
        summary_tree = ttk.Treeview(summary_frame, columns=("Period", "Sales", "Costs", "Net Cash"), show="headings", style="App.Treeview", height=7)
        for col in ("Period", "Sales", "Costs", "Net Cash"):
            summary_tree.heading(col, text=col)
            summary_tree.column(col, width=150, anchor="w")
        summary_tree.grid(row=0, column=0, sticky="nsew")
        summary_scroll = ttk.Scrollbar(summary_frame, orient="vertical", command=summary_tree.yview)
        summary_scroll.grid(row=0, column=1, sticky="ns")
        summary_tree.configure(yscrollcommand=summary_scroll.set)
        summary_frame.grid_rowconfigure(0, weight=1)
        summary_frame.grid_columnconfigure(0, weight=1)

        detail_label = tk.Label(frame, text="Sales Detail", bg=palette["surface"], fg=palette["text"], font=("Segoe UI", 10, "bold"))
        detail_label.pack(anchor="w", padx=10, pady=(2, 0))

        def period_filter_provider():
            start_date, end_date = self.get_period_date_range(view_var.get(), selected_period["value"])
            if not start_date or not end_date:
                return None
            return {"start_date": start_date, "end_date": end_date}

        detail_frame = tk.Frame(frame, bg=palette["surface"])
        detail_frame.pack(fill="both", expand=True, padx=10, pady=(4, 10))
        detail_panel = self.build_sales_records_panel(detail_frame, enable_edit=True, palette=palette, period_filter_provider=period_filter_provider)

        def set_period(period):
            selected_period["value"] = period
            selected_var.set(f"Selected Period: {period}" if period else "Selected Period: (none)")
            detail_label.configure(text=f"Sales Detail - {period}" if period else "Sales Detail")
            detail_panel["refresh"]()

        def load_summary():
            rows = self.fetch_financial_summary_rows(view_var.get())
            for item in summary_tree.get_children():
                summary_tree.delete(item)
            for period, sales_val, cost_val, net_cash in rows:
                summary_tree.insert("", "end", values=(period, self.format_cell(sales_val, "money"), self.format_cell(cost_val, "money"), self.format_cell(net_cash, "money")))
            if rows:
                first_item = summary_tree.get_children()[0]
                summary_tree.selection_set(first_item)
                set_period(rows[0][0])
            else:
                set_period(None)

        def on_summary_select(event=None):
            selection = summary_tree.selection()
            if not selection:
                return
            values = summary_tree.item(selection[0]).get("values", [])
            set_period(values[0] if values else None)

        tk.Button(control_frame, text="Refresh", command=load_summary, bg=palette["accent"], fg="white", width=10).pack(side="right")
        view_combo.bind("<<ComboboxSelected>>", lambda event: load_summary())
        summary_tree.bind("<<TreeviewSelect>>", on_summary_select)
        load_summary()

    def build_stock_reports_workspace(self, frame, palette=None, enable_edit=False):
        """Build Stock Reports interface with period-based summary and transaction drill-down"""
        palette = palette or self.ui_palette
        selected_period = {"value": None}
        hovered_stock_id = {"value": None}
        edit_btn_hide_job = {"id": None}

        control_frame = tk.Frame(frame, bg=palette["surface"])
        control_frame.pack(fill="x", padx=10, pady=(10, 6))
        tk.Label(control_frame, text="View:", bg=palette["surface"], fg=palette["text"], font=("Segoe UI", 9)).pack(side="left")
        view_var = tk.StringVar(value="Quarterly")
        view_combo = ttk.Combobox(control_frame, textvariable=view_var, values=["Quarterly", "Yearly"], state="readonly", width=12)
        view_combo.pack(side="left", padx=8)
        selected_var = tk.StringVar(value="Selected Period: (none)")
        tk.Label(control_frame, textvariable=selected_var, bg=palette["surface"], fg=palette["muted"], font=("Segoe UI", 9, "italic")).pack(side="left", padx=12)

        summary_frame = tk.Frame(frame, bg=palette["surface"])
        summary_frame.pack(fill="x", padx=10, pady=(0, 8))
        summary_tree = ttk.Treeview(
            summary_frame,
            columns=("Period", "Units In (Period)", "Units Sold (Period)", "Net Change (Period)", "Total Cost"),
            show="headings",
            style="App.Treeview",
            height=7,
        )
        for col in ("Period", "Units In (Period)", "Units Sold (Period)", "Net Change (Period)", "Total Cost"):
            summary_tree.heading(col, text=col)
            summary_tree.column(col, width=140, anchor="w")
        summary_tree.grid(row=0, column=0, sticky="nsew")
        summary_scroll = ttk.Scrollbar(summary_frame, orient="vertical", command=summary_tree.yview)
        summary_scroll.grid(row=0, column=1, sticky="ns")
        summary_tree.configure(yscrollcommand=summary_scroll.set)
        summary_frame.grid_rowconfigure(0, weight=1)
        summary_frame.grid_columnconfigure(0, weight=1)

        tk.Label(
            frame,
            text="Net Change (Period) = Units In (Period) - Units Sold (Period). This is period movement, not current on-hand balance.",
            bg=palette["surface"],
            fg=palette["muted"],
            font=("Segoe UI", 9, "italic"),
        ).pack(anchor="w", padx=10, pady=(0, 2))

        detail_label = tk.Label(frame, text="Stock Records", bg=palette["surface"], fg=palette["text"], font=("Segoe UI", 10, "bold"))
        detail_label.pack(anchor="w", padx=10, pady=(2, 0))

        edit_btn = None

        detail_frame = tk.Frame(frame, bg=palette["surface"])
        detail_frame.pack(fill="both", expand=True, padx=10, pady=(4, 10))

        if enable_edit and self.can_request_stock_log_edit():
            edit_btn = tk.Button(
                detail_frame,
                text="Edit",
                bg="#4CAF50",
                fg="white",
                width=12,
            )
            edit_btn.place_forget()

        def cancel_edit_btn_hide():
            if edit_btn_hide_job["id"] is not None:
                try:
                    self.root.after_cancel(edit_btn_hide_job["id"])
                except Exception:
                    pass
                edit_btn_hide_job["id"] = None

        def hide_edit_btn_now():
            cancel_edit_btn_hide()
            hovered_stock_id["value"] = None
            if edit_btn is not None:
                edit_btn.place_forget()

        def schedule_edit_btn_hide(delay_ms=120):
            if edit_btn is None:
                return
            cancel_edit_btn_hide()
            edit_btn_hide_job["id"] = self.root.after(delay_ms, hide_edit_btn_now)

        def show_edit_btn_for_row(row_id, fallback_y=None):
            if edit_btn is None:
                return False
            stock_id = self.parse_int_input(row_id)
            if not stock_id:
                return False
            hovered_stock_id["value"] = stock_id
            edit_btn.configure(
                text=f"Edit #{stock_id}",
                command=lambda sid=stock_id: submit_stock_edit_request(sid),
            )
            bbox = detail_tree.bbox(row_id, "#1")
            if bbox:
                _, y, _, h = bbox
                y_pos = max(0, y + (h - 24) // 2)
            else:
                y_pos = max(0, (fallback_y or 0) - 12)
            edit_btn.place(x=4, y=y_pos)
            return True

        detail_tree = ttk.Treeview(
            detail_frame,
            columns=("ID", "Date", "SKU", "Unit Cost", "Current Unit Price", "Unit In", "Tax %", "Tax Amount", "Total", "Note"),
            show="headings",
            style="App.Treeview"
        )
        for col in ("ID", "Date", "SKU", "Unit Cost", "Current Unit Price", "Unit In", "Tax %", "Tax Amount", "Total", "Note"):
            detail_tree.heading(col, text=col)
            detail_tree.column(col, width=100, anchor="w")
        detail_tree.column("ID", width=1, stretch=False)
        detail_tree.column("Total", width=120, anchor="e")
        detail_tree.column("Tax Amount", width=120, anchor="e")
        detail_tree.column("Unit Cost", width=120, anchor="e")
        detail_tree.column("Current Unit Price", width=140, anchor="e")

        detail_scroll = ttk.Scrollbar(detail_frame, orient="vertical", command=detail_tree.yview)
        detail_tree.configure(yscrollcommand=detail_scroll.set)
        detail_tree.grid(row=0, column=0, sticky="nsew")
        detail_scroll.grid(row=0, column=1, sticky="ns")
        detail_frame.grid_rowconfigure(0, weight=1)
        detail_frame.grid_columnconfigure(0, weight=1)

        def load_detail_records():
            start_date, end_date = self.get_period_date_range(view_var.get(), selected_period["value"])
            for item in detail_tree.get_children():
                detail_tree.delete(item)
            hide_edit_btn_now()
            if not start_date or not end_date:
                return
            try:
                rows = self.fetch_stock_records_by_period(start_date, end_date)
                for row_id, row_date, sku, unit_cost, current_unit_price, unit_in, tax_rate, tax_amount, total, note in rows:
                    detail_tree.insert("", "end", iid=str(row_id), values=(
                        row_id,
                        row_date,
                        sku,
                        self.format_cell(unit_cost, "money"),
                        self.format_cell(current_unit_price, "money"),
                        f"{int(unit_in):,}",
                        f"{tax_rate}%",
                        self.format_cell(tax_amount, "money"),
                        self.format_cell(total, "money"),
                        note or ""
                    ))
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load stock records: {e}")

        def submit_stock_edit_request(stock_id):
            if not self.can_request_stock_log_edit():
                messagebox.showerror("Access Denied", "Only Level 2, 3, or 4 can submit Stock edit requests.")
                return
            self.open_stock_edit_dialog(stock_id, on_submitted=load_detail_records)

        context_target = {"stock_id": None, "sku": ""}

        def set_context_target(row_id):
            if not row_id:
                context_target["stock_id"] = None
                context_target["sku"] = ""
                return
            values = detail_tree.item(row_id).get("values", [])
            if not values or len(values) < 3:
                context_target["stock_id"] = None
                context_target["sku"] = ""
                return
            stock_id = self.parse_int_input(values[0] if values else row_id)
            if not stock_id:
                context_target["stock_id"] = None
                context_target["sku"] = ""
                return
            sku = str(values[2]).strip() if len(values) > 2 else ""
            context_target["stock_id"] = stock_id
            context_target["sku"] = sku

        def edit_stock_from_context():
            stock_id = context_target.get("stock_id")
            if stock_id:
                submit_stock_edit_request(stock_id)

        def view_sku_image_from_context():
            sku = context_target.get("sku") or ""
            if not sku:
                return
            self.show_sku_preview(sku, self.root.winfo_pointerx(), self.root.winfo_pointery())

        def copy_sku_from_context():
            sku = context_target.get("sku") or ""
            if not sku:
                return
            try:
                self.root.clipboard_clear()
                self.root.clipboard_append(sku)
            except tk.TclError:
                return

        def copy_stock_id_from_context():
            stock_id = context_target.get("stock_id")
            if stock_id is None:
                return
            try:
                self.root.clipboard_clear()
                self.root.clipboard_append(str(stock_id))
            except tk.TclError:
                return

        context_menu = tk.Menu(detail_tree, tearoff=0)
        context_menu.add_command(label="Edit Stock (Submit for Approval)", command=edit_stock_from_context)
        context_menu.add_separator()
        context_menu.add_command(label="View SKU Image", command=view_sku_image_from_context)
        context_menu.add_command(label="Copy SKU", command=copy_sku_from_context)
        context_menu.add_command(label="Copy Stock ID", command=copy_stock_id_from_context)

        def on_detail_right_click(event):
            row_id = detail_tree.identify_row(event.y)
            if not row_id:
                return

            hide_edit_btn_now()
            detail_tree.selection_set(row_id)
            detail_tree.focus(row_id)
            set_context_target(row_id)

            can_edit = enable_edit and self.can_request_stock_log_edit() and bool(context_target.get("stock_id"))
            context_menu.entryconfigure(0, state=("normal" if can_edit else "disabled"))

            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                context_menu.grab_release()

        def on_detail_select(event=None):
            selection = detail_tree.selection()
            if selection:
                set_context_target(selection[0])

        def on_detail_hover(event):
            row_id = detail_tree.identify_row(event.y)
            column_id = detail_tree.identify_column(event.x)

            try:
                col_index = int(str(column_id).replace("#", ""))
            except Exception:
                col_index = None

            if row_id and col_index == 3:
                values = detail_tree.item(row_id).get("values", [])
                if len(values) >= 3:
                    sku = str(values[2]).strip()
                    if sku:
                        self.show_sku_preview(sku, event.x_root, event.y_root)
                    else:
                        self.schedule_sku_preview_hide()
                else:
                    self.schedule_sku_preview_hide()
            else:
                self.schedule_sku_preview_hide()

            if not enable_edit or edit_btn is None:
                return

            if row_id and show_edit_btn_for_row(row_id, fallback_y=event.y):
                cancel_edit_btn_hide()
                return

            schedule_edit_btn_hide()

        def on_detail_leave(event=None):
            self.schedule_sku_preview_hide()
            schedule_edit_btn_hide()

        def on_wheel_scroll(event=None):
            schedule_edit_btn_hide(0)

        if edit_btn is not None:
            edit_btn.bind("<Enter>", lambda event: cancel_edit_btn_hide())
            edit_btn.bind("<Leave>", lambda event: schedule_edit_btn_hide())

        def set_period(period):
            selected_period["value"] = period
            selected_var.set(f"Selected Period: {period}" if period else "Selected Period: (none)")
            detail_label.configure(text=f"Stock Records - {period}" if period else "Stock Records")
            load_detail_records()

        def load_summary():
            try:
                rows = self.fetch_stock_summary_by_period(view_var.get())
                for item in summary_tree.get_children():
                    summary_tree.delete(item)
                for period, stock_in, sold, available, grand_cost in rows:
                    summary_tree.insert("", "end", values=(
                        period,
                        f"{int(stock_in):,}",
                        f"{int(sold):,}",
                        f"{int(available):,}",
                        self.format_cell(grand_cost, "money")
                    ))
                if rows:
                    first_item = summary_tree.get_children()[0]
                    summary_tree.selection_set(first_item)
                    set_period(rows[0][0])
                else:
                    set_period(None)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load stock summary: {e}")

        def on_summary_select(event=None):
            selection = summary_tree.selection()
            if not selection:
                return
            values = summary_tree.item(selection[0]).get("values", [])
            set_period(values[0] if values else None)

        def show_integrity_report():
            try:
                report = self.run_inventory_integrity_scan()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to run inventory integrity check: {e}")
                return

            def append_items(lines, title, items, formatter, limit=20):
                lines.append(f"{title}: {len(items)}")
                for item in items[:limit]:
                    lines.append(f"  - {formatter(item)}")
                if len(items) > limit:
                    lines.append(f"  - ... and {len(items) - limit} more")
                lines.append("")

            lines = ["Inventory Integrity Report", "=" * 28]
            lines.append(f"Products in catalog: {len(report['product_skus'])}")
            lines.append(f"SKUs in Sales: {len(report['sales_skus'])}")
            lines.append(f"SKUs in Stock: {len(report['stock_skus'])}")
            lines.append("")

            append_items(lines, "Unknown SKUs in Sales", report["unknown_in_sales"], lambda item: item)
            append_items(lines, "Unknown SKUs in Stock", report["unknown_in_stock"], lambda item: item)
            append_items(lines, "Low stock (<=2 and >0)", report["low_stock"], lambda item: f"{item[0]}: {item[1]}")
            append_items(lines, "Critical stock (<=0)", report["critical_stock"], lambda item: f"{item[0]}: {item[1]}")

            messagebox.showinfo("Inventory Integrity", "\n".join(lines))

        tk.Button(control_frame, text="Integrity Check", command=show_integrity_report, bg="#607D8B", fg="white", width=14).pack(side="right", padx=(0, 8))
        tk.Button(control_frame, text="Refresh", command=load_summary, bg=palette["accent"], fg="white", width=10).pack(side="right")
        view_combo.bind("<<ComboboxSelected>>", lambda event: load_summary())
        summary_tree.bind("<<TreeviewSelect>>", on_summary_select)
        detail_tree.bind("<<TreeviewSelect>>", on_detail_select)
        detail_tree.bind("<Motion>", on_detail_hover)
        detail_tree.bind("<Leave>", on_detail_leave)
        detail_tree.bind("<Button-3>", on_detail_right_click)
        detail_tree.bind("<Button-2>", on_detail_right_click)
        detail_tree.bind("<Control-Button-1>", on_detail_right_click)
        detail_tree.bind("<MouseWheel>", on_wheel_scroll)
        detail_tree.bind("<Button-4>", on_wheel_scroll)
        detail_tree.bind("<Button-5>", on_wheel_scroll)
        load_summary()

    def build_cost_reports_workspace(self, frame, palette=None, enable_edit=False):
        palette = palette or self.ui_palette
        selected_period = {"value": None}

        control_frame = tk.Frame(frame, bg=palette["surface"])
        control_frame.pack(fill="x", padx=10, pady=(10, 6))
        tk.Label(control_frame, text="View:", bg=palette["surface"], fg=palette["text"], font=("Segoe UI", 9)).pack(side="left")
        view_var = tk.StringVar(value="Quarterly")
        view_combo = ttk.Combobox(control_frame, textvariable=view_var, values=["Quarterly", "Yearly"], state="readonly", width=12)
        view_combo.pack(side="left", padx=8)
        selected_var = tk.StringVar(value="Selected Period: (none)")
        tk.Label(control_frame, textvariable=selected_var, bg=palette["surface"], fg=palette["muted"], font=("Segoe UI", 9, "italic")).pack(side="left", padx=12)

        summary_frame = tk.Frame(frame, bg=palette["surface"])
        summary_frame.pack(fill="x", padx=10, pady=(0, 8))
        summary_tree = ttk.Treeview(
            summary_frame,
            columns=("Period", "Entries", "Amount", "VAT Amount", "Total Incl. VAT"),
            show="headings",
            style="App.Treeview",
            height=7,
        )
        for col in ("Period", "Entries", "Amount", "VAT Amount", "Total Incl. VAT"):
            summary_tree.heading(col, text=col)
            summary_tree.column(col, width=145, anchor="w")
        summary_tree.column("Entries", anchor="e")
        summary_tree.column("Amount", anchor="e")
        summary_tree.column("VAT Amount", anchor="e")
        summary_tree.column("Total Incl. VAT", anchor="e")
        summary_tree.grid(row=0, column=0, sticky="nsew")
        summary_scroll = ttk.Scrollbar(summary_frame, orient="vertical", command=summary_tree.yview)
        summary_scroll.grid(row=0, column=1, sticky="ns")
        summary_tree.configure(yscrollcommand=summary_scroll.set)
        summary_frame.grid_rowconfigure(0, weight=1)
        summary_frame.grid_columnconfigure(0, weight=1)

        detail_label = tk.Label(frame, text="Cost Records", bg=palette["surface"], fg=palette["text"], font=("Segoe UI", 10, "bold"))
        detail_label.pack(anchor="w", padx=10, pady=(2, 0))

        def period_filter_provider():
            start_date, end_date = self.get_period_date_range(view_var.get(), selected_period["value"])
            if not start_date or not end_date:
                return None
            return {"start_date": start_date, "end_date": end_date}

        detail_frame = tk.Frame(frame, bg=palette["surface"])
        detail_frame.pack(fill="both", expand=True, padx=10, pady=(4, 10))
        detail_panel = self.build_cost_records_panel(
            detail_frame,
            enable_edit=enable_edit,
            palette=palette,
            period_filter_provider=period_filter_provider,
        )

        def set_period(period):
            selected_period["value"] = period
            selected_var.set(f"Selected Period: {period}" if period else "Selected Period: (none)")
            detail_label.configure(text=f"Cost Records - {period}" if period else "Cost Records")
            detail_panel["refresh"]()

        def load_summary():
            rows = self.fetch_cost_summary_by_period(view_var.get())
            for item in summary_tree.get_children():
                summary_tree.delete(item)
            for period, count_val, amount_val, vat_val, total_val in rows:
                summary_tree.insert(
                    "",
                    "end",
                    values=(
                        period,
                        f"{int(count_val):,}",
                        self.format_cell(amount_val, "money"),
                        self.format_cell(vat_val, "money"),
                        self.format_cell(total_val, "money"),
                    ),
                )
            if rows:
                first_item = summary_tree.get_children()[0]
                summary_tree.selection_set(first_item)
                set_period(rows[0][0])
            else:
                set_period(None)

        def on_summary_select(event=None):
            selection = summary_tree.selection()
            if not selection:
                return
            values = summary_tree.item(selection[0]).get("values", [])
            set_period(values[0] if values else None)

        tk.Button(control_frame, text="Refresh", command=load_summary, bg=palette["accent"], fg="white", width=10).pack(side="right")
        view_combo.bind("<<ComboboxSelected>>", lambda event: load_summary())
        summary_tree.bind("<<TreeviewSelect>>", on_summary_select)
        load_summary()

    def create_taxation_tab(self, notebook):
        frame = tk.Frame(notebook, bg="white")
        notebook.add(frame, text="Taxation (VAT)")

        control_frame = tk.Frame(frame, bg="white")
        control_frame.pack(fill="x", padx=10, pady=10)

        tk.Label(control_frame, text="Start Date (YYYY-MM-DD):", bg="white").grid(row=0, column=0, sticky="e", padx=6, pady=6)
        start_var = tk.StringVar(value="2025-10-01")
        start_entry = tk.Entry(control_frame, textvariable=start_var, width=14)
        start_entry.grid(row=0, column=1, sticky="w", padx=6, pady=6)

        tk.Label(control_frame, text="End Date (YYYY-MM-DD):", bg="white").grid(row=0, column=2, sticky="e", padx=6, pady=6)
        end_var = tk.StringVar(value="2025-12-31")
        end_entry = tk.Entry(control_frame, textvariable=end_var, width=14)
        end_entry.grid(row=0, column=3, sticky="w", padx=6, pady=6)

        tk.Label(control_frame, text="VAT Rate:", bg="white").grid(row=0, column=4, sticky="e", padx=6, pady=6)
        vat_rate_var = tk.StringVar(value="0.08")
        vat_rate_entry = tk.Entry(control_frame, textvariable=vat_rate_var, width=8)
        vat_rate_entry.grid(row=0, column=5, sticky="w", padx=6, pady=6)

        inputs_frame = tk.Frame(frame, bg="white")
        inputs_frame.pack(fill="x", padx=10, pady=5)

        tk.Label(inputs_frame, text="Carryover VAT credit [22]:", bg="white").grid(row=0, column=0, sticky="e", padx=6, pady=4)
        carry_var = tk.StringVar(value="0")
        tk.Entry(inputs_frame, textvariable=carry_var, width=14).grid(row=0, column=1, sticky="w", padx=6, pady=4)

        tk.Label(inputs_frame, text="Adjustment decrease [37]:", bg="white").grid(row=0, column=2, sticky="e", padx=6, pady=4)
        adj_down_var = tk.StringVar(value="0")
        tk.Entry(inputs_frame, textvariable=adj_down_var, width=14).grid(row=0, column=3, sticky="w", padx=6, pady=4)

        tk.Label(inputs_frame, text="Adjustment increase [38]:", bg="white").grid(row=0, column=4, sticky="e", padx=6, pady=4)
        adj_up_var = tk.StringVar(value="0")
        tk.Entry(inputs_frame, textvariable=adj_up_var, width=14).grid(row=0, column=5, sticky="w", padx=6, pady=4)

        tk.Label(inputs_frame, text="Transferred VAT [39a]:", bg="white").grid(row=1, column=0, sticky="e", padx=6, pady=4)
        transfer_var = tk.StringVar(value="0")
        tk.Entry(inputs_frame, textvariable=transfer_var, width=14).grid(row=1, column=1, sticky="w", padx=6, pady=4)

        tk.Label(inputs_frame, text="VAT refund requested [42]:", bg="white").grid(row=1, column=2, sticky="e", padx=6, pady=4)
        refund_var = tk.StringVar(value="0")
        tk.Entry(inputs_frame, textvariable=refund_var, width=14).grid(row=1, column=3, sticky="w", padx=6, pady=4)

        report_frame = tk.Frame(frame, bg="white")
        report_frame.pack(fill="both", expand=True, padx=10, pady=10)

        columns = ("Code", "Description", "Value")
        tree = ttk.Treeview(report_frame, columns=columns, show="headings")
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=240 if col != "Value" else 140, anchor="w")
        tree.pack(fill="both", expand=True)

        def parse_input(value: str) -> float:
            return self.parse_float_input(value) or 0.0

        def calculate_report():
            start_date = start_var.get().strip()
            end_date = end_var.get().strip()
            vat_rate = parse_input(vat_rate_var.get())
            carryover = parse_input(carry_var.get())
            adj_down = parse_input(adj_down_var.get())
            adj_up = parse_input(adj_up_var.get())
            transferred = parse_input(transfer_var.get())
            refund = parse_input(refund_var.get())

            try:
                conn = sqlite3.connect(FINANCIAL_DB)
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT COALESCE(SUM(gross_sales), 0) FROM Sales WHERE sale_date BETWEEN ? AND ?",
                    (start_date, end_date),
                )
                sales_taxable = cursor.fetchone()[0] or 0

                cursor.execute(
                    "SELECT COALESCE(SUM(amount), 0) FROM Costs WHERE cost_date BETWEEN ? AND ?",
                    (start_date, end_date),
                )
                purchases_taxable = cursor.fetchone()[0] or 0
                conn.close()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load tax data: {e}")
                return

            sales_vat = round(sales_taxable * vat_rate, 2)
            purchases_vat = round(purchases_taxable * vat_rate, 2)

            vat_generated = round(sales_vat - purchases_vat, 2)
            vat_payable = round(vat_generated - carryover + adj_down - adj_up - transferred, 2)
            vat_carry = vat_payable if vat_payable < 0 else 0
            vat_due = vat_payable if vat_payable > 0 else 0
            vat_carry_next = round(vat_carry - refund, 2)

            rows = [
                ("[23]", "Purchases taxable value", self.format_cell(purchases_taxable, "money")),
                ("[24]", "Purchases VAT", self.format_cell(purchases_vat, "money")),
                ("[25]", "Purchases VAT deductible this period", self.format_cell(purchases_vat, "money")),
                ("[27]", "Sales taxable value", self.format_cell(sales_taxable, "money")),
                ("[28]", "Sales VAT", self.format_cell(sales_vat, "money")),
                ("[32]", "Sales VAT at standard rate", self.format_cell(sales_taxable, "money")),
                ("[33]", "VAT at standard rate", self.format_cell(sales_vat, "money")),
                ("[34]", "Total sales taxable value", self.format_cell(sales_taxable, "money")),
                ("[35]", "Total sales VAT", self.format_cell(sales_vat, "money")),
                ("[36]", "VAT generated this period", self.format_cell(vat_generated, "money")),
                ("[40a]", "VAT payable for business", self.format_cell(vat_due, "money")),
                ("[41]", "VAT credit carryover", self.format_cell(vat_carry, "money")),
                ("[43]", "VAT carried forward", self.format_cell(vat_carry_next, "money")),
            ]

            for item in tree.get_children():
                tree.delete(item)
            for row in rows:
                tree.insert("", "end", values=row)

        tk.Button(control_frame, text="Refresh", command=calculate_report, bg="#4CAF50", fg="white").grid(
            row=0, column=6, padx=10, pady=6
        )

        calculate_report()

    def show_financial_entry(self):
        for widget in self.content_area.winfo_children():
            widget.destroy()

        tk.Label(self.content_area, text="Point of Sales",
            font=("Segoe UI", 18, "bold"), bg="white").pack(pady=15)

        entry_access = self.current_level in {2, 3, 4}

        if not entry_access:
            tk.Label(self.content_area, text="You do not have access to financial entry workflows.",
                    fg="red", bg="white").pack(pady=20)
            return

        notebook = ttk.Notebook(self.content_area, style="App.TNotebook")
        notebook.pack(expand=True, fill="both", padx=10, pady=10)

        if entry_access:
            self.create_financial_entry_form(notebook)

    def show_approval_view(self):
        for widget in self.content_area.winfo_children():
            widget.destroy()

        tk.Label(self.content_area, text="Approval",
                font=("Segoe UI", 18, "bold"), bg="white").pack(pady=15)

        approve_access = self.current_level in {2, 3, 4}
        if not approve_access:
            tk.Label(self.content_area, text="You do not have access to approval workflows.",
                    fg="red", bg="white").pack(pady=20)
            return

        panel = tk.Frame(self.content_area, bg="white")
        panel.pack(expand=True, fill="both", padx=10, pady=10)
        self.build_approval_panel(panel)

    def show_product_management(self):
        for widget in self.content_area.winfo_children():
            widget.destroy()

        self.product_management_refresh_callback = self.show_product_management

        self.render_product_management_content(self.content_area)

    def render_product_management_content(self, parent):
        for widget in parent.winfo_children():
            widget.destroy()

        tk.Label(parent, text="Product Management",
                font=("Segoe UI", 18, "bold"), bg="white").pack(pady=15)

        if self.current_level not in {2, 3, 4}:
            tk.Label(parent, text="Product management is available to Level 2-4 only.",
                    fg="red", bg="white").pack(pady=20)
            return

        warning_text = (
            "Important: Removing a product does not delete historical sales. "
            "If the SKU is re-added later, it will link to existing history.\n"
            "Current price updates apply to future sales only; historical sales keep their original unit prices.\n"
            "All product changes require approval by Level 2, 3, or 4."
        )
        tk.Label(parent, text=warning_text, fg="#f97316", bg=self.ui_palette["bg"],
            font=("Segoe UI", 9, "italic"), wraplength=650, justify="left").pack(pady=10)

        notebook = ttk.Notebook(parent, style="App.TNotebook")
        notebook.pack(expand=True, fill="both", padx=10, pady=10)

        self.create_product_list_tab(notebook)

        tk.Label(parent, text="Product approvals are handled in the Approval tab.",
            fg=self.ui_palette["muted"], bg=self.ui_palette["bg"],
            font=("Segoe UI", 9, "italic")).pack(pady=5)

    def open_product_management_popup(self):
        if self.current_level not in {2, 3, 4}:
            messagebox.showerror("Access Denied", "Product management is available to Level 2-4 only.")
            return

        if self.product_management_popup and self.product_management_popup.winfo_exists():
            self.product_management_popup.deiconify()
            self.product_management_popup.lift()
            self.product_management_popup.focus_force()
            return

        popup = tk.Toplevel(self.root)
        popup.title("Product Management")
        popup.geometry("1020x700")
        popup.configure(bg=self.ui_palette["bg"])
        popup.transient(self.root)

        container = tk.Frame(popup, bg=self.ui_palette["bg"])
        container.pack(expand=True, fill="both")

        def refresh_popup_view():
            if popup.winfo_exists():
                self.render_product_management_content(container)

        def close_popup():
            if popup.winfo_exists():
                popup.destroy()
            self.product_management_popup = None
            self.product_management_refresh_callback = self.show_product_management

        popup.protocol("WM_DELETE_WINDOW", close_popup)
        self.product_management_popup = popup
        self.product_management_refresh_callback = refresh_popup_view
        refresh_popup_view()

    def add_product_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Product")
        dialog.geometry("420x360")

        fields = [
            ("SKU", "sku"),
            ("Name", "name"),
            ("Category", "category"),
            ("Unit Cost", "unit_cost"),
            ("Current Unit Price", "current_unit_price"),
            ("Image Path", "image_path"),
        ]

        entries = {}
        def browse_image():
            path = filedialog.askopenfilename(
                title="Select Product Image",
                filetypes=[
                    ("Image files", "*.png *.jpg *.jpeg *.gif *.bmp"),
                    ("All files", "*.*"),
                ],
            )
            if path:
                entries["image_path"].delete(0, "end")
                entries["image_path"].insert(0, path)

        for idx, (label, key) in enumerate(fields):
            tk.Label(dialog, text=f"{label}:").grid(row=idx, column=0, padx=10, pady=6, sticky="e")
            entry = tk.Entry(dialog, width=25)
            entry.grid(row=idx, column=1, padx=10, pady=6)
            entries[key] = entry
            if key == "image_path":
                tk.Button(dialog, text="Browse", command=browse_image, width=8).grid(
                    row=idx, column=2, padx=6, pady=6
                )

        def save_product():
            sku = entries["sku"].get().strip()
            if not sku:
                messagebox.showerror("Error", "SKU is required.")
                return
            unit_cost = self.parse_float_input(entries["unit_cost"].get())
            current_unit_price = self.parse_float_input(entries["current_unit_price"].get())
            raw_image_path = entries["image_path"].get().strip() or None
            image_path = raw_image_path
            if image_path:
                is_valid, error_message = self.validate_image_extension(image_path)
                if not is_valid:
                    messagebox.showerror(
                        "Error",
                        error_message,
                    )
                    return
                try:
                    image_path = self.persist_product_image(sku, raw_image_path)
                except Exception as exc:
                    messagebox.showerror("Error", f"Failed to save product image: {exc}")
                    return

            payload = {
                "sku": sku,
                "name": entries["name"].get().strip() or None,
                "category": entries["category"].get().strip() or None,
                "unit_cost": unit_cost,
                "current_unit_price": current_unit_price,
                "image_path": image_path,
            }

            try:
                self.submit_pending_entry("ProductAdd", payload)
                self.log_action("REQUEST_PRODUCT_ADD", f"Requested add product {sku}")
                messagebox.showinfo("Success", "Product change submitted for approval")
                dialog.destroy()
                if callable(self.product_management_refresh_callback):
                    self.product_management_refresh_callback()
                else:
                    self.show_product_management()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to submit product add: {e}")

        tk.Button(dialog, text="Save", command=save_product, bg="#4CAF50", fg="white", width=16).grid(
            row=len(fields), column=0, columnspan=2, pady=15
        )

    def update_product_price_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Adjust Product Pricing")
        dialog.geometry("380x260")

        tk.Label(dialog, text="Product SKU:").grid(row=0, column=0, padx=10, pady=8, sticky="e")
        sku_entry = tk.Entry(dialog, width=25)
        sku_entry.grid(row=0, column=1, padx=10, pady=8)

        tk.Label(dialog, text="New Unit Cost:").grid(row=1, column=0, padx=10, pady=8, sticky="e")
        cost_entry = tk.Entry(dialog, width=25)
        cost_entry.grid(row=1, column=1, padx=10, pady=8)

        tk.Label(dialog, text="New Current Unit Price:").grid(row=2, column=0, padx=10, pady=8, sticky="e")
        price_entry = tk.Entry(dialog, width=25)
        price_entry.grid(row=2, column=1, padx=10, pady=8)

        tk.Label(
            dialog,
            text="Historical sales keep their original unit prices. New price applies to future sales only.",
            fg="#546E7A",
            font=("Segoe UI", 8, "italic"),
            wraplength=340,
        ).grid(row=3, column=0, columnspan=2, padx=10, pady=8)

        def update_price():
            sku = sku_entry.get().strip()
            if not sku:
                messagebox.showerror("Error", "SKU is required.")
                return
            unit_cost = self.parse_float_input(cost_entry.get())
            current_unit_price = self.parse_float_input(price_entry.get())
            if unit_cost is None and current_unit_price is None:
                messagebox.showerror("Error", "Enter a valid unit cost or current unit price.")
                return
            try:
                payload = {"sku": sku, "unit_cost": unit_cost, "current_unit_price": current_unit_price}
                self.submit_pending_entry("ProductUpdate", payload)
                self.log_action("REQUEST_PRODUCT_UPDATE", f"Requested pricing update for {sku}")
                messagebox.showinfo("Success", "Price update submitted for approval")
                dialog.destroy()
                if callable(self.product_management_refresh_callback):
                    self.product_management_refresh_callback()
                else:
                    self.show_product_management()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to submit price update: {e}")

        tk.Button(dialog, text="Update", command=update_price, bg="#607D8B", fg="white", width=16).grid(
            row=3, column=0, columnspan=2, pady=12
        )

    def update_product_image_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Update Product Image")
        dialog.geometry("420x220")

        tk.Label(dialog, text="Product SKU:").grid(row=0, column=0, padx=10, pady=8, sticky="e")
        sku_entry = tk.Entry(dialog, width=25)
        sku_entry.grid(row=0, column=1, padx=10, pady=8)

        tk.Label(dialog, text="Image Path:").grid(row=1, column=0, padx=10, pady=8, sticky="e")
        image_entry = tk.Entry(dialog, width=25)
        image_entry.grid(row=1, column=1, padx=10, pady=8)

        def browse_image():
            path = filedialog.askopenfilename(
                title="Select Product Image",
                filetypes=[
                    ("Image files", "*.png *.jpg *.jpeg *.gif *.bmp"),
                    ("All files", "*.*"),
                ],
            )
            if path:
                image_entry.delete(0, "end")
                image_entry.insert(0, path)

        tk.Button(dialog, text="Browse", command=browse_image, width=10).grid(
            row=1, column=2, padx=6, pady=8
        )

        def update_image():
            sku = sku_entry.get().strip()
            raw_image_path = image_entry.get().strip()
            image_path = raw_image_path
            if not sku:
                messagebox.showerror("Error", "SKU is required.")
                return
            if not image_path:
                messagebox.showerror("Error", "Image path is required.")
                return
            is_valid, error_message = self.validate_image_extension(image_path)
            if not is_valid:
                messagebox.showerror(
                    "Error",
                    error_message,
                )
                return
            try:
                image_path = self.persist_product_image(sku, raw_image_path)
            except Exception as exc:
                messagebox.showerror("Error", f"Failed to save product image: {exc}")
                return
            try:
                payload = {"sku": sku, "image_path": image_path}
                self.submit_pending_entry("ProductUpdate", payload)
                self.log_action("REQUEST_PRODUCT_UPDATE", f"Requested image update for {sku}")
                messagebox.showinfo("Success", "Image update submitted for approval")
                dialog.destroy()
                if callable(self.product_management_refresh_callback):
                    self.product_management_refresh_callback()
                else:
                    self.show_product_management()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to submit image update: {e}")

    def update_product_dialog(self, sku, unit_cost=None, current_unit_price=None, image_path=None):
        dialog = tk.Toplevel(self.root)
        dialog.title("Edit Product")
        dialog.geometry("420x300")

        tk.Label(dialog, text="Product SKU:").grid(row=0, column=0, padx=10, pady=8, sticky="e")
        sku_entry = tk.Entry(dialog, width=25)
        sku_entry.grid(row=0, column=1, padx=10, pady=8)
        sku_entry.insert(0, sku)
        sku_entry.config(state="readonly")

        tk.Label(dialog, text="Unit Cost:").grid(row=1, column=0, padx=10, pady=8, sticky="e")
        cost_entry = tk.Entry(dialog, width=25)
        cost_entry.grid(row=1, column=1, padx=10, pady=8)
        if unit_cost not in (None, ""):
            cost_entry.insert(0, str(unit_cost))

        tk.Label(dialog, text="Current Unit Price:").grid(row=2, column=0, padx=10, pady=8, sticky="e")
        price_entry = tk.Entry(dialog, width=25)
        price_entry.grid(row=2, column=1, padx=10, pady=8)
        if current_unit_price not in (None, ""):
            price_entry.insert(0, str(current_unit_price))

        tk.Label(dialog, text="Image Path:").grid(row=3, column=0, padx=10, pady=8, sticky="e")
        image_entry = tk.Entry(dialog, width=25)
        image_entry.grid(row=3, column=1, padx=10, pady=8)
        if image_path:
            image_entry.insert(0, str(image_path))

        def browse_image():
            path = filedialog.askopenfilename(
                title="Select Product Image",
                filetypes=[
                    ("Image files", "*.png *.jpg *.jpeg *.gif *.bmp"),
                    ("All files", "*.*"),
                ],
            )
            if path:
                image_entry.delete(0, "end")
                image_entry.insert(0, path)

        tk.Button(dialog, text="Browse", command=browse_image, width=10).grid(
            row=3, column=2, padx=6, pady=8
        )

        def update_product():
            updated_cost = self.parse_float_input(cost_entry.get())
            updated_price = self.parse_float_input(price_entry.get())
            raw_updated_image = image_entry.get().strip() or None
            updated_image = raw_updated_image
            if updated_image:
                is_valid, error_message = self.validate_image_extension(updated_image)
                if not is_valid:
                    messagebox.showerror(
                        "Error",
                        error_message,
                    )
                    return
                try:
                    updated_image = self.persist_product_image(sku, raw_updated_image)
                except Exception as exc:
                    messagebox.showerror("Error", f"Failed to save product image: {exc}")
                    return

            payload = {"sku": sku}
            if updated_cost is not None:
                payload["unit_cost"] = updated_cost
            if updated_price is not None:
                payload["current_unit_price"] = updated_price
            if updated_image is not None:
                payload["image_path"] = updated_image

            if len(payload) == 1:
                messagebox.showerror("Error", "Provide at least one update.")
                return

            try:
                self.submit_pending_entry("ProductUpdate", payload)
                self.log_action("REQUEST_PRODUCT_UPDATE", f"Requested update for {sku}")
                messagebox.showinfo("Success", "Product update submitted for approval")
                dialog.destroy()
                if callable(self.product_management_refresh_callback):
                    self.product_management_refresh_callback()
                else:
                    self.show_product_management()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to submit product update: {e}")

        tk.Button(dialog, text="Update", command=update_product, bg="#607D8B", fg="white", width=16).grid(
            row=4, column=0, columnspan=2, pady=14
        )

    def remove_product_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Remove Product")
        dialog.geometry("380x220")

        tk.Label(dialog, text="Product SKU:").grid(row=0, column=0, padx=10, pady=8, sticky="e")
        sku_entry = tk.Entry(dialog, width=25)
        sku_entry.grid(row=0, column=1, padx=10, pady=8)

        tk.Label(
            dialog,
            text=(
                "Removal does not delete historical sales. "
                "Re-adding the same SKU will reconnect to history."
            ),
            fg="#ff6f00",
            font=("Segoe UI", 8, "italic"),
            wraplength=330,
        ).grid(row=1, column=0, columnspan=2, padx=10, pady=8)

        def remove_product():
            sku = sku_entry.get().strip()
            if not sku:
                messagebox.showerror("Error", "SKU is required.")
                return
            if not messagebox.askyesno("Confirm", f"Remove product {sku}? Historical sales will remain."):
                return
            try:
                payload = {"sku": sku}
                self.submit_pending_entry("ProductRemove", payload)
                self.log_action("REQUEST_PRODUCT_REMOVE", f"Requested remove product {sku}")
                messagebox.showinfo("Success", "Product removal submitted for approval")
                dialog.destroy()
                if callable(self.product_management_refresh_callback):
                    self.product_management_refresh_callback()
                else:
                    self.show_product_management()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to submit product removal: {e}")

        tk.Button(dialog, text="Remove", command=remove_product, bg="#f44336", fg="white", width=16).grid(
            row=2, column=0, columnspan=2, pady=12
        )

    def create_product_list_tab(self, notebook):
        frame = tk.Frame(notebook, bg=self.ui_palette["bg"])
        notebook.add(frame, text="Catalog Requests")

        btn_frame = tk.Frame(frame, bg=self.ui_palette["bg"])
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="Request Add", command=self.add_product_dialog,
             bg=self.ui_palette["accent"], fg="white", width=15, height=2,
             relief="flat").pack(side="left", padx=8)
        tk.Button(btn_frame, text="Request Removal", command=self.remove_product_dialog,
             bg=self.ui_palette["danger"], fg="white", width=16, height=2,
             relief="flat").pack(side="left", padx=8)

        list_frame = tk.Frame(frame, bg=self.ui_palette["bg"])
        list_frame.pack(pady=10, padx=20, fill="both", expand=True)

        tree = ttk.Treeview(
            list_frame,
            columns=("SKU", "Name", "Category", "Unit Cost", "Current Unit Price", "Image"),
            show="headings",
            style="App.Treeview",
        )
        for col in ("SKU", "Name", "Category", "Unit Cost", "Current Unit Price", "Image"):
            tree.heading(col, text=col)
            tree.column(col, width=160)

        tree.pack(fill="both", expand=True)

        hover_state = {"row": None}
        edit_popup = tk.Toplevel(self.root)
        edit_popup.withdraw()
        edit_popup.overrideredirect(True)
        edit_popup.attributes("-topmost", True)
        edit_button = tk.Button(
            edit_popup,
            text="Edit",
            command=lambda: on_edit_hover(),
            bg=self.ui_palette["accent_alt"],
            fg="white",
            relief="flat",
            width=6,
        )
        edit_button.pack(padx=1, pady=1)

        def on_edit_hover():
            row_id = hover_state.get("row")
            if not row_id:
                return
            values = tree.item(row_id)["values"]
            if len(values) < 6:
                return
            sku, _, _, unit_cost, current_unit_price, image_path = values
            hide_edit_button()
            self.update_product_dialog(sku, unit_cost, current_unit_price, image_path)

        def hide_edit_button():
            edit_popup.withdraw()
            hover_state["row"] = None

        def conditional_hide():
            x, y = self.root.winfo_pointerxy()
            widget = self.root.winfo_containing(x, y)
            if widget and (str(widget).startswith(str(tree)) or str(widget).startswith(str(edit_popup))):
                return
            hide_edit_button()

        def schedule_hide():
            if hover_state.get("hide_after"):
                edit_popup.after_cancel(hover_state["hide_after"])
            hover_state["hide_after"] = edit_popup.after(450, conditional_hide)

        def cancel_hide():
            if hover_state.get("hide_after"):
                edit_popup.after_cancel(hover_state["hide_after"])
                hover_state["hide_after"] = None

        def on_hover(event):
            row_id = tree.identify_row(event.y)
            if not row_id:
                hide_edit_button()
                self.schedule_sku_preview_hide()
                return
            bbox = tree.bbox(row_id)
            if not bbox:
                hide_edit_button()
                self.schedule_sku_preview_hide()
                return
            x, y, width, height = bbox
            hover_state["row"] = row_id
            tree.update_idletasks()
            popup_x = tree.winfo_rootx() + x + width - 56
            popup_y = tree.winfo_rooty() + y + 2
            edit_popup.geometry(f"60x{max(height, 22)}+{popup_x}+{popup_y}")
            edit_popup.deiconify()
            edit_popup.lift()

            column_id = tree.identify_column(event.x)
            if column_id == "#1":
                row_values = tree.item(row_id).get("values", [])
                sku_value = str(row_values[0]).strip() if row_values else ""
                image_path = row_values[5] if len(row_values) > 5 else None
                if sku_value:
                    self.show_sku_preview(sku_value, event.x_root, event.y_root, image_path=image_path)
            else:
                self.schedule_sku_preview_hide()

        edit_popup.bind("<Enter>", lambda event: cancel_hide())
        edit_popup.bind("<Leave>", lambda event: schedule_hide())

        tree.bind("<Motion>", on_hover)
        tree.bind("<Leave>", lambda event: (schedule_hide(), self.schedule_sku_preview_hide()))
        list_frame.bind("<Leave>", lambda event: (schedule_hide(), self.schedule_sku_preview_hide()))

        try:
            conn = sqlite3.connect(FINANCIAL_DB)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT sku, name, category, unit_cost, current_unit_price, image_path FROM Products ORDER BY sku"
            )
            rows = cursor.fetchall()
            conn.close()
            for row in rows:
                tree.insert("", "end", values=row)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load products: {e}")

    def show_financial_entry_form_error(self):
        messagebox.showerror("Error", "Entry form not available.")

    def create_financial_entry_form(self, notebook):
        frame = tk.Frame(notebook, bg="#f5f6f8")
        notebook.add(frame, text="Point of Sales")

        if not hasattr(self, "pos_ui_state"):
            self.pos_ui_state = {
                "theme": "light",
                "high_contrast": False,
                "search": "",
                "category": "All",
                "cart": {},
                "nav_view": "Dashboard",
                "entry_type": "Sales",
            }
        else:
            self.pos_ui_state.setdefault("nav_view", "Dashboard")
            self.pos_ui_state.setdefault("entry_type", "Sales")
            if self.pos_ui_state.get("nav_view") == "Inventory":
                self.pos_ui_state["nav_view"] = "Entry"

        def load_products():
            try:
                conn = sqlite3.connect(FINANCIAL_DB)
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT sku, name, category, current_unit_price, image_path FROM Products ORDER BY name"
                )
                rows = cursor.fetchall()
                conn.close()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load products: {e}")
                rows = []
            products = []
            for row in rows:
                products.append(
                    {
                        "sku": row[0],
                        "name": row[1] or "Unnamed",
                        "category": row[2] or "Uncategorized",
                        "unit_price": self.parse_float_input(row[3]) or 0.0,
                        "image_path": row[4] if len(row) > 4 else None,
                    }
                )
            return products

        live_inventory = {"snapshot": {}}
        ui_refresh = {"callback": None}

        def refresh_inventory_snapshot():
            try:
                live_inventory["snapshot"] = self.get_inventory_snapshot()
            except Exception as exc:
                messagebox.showerror("Error", f"Failed to load inventory status: {exc}")
                live_inventory["snapshot"] = {}

        def available_units_for_sku(sku):
            item = live_inventory["snapshot"].get(sku, {})
            available = item.get("available", 0)
            return self.parse_int_input(available) or 0

        def stock_alert_text(sku, available):
            level = self.stock_alert_level(available)
            if level == "critical":
                return f"{sku}: stock is 0 or below ({available})"
            if level == "low":
                return f"{sku}: low stock ({available})"
            return ""

        def current_unit_cost_for_sku(sku):
            item = live_inventory["snapshot"].get(sku, {})
            if item.get("unit_cost") is not None:
                return item["unit_cost"]
            conn = sqlite3.connect(FINANCIAL_DB)
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT unit_cost FROM Products WHERE sku = ?", (sku,))
                row = cursor.fetchone()
                if row and row[0] is not None:
                    return self.parse_float_input(row[0]) or 0.0
            finally:
                conn.close()
            return 0.0

        def validate_cart_stock_levels():
            refresh_inventory_snapshot()
            alerts = []
            for item in self.pos_ui_state["cart"].values():
                available = available_units_for_sku(item["sku"])
                alert = stock_alert_text(item["sku"], available)
                if alert:
                    alerts.append((item["sku"], item["qty"], available, alert))
            return alerts

        def open_stock_adjustment_dialog():
            dialog = tk.Toplevel(self.root)
            dialog.title("Manual Stock Adjustment")
            dialog.geometry("420x320")
            dialog.configure(bg="#f5f6f8")
            registered_product_skus = self.get_registered_product_skus()

            tk.Label(
                dialog,
                text="Manual Stock Adjustment",
                font=("Segoe UI", 12, "bold"),
                bg="#f5f6f8",
            ).pack(pady=10)

            form = tk.Frame(dialog, bg="#f5f6f8")
            form.pack(fill="x", padx=14, pady=8)

            tk.Label(form, text="Date (YYYY-MM-DD)", bg="#f5f6f8").grid(row=0, column=0, sticky="w", pady=4)
            date_var = tk.StringVar(value=datetime.now().date().isoformat())
            tk.Entry(form, textvariable=date_var, width=28).grid(row=0, column=1, sticky="e", pady=4)

            tk.Label(form, text="Product SKU", bg="#f5f6f8").grid(row=1, column=0, sticky="w", pady=4)
            sku_var = tk.StringVar()
            sku_combo = ttk.Combobox(
                form,
                textvariable=sku_var,
                values=registered_product_skus,
                state="readonly",
                width=26,
            )
            sku_combo.grid(row=1, column=1, sticky="e", pady=4)
            self.bind_widget_sku_preview(sku_combo, lambda: sku_var.get())

            tk.Label(form, text="Quantity Delta", bg="#f5f6f8").grid(row=2, column=0, sticky="w", pady=4)
            delta_var = tk.StringVar()
            tk.Entry(form, textvariable=delta_var, width=28).grid(row=2, column=1, sticky="e", pady=4)

            tk.Label(form, text="Unit Cost (optional)", bg="#f5f6f8").grid(row=3, column=0, sticky="w", pady=4)
            cost_var = tk.StringVar()
            tk.Entry(form, textvariable=cost_var, width=28).grid(row=3, column=1, sticky="e", pady=4)

            tk.Label(form, text="Reason", bg="#f5f6f8").grid(row=4, column=0, sticky="w", pady=4)
            reason_var = tk.StringVar()
            tk.Entry(form, textvariable=reason_var, width=28).grid(row=4, column=1, sticky="e", pady=4)

            def submit_adjustment():
                adjust_date = self.parse_date_input(date_var.get())
                sku = sku_var.get().strip()
                delta = self.parse_int_input(delta_var.get())
                reason = reason_var.get().strip() or "Manual correction"

                if not adjust_date:
                    messagebox.showerror("Error", "Invalid date. Use YYYY-MM-DD format.")
                    return
                if not sku:
                    messagebox.showerror("Error", "Product SKU is required.")
                    return
                if not self.product_exists(sku):
                    messagebox.showerror("Error", f"Product SKU '{sku}' does not exist in catalog.")
                    return
                if delta is None or delta == 0:
                    messagebox.showerror("Error", "Quantity Delta must be a non-zero integer.")
                    return

                refresh_inventory_snapshot()
                available = available_units_for_sku(sku)
                projected = available + delta
                alert = stock_alert_text(sku, projected)
                if alert:
                    messagebox.showwarning("Inventory Warning", f"Adjustment will set {alert}.")

                entered_cost = self.parse_float_input(cost_var.get())
                unit_cost = entered_cost if entered_cost is not None else current_unit_cost_for_sku(sku)
                tax_rate = 8.0
                pre_tax_total = (unit_cost or 0.0) * delta
                tax_amount = pre_tax_total * tax_rate / 100.0
                total = pre_tax_total + tax_amount
                note_text = f"POS stock adjustment: {reason}"

                conn = sqlite3.connect(FINANCIAL_DB)
                try:
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        INSERT INTO Stock (date, product_sku, unit_cost, unit_in, tax_rate, tax_amount, total, note)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (adjust_date, sku, unit_cost, delta, tax_rate, tax_amount, total, note_text),
                    )
                    cursor.execute(
                        """
                        INSERT INTO Logs (log_date, log_type, product_sku, details)
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            adjust_date,
                            "StockAdjustment",
                            sku,
                            f"delta={delta}, unit_cost={unit_cost}, tax_rate={tax_rate}, tax_amount={tax_amount}, reason={reason}, by={self.current_user['user_id']}",
                        ),
                    )
                    conn.commit()
                finally:
                    conn.close()

                self.log_action(
                    "STOCK_ADJUSTMENT",
                    f"Adjusted stock for {sku}: {delta} ({reason})",
                )
                messagebox.showinfo("Success", "Stock adjustment saved.")
                if ui_refresh["callback"]:
                    ui_refresh["callback"]()
                dialog.destroy()

            tk.Button(
                dialog,
                text="Apply Adjustment",
                command=submit_adjustment,
                bg=self.ui_palette["accent_alt"],
                fg="white",
                width=20,
            ).pack(pady=12)

        def render_inline_entry_panel(parent):
            for widget in parent.winfo_children():
                widget.destroy()

            tk.Label(
                parent,
                text="Financial Entry",
                font=("Segoe UI", 11, "bold"),
                bg="#f5f6f8",
            ).pack(anchor="w", padx=8, pady=(6, 2))

            form_frame = tk.Frame(parent, bg="#f5f6f8")
            form_frame.pack(fill="x", padx=8, pady=4)

            tk.Label(form_frame, text="Entry Type:", bg="#f5f6f8").grid(
                row=0, column=0, sticky="e", padx=6, pady=4
            )
            entry_type_var = tk.StringVar(value=self.pos_ui_state.get("entry_type", "Sales"))
            entry_type_combo = ttk.Combobox(
                form_frame,
                textvariable=entry_type_var,
                values=["Sales", "Costs", "Stock", "Timeline"],
                state="readonly",
                width=20,
            )
            entry_type_combo.grid(row=0, column=1, sticky="w", padx=6, pady=4)

            tk.Label(
                form_frame,
                text="Use YYYY-MM-DD dates",
                bg="#f5f6f8",
                fg="#546E7A",
                font=("Segoe UI", 8, "italic"),
            ).grid(row=0, column=2, sticky="w", padx=6, pady=4)

            fields_frame = tk.Frame(parent, bg="#f5f6f8")
            fields_frame.pack(fill="x", padx=8, pady=4)
            btn_frame = tk.Frame(parent, bg="#f5f6f8")
            btn_frame.pack(fill="x", padx=8, pady=6)
            field_vars = {}
            sales_receipt_state = {"products": [], "services": []}

            def export_receipt_pdf(receipt_payload):
                try:
                    from reportlab.lib.pagesizes import A4
                    from reportlab.pdfgen import canvas
                except Exception:
                    messagebox.showerror("Error", "PDF export requires reportlab package.")
                    return None

                receipt_no = receipt_payload.get("receipt_no") or self.generate_receipt_no()
                safe_receipt_no = re.sub(r"[^A-Za-z0-9_-]", "_", receipt_no)
                out_dir = BASE_DIR / "artifacts" / "receipts"
                out_dir.mkdir(parents=True, exist_ok=True)
                out_file = out_dir / f"{safe_receipt_no}.pdf"

                doc = canvas.Canvas(str(out_file), pagesize=A4)
                width, height = A4
                y = height - 50

                customer = receipt_payload.get("customer", {})
                products = receipt_payload.get("products", [])
                services = receipt_payload.get("services", [])

                left_logo = BASE_DIR / "Logo" / "Logo.png"
                right_logo = BASE_DIR / "Logo" / "Safefire.png"
                logo_h = 42
                top_y = height - 58
                try:
                    if left_logo.exists():
                        doc.drawImage(
                            str(left_logo),
                            40,
                            top_y,
                            height=logo_h,
                            width=150,
                            preserveAspectRatio=True,
                            mask="auto",
                        )
                except Exception:
                    pass
                try:
                    if right_logo.exists():
                        doc.drawImage(
                            str(right_logo),
                            width - 170,
                            top_y,
                            height=logo_h,
                            width=130,
                            preserveAspectRatio=True,
                            mask="auto",
                        )
                except Exception:
                    pass

                y = height - 96

                doc.setFont("Helvetica-Bold", 18)
                doc.drawString(40, y, "Sales Receipt")
                y -= 24
                doc.setFont("Helvetica", 10)
                doc.drawString(40, y, f"Receipt No: {receipt_no}")
                doc.drawString(240, y, f"Sale Date: {receipt_payload.get('sale_date', '')}")
                y -= 20

                doc.setFont("Helvetica-Bold", 12)
                doc.drawString(40, y, "Customer Information")
                y -= 16
                doc.setFont("Helvetica", 10)
                doc.drawString(40, y, f"Name: {customer.get('name', '')}")
                y -= 14
                doc.drawString(40, y, f"Phone: {customer.get('phone', '')}")
                y -= 14
                doc.drawString(40, y, f"Email: {customer.get('email', '')}")
                y -= 14
                doc.drawString(40, y, f"Address: {customer.get('address', '')}")
                y -= 24

                def draw_section(title, lines):
                    nonlocal y
                    doc.setFont("Helvetica-Bold", 11)
                    doc.drawString(40, y, title)
                    y -= 16
                    doc.setFont("Helvetica-Bold", 10)
                    doc.drawString(40, y, "Item")
                    doc.drawString(280, y, "Unit")
                    doc.drawString(360, y, "Qty")
                    doc.drawString(430, y, "Total")
                    y -= 14
                    doc.setFont("Helvetica", 10)
                    for line in lines:
                        doc.drawString(40, y, str(line.get("item_name", ""))[:42])
                        doc.drawRightString(340, y, f"{line.get('unit_price', 0):,.0f}")
                        doc.drawRightString(400, y, str(line.get("quantity", 0)))
                        doc.drawRightString(520, y, f"{line.get('line_total', 0):,.0f}")
                        y -= 14
                    y -= 8

                draw_section("Products", products)
                draw_section("Services", services)

                doc.setFont("Helvetica", 10)
                doc.drawRightString(520, y, f"Subtotal: {receipt_payload.get('subtotal', 0):,.0f}")
                y -= 14
                doc.drawRightString(520, y, f"Service Total: {receipt_payload.get('service_total', 0):,.0f}")
                y -= 14
                doc.drawRightString(
                    520,
                    y,
                    f"GTGT ({receipt_payload.get('tax_rate', 0):.2f}%): {receipt_payload.get('tax_amount', 0):,.0f}",
                )
                y -= 16
                doc.setFont("Helvetica-Bold", 12)
                doc.drawRightString(520, y, f"Grand Total: {receipt_payload.get('total', 0):,.0f}")

                doc.save()
                return str(out_file)

            def build_fields(entry_type):
                self.pos_ui_state["entry_type"] = entry_type
                for widget in fields_frame.winfo_children():
                    widget.destroy()
                field_vars.clear()

                for widget in btn_frame.winfo_children():
                    widget.destroy()

                registered_product_skus = self.get_registered_product_skus()

                if entry_type == "Sales":
                    sales_receipt_state["products"] = []
                    sales_receipt_state["services"] = []
                    sales_receipt_state["pdf_path"] = None

                    customer_frame = tk.LabelFrame(fields_frame, text="Customer", bg="#f5f6f8")
                    customer_frame.pack(fill="x", padx=4, pady=4)

                    field_vars["sale_date"] = tk.StringVar(value=datetime.now().date().isoformat())
                    field_vars["receipt_no"] = tk.StringVar(value=self.generate_receipt_no())
                    field_vars["customer_name"] = tk.StringVar()
                    field_vars["customer_phone"] = tk.StringVar()
                    field_vars["customer_email"] = tk.StringVar()
                    field_vars["customer_address"] = tk.StringVar()
                    field_vars["tax_rate"] = tk.StringVar(value="0")
                    field_vars["note"] = tk.StringVar()

                    customer_fields = [
                        ("Sale Date", "sale_date"),
                        ("Receipt No", "receipt_no"),
                        ("Name", "customer_name"),
                        ("Phone", "customer_phone"),
                        ("Email", "customer_email"),
                        ("Address", "customer_address"),
                    ]
                    for idx, (label, key) in enumerate(customer_fields):
                        tk.Label(customer_frame, text=label, bg="#f5f6f8").grid(
                            row=idx // 2, column=(idx % 2) * 2, sticky="e", padx=6, pady=4
                        )
                        tk.Entry(customer_frame, textvariable=field_vars[key], width=34).grid(
                            row=idx // 2, column=(idx % 2) * 2 + 1, sticky="w", padx=6, pady=4
                        )

                    lines_frame = tk.Frame(fields_frame, bg="#f5f6f8")
                    lines_frame.pack(fill="x", padx=4, pady=6)

                    product_wrap = tk.LabelFrame(lines_frame, text="Product Sales", bg="#f5f6f8")
                    product_wrap.pack(side="left", fill="both", expand=True, padx=(0, 6))
                    service_wrap = tk.LabelFrame(lines_frame, text="Services", bg="#f5f6f8")
                    service_wrap.pack(side="left", fill="both", expand=True, padx=(6, 0))

                    product_header = tk.Frame(product_wrap, bg="#f5f6f8")
                    product_header.pack(fill="x", padx=4, pady=(4, 2))
                    for idx, (title, width) in enumerate([
                        ("Item", 18),
                        ("Unit Price", 11),
                        ("#Item", 7),
                        ("Total", 11),
                        ("SKU", 12),
                        ("", 3),
                    ]):
                        tk.Label(
                            product_header,
                            text=title,
                            width=width,
                            bg="#d9d9d9",
                            anchor="w",
                            font=("Segoe UI", 9, "bold"),
                        ).grid(row=0, column=idx, padx=1, pady=1, sticky="ew")

                    service_header = tk.Frame(service_wrap, bg="#f5f6f8")
                    service_header.pack(fill="x", padx=4, pady=(4, 2))
                    for idx, (title, width) in enumerate([
                        ("Item", 20),
                        ("Unit Price", 11),
                        ("#Item", 7),
                        ("Total", 11),
                        ("", 3),
                    ]):
                        tk.Label(
                            service_header,
                            text=title,
                            width=width,
                            bg="#d9d9d9",
                            anchor="w",
                            font=("Segoe UI", 9, "bold"),
                        ).grid(row=0, column=idx, padx=1, pady=1, sticky="ew")

                    product_rows_frame = tk.Frame(product_wrap, bg="#f5f6f8")
                    product_rows_frame.pack(fill="x", padx=4, pady=2)
                    service_rows_frame = tk.Frame(service_wrap, bg="#f5f6f8")
                    service_rows_frame.pack(fill="x", padx=4, pady=2)

                    product_rows = []
                    service_rows = []

                    totals_frame = tk.Frame(fields_frame, bg="#f5f6f8")
                    totals_frame.pack(fill="x", padx=4, pady=6)
                    subtotal_var = tk.StringVar(value="0")
                    service_total_var = tk.StringVar(value="0")
                    tax_amount_var = tk.StringVar(value="0")
                    grand_total_var = tk.StringVar(value="0")

                    def recalc_totals():
                        products = []
                        services = []

                        for row in product_rows:
                            item_name = row["item_name"].get().strip()
                            sku = row["sku"].get().strip()
                            unit_price = self.parse_float_input(row["unit_price"].get()) or 0.0
                            quantity = self.parse_int_input(row["quantity"].get()) or 0
                            line_total = unit_price * quantity
                            row["line_total"].set(f"{line_total:,.0f}" if (unit_price or quantity) else "")
                            if item_name or sku or unit_price or quantity:
                                products.append(
                                    {
                                        "line_type": "Product",
                                        "item_name": item_name,
                                        "product_sku": sku or None,
                                        "unit_price": unit_price,
                                        "quantity": quantity,
                                        "line_total": line_total,
                                    }
                                )

                        for row in service_rows:
                            item_name = row["item_name"].get().strip()
                            unit_price = self.parse_float_input(row["unit_price"].get()) or 0.0
                            quantity = self.parse_int_input(row["quantity"].get()) or 0
                            line_total = unit_price * quantity
                            row["line_total"].set(f"{line_total:,.0f}" if (unit_price or quantity) else "")
                            if item_name or unit_price or quantity:
                                services.append(
                                    {
                                        "line_type": "Service",
                                        "item_name": item_name,
                                        "product_sku": None,
                                        "unit_price": unit_price,
                                        "quantity": quantity,
                                        "line_total": line_total,
                                    }
                                )

                        sales_receipt_state["products"] = products
                        sales_receipt_state["services"] = services

                        subtotal = sum(line["line_total"] for line in products)
                        service_total = sum(line["line_total"] for line in services)
                        tax_rate = self.parse_float_input(field_vars["tax_rate"].get()) or 0.0
                        tax_amount = (subtotal + service_total) * tax_rate / 100.0
                        total = subtotal + service_total + tax_amount

                        subtotal_var.set(f"{subtotal:,.0f}")
                        service_total_var.set(f"{service_total:,.0f}")
                        tax_amount_var.set(f"{tax_amount:,.0f}")
                        grand_total_var.set(f"{total:,.0f}")

                    field_vars["tax_rate"].trace_add("write", lambda *args: recalc_totals())

                    tk.Label(totals_frame, text="GTGT Tax %", bg="#f5f6f8").grid(row=0, column=0, sticky="e", padx=6, pady=4)
                    tk.Entry(totals_frame, textvariable=field_vars["tax_rate"], width=8).grid(row=0, column=1, sticky="w", padx=6, pady=4)
                    tk.Label(totals_frame, text="Products", bg="#f5f6f8").grid(row=0, column=2, sticky="e", padx=6)
                    tk.Label(totals_frame, textvariable=subtotal_var, bg="#f5f6f8").grid(row=0, column=3, sticky="w", padx=4)
                    tk.Label(totals_frame, text="Services", bg="#f5f6f8").grid(row=1, column=2, sticky="e", padx=6)
                    tk.Label(totals_frame, textvariable=service_total_var, bg="#f5f6f8").grid(row=1, column=3, sticky="w", padx=4)
                    tk.Label(totals_frame, text="Tax", bg="#f5f6f8").grid(row=2, column=2, sticky="e", padx=6)
                    tk.Label(totals_frame, textvariable=tax_amount_var, bg="#f5f6f8").grid(row=2, column=3, sticky="w", padx=4)
                    tk.Label(totals_frame, text="Total", bg="#f5f6f8", font=("Segoe UI", 9, "bold")).grid(row=3, column=2, sticky="e", padx=6)
                    tk.Label(totals_frame, textvariable=grand_total_var, bg="#f5f6f8", font=("Segoe UI", 9, "bold")).grid(row=3, column=3, sticky="w", padx=4)

                    tk.Label(totals_frame, text="Note", bg="#f5f6f8").grid(row=4, column=0, sticky="e", padx=6, pady=4)
                    tk.Entry(totals_frame, textvariable=field_vars["note"], width=70).grid(row=4, column=1, columnspan=3, sticky="w", padx=6, pady=4)

                    def bind_recalc(var):
                        var.trace_add("write", lambda *args: recalc_totals())

                    def add_product_row():
                        row_frame = tk.Frame(product_rows_frame, bg="#f5f6f8")
                        row_frame.pack(fill="x", pady=1)
                        row = {
                            "frame": row_frame,
                            "item_name": tk.StringVar(),
                            "unit_price": tk.StringVar(),
                            "quantity": tk.StringVar(value="1"),
                            "line_total": tk.StringVar(),
                            "sku": tk.StringVar(),
                        }
                        tk.Entry(row_frame, textvariable=row["item_name"], width=18).grid(row=0, column=0, padx=1)
                        tk.Entry(row_frame, textvariable=row["unit_price"], width=11).grid(row=0, column=1, padx=1)
                        tk.Entry(row_frame, textvariable=row["quantity"], width=7).grid(row=0, column=2, padx=1)
                        tk.Entry(row_frame, textvariable=row["line_total"], width=11, state="readonly").grid(row=0, column=3, padx=1)
                        sku_combo = ttk.Combobox(
                            row_frame,
                            textvariable=row["sku"],
                            values=registered_product_skus,
                            state="readonly",
                            width=12,
                        )
                        sku_combo.grid(row=0, column=4, padx=1)
                        self.bind_widget_sku_preview(sku_combo, lambda current=row: current["sku"].get())

                        def remove_row():
                            if row in product_rows:
                                product_rows.remove(row)
                            row_frame.destroy()
                            recalc_totals()

                        tk.Button(row_frame, text="-", width=2, bg="#bdbdbd", command=remove_row).grid(row=0, column=5, padx=1)
                        product_rows.append(row)
                        for key in ("item_name", "unit_price", "quantity", "sku"):
                            bind_recalc(row[key])
                        recalc_totals()

                    def add_service_row():
                        row_frame = tk.Frame(service_rows_frame, bg="#f5f6f8")
                        row_frame.pack(fill="x", pady=1)
                        row = {
                            "frame": row_frame,
                            "item_name": tk.StringVar(),
                            "unit_price": tk.StringVar(),
                            "quantity": tk.StringVar(value="1"),
                            "line_total": tk.StringVar(),
                        }
                        tk.Entry(row_frame, textvariable=row["item_name"], width=20).grid(row=0, column=0, padx=1)
                        tk.Entry(row_frame, textvariable=row["unit_price"], width=11).grid(row=0, column=1, padx=1)
                        tk.Entry(row_frame, textvariable=row["quantity"], width=7).grid(row=0, column=2, padx=1)
                        tk.Entry(row_frame, textvariable=row["line_total"], width=11, state="readonly").grid(row=0, column=3, padx=1)

                        def remove_row():
                            if row in service_rows:
                                service_rows.remove(row)
                            row_frame.destroy()
                            recalc_totals()

                        tk.Button(row_frame, text="-", width=2, bg="#bdbdbd", command=remove_row).grid(row=0, column=4, padx=1)
                        service_rows.append(row)
                        for key in ("item_name", "unit_price", "quantity"):
                            bind_recalc(row[key])
                        recalc_totals()

                    tk.Button(
                        product_wrap,
                        text="+",
                        bg="#9e9e9e",
                        fg="white",
                        width=3,
                        command=add_product_row,
                    ).pack(anchor="e", padx=6, pady=(3, 5))

                    tk.Button(
                        service_wrap,
                        text="+",
                        bg="#9e9e9e",
                        fg="white",
                        width=3,
                        command=add_service_row,
                    ).pack(anchor="e", padx=6, pady=(3, 5))

                    add_product_row()
                    add_service_row()

                    def build_receipt_payload():
                        recalc_totals()
                        sale_date = self.parse_date_input(field_vars["sale_date"].get())
                        if not sale_date:
                            messagebox.showerror("Error", "Invalid sale date. Use YYYY-MM-DD format.")
                            return None

                        customer = {
                            "name": field_vars["customer_name"].get().strip(),
                            "phone": field_vars["customer_phone"].get().strip(),
                            "email": field_vars["customer_email"].get().strip(),
                            "address": field_vars["customer_address"].get().strip(),
                        }
                        if not all(customer.values()):
                            messagebox.showerror("Error", "Name, phone, email, and address are required.")
                            return None

                        if not sales_receipt_state["products"] and not sales_receipt_state["services"]:
                            messagebox.showerror("Error", "Add at least one product or service line.")
                            return None

                        for product_line in sales_receipt_state["products"]:
                            if not product_line.get("item_name"):
                                messagebox.showerror("Error", "Each product row requires an item name.")
                                return None
                            sku = product_line.get("product_sku")
                            if not sku:
                                messagebox.showerror("Error", "Each product row requires SKU.")
                                return None
                            if not self.product_exists(sku):
                                messagebox.showerror("Error", f"Product SKU '{sku}' does not exist.")
                                return None
                            if (product_line.get("quantity") or 0) <= 0:
                                messagebox.showerror("Error", "Product #Item must be greater than 0.")
                                return None

                        for service_line in sales_receipt_state["services"]:
                            if not service_line.get("item_name"):
                                messagebox.showerror("Error", "Each service row requires an item name.")
                                return None
                            if (service_line.get("quantity") or 0) <= 0:
                                messagebox.showerror("Error", "Service #Item must be greater than 0.")
                                return None

                        tax_rate = self.parse_float_input(field_vars["tax_rate"].get())
                        if tax_rate is None:
                            messagebox.showerror("Error", "GTGT tax rate is required.")
                            return None

                        subtotal = sum(line["line_total"] for line in sales_receipt_state["products"])
                        service_total = sum(line["line_total"] for line in sales_receipt_state["services"])
                        tax_amount = (subtotal + service_total) * tax_rate / 100.0
                        total = subtotal + service_total + tax_amount

                        matches = self.find_customer_matches(
                            customer["phone"], customer["email"], customer["address"]
                        )

                        return {
                            "receipt_no": field_vars["receipt_no"].get().strip() or self.generate_receipt_no(),
                            "sale_date": sale_date,
                            "channel": "POS",
                            "customer": customer,
                            "products": sales_receipt_state["products"],
                            "services": sales_receipt_state["services"],
                            "tax_rate": tax_rate,
                            "subtotal": subtotal,
                            "service_total": service_total,
                            "tax_amount": tax_amount,
                            "total": total,
                            "pdf_path": sales_receipt_state.get("pdf_path"),
                            "note": field_vars["note"].get().strip() or None,
                            "customer_matches": matches,
                        }

                    def export_pdf_action():
                        payload = build_receipt_payload()
                        if payload is None:
                            return
                        pdf_path = export_receipt_pdf(payload)
                        if pdf_path:
                            sales_receipt_state["pdf_path"] = pdf_path
                            messagebox.showinfo("Success", f"PDF exported to:\n{pdf_path}")

                    def submit_sales_receipt():
                        payload = build_receipt_payload()
                        if payload is None:
                            return

                        try:
                            pending_id = self.submit_pending_entry("SalesReceipt", payload)
                            if payload.get("customer_matches"):
                                conn = sqlite3.connect(FINANCIAL_DB)
                                try:
                                    cursor = conn.cursor()
                                    for item in payload["customer_matches"]:
                                        cursor.execute(
                                            """
                                            INSERT INTO CustomerMatchFlags (
                                                pending_entry_id, submitted_name, submitted_phone, submitted_email,
                                                submitted_address, matched_customer_id, matched_score, status
                                            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDING')
                                            """,
                                            (
                                                pending_id,
                                                payload["customer"]["name"],
                                                payload["customer"]["phone"],
                                                payload["customer"]["email"],
                                                payload["customer"]["address"],
                                                item["id"],
                                                item["score"],
                                            ),
                                        )
                                    conn.commit()
                                finally:
                                    conn.close()

                            self.log_action("SUBMIT_ENTRY", f"Submitted SalesReceipt {payload['receipt_no']} for approval")
                            if payload.get("customer_matches"):
                                messagebox.showinfo(
                                    "Submitted",
                                    f"Sales receipt submitted for approval. {len(payload['customer_matches'])} potential customer matches were flagged.",
                                )
                            else:
                                messagebox.showinfo("Submitted", "Sales receipt submitted for approval.")
                            build_fields("Sales")
                        except Exception as exc:
                            messagebox.showerror("Error", f"Failed to submit sales receipt: {exc}")

                    tk.Button(
                        btn_frame,
                        text="Export to PDF",
                        command=export_pdf_action,
                        bg="#1976d2",
                        fg="white",
                        width=18,
                    ).pack(side="left", padx=4)
                    tk.Button(
                        btn_frame,
                        text="Submit for Sales Approval",
                        command=submit_sales_receipt,
                        bg="#4CAF50",
                        fg="white",
                        width=24,
                    ).pack(side="left", padx=4)

                    recalc_totals()
                    return

                if entry_type == "Costs":
                    fields = [
                        ("Cost Date", "cost_date"),
                        ("Cost Type", "cost_type"),
                        ("Amount", "amount"),
                        ("Note", "note"),
                    ]
                elif entry_type == "Stock":
                    stock_state = {"rows": []}

                    stock_header = tk.Frame(fields_frame, bg="#f5f6f8")
                    stock_header.pack(fill="x", padx=4, pady=(4, 2))
                    for idx, (title, width) in enumerate([
                        ("Date", 13),
                        ("Product SKU", 14),
                        ("Unit Cost (pre-tax)", 16),
                        ("Current Unit Price", 16),
                        ("Unit In", 9),
                        ("Tax Amount", 11),
                        ("Total Unit Cost", 14),
                        ("", 3),
                    ]):
                        tk.Label(
                            stock_header,
                            text=title,
                            width=width,
                            bg="#d9d9d9",
                            anchor="w",
                            font=("Segoe UI", 9, "bold"),
                        ).grid(row=0, column=idx, padx=1, pady=1, sticky="ew")

                    stock_rows_frame = tk.Frame(fields_frame, bg="#f5f6f8")
                    stock_rows_frame.pack(fill="x", padx=4, pady=2)

                    stock_totals_frame = tk.Frame(fields_frame, bg="#f5f6f8")
                    stock_totals_frame.pack(fill="x", padx=4, pady=6)
                    stock_grand_var = tk.StringVar(value="0")
                    stock_grand_tax_var = tk.StringVar(value="0")
                    stock_grand_incl_var = tk.StringVar(value="0")
                    field_vars["stock_tax_rate"] = tk.StringVar(value="8")
                    field_vars["note"] = tk.StringVar()

                    tk.Label(stock_totals_frame, text="Grand Total Unit Cost", bg="#f5f6f8", font=("Segoe UI", 9, "bold")).grid(
                        row=0, column=0, sticky="e", padx=6, pady=4
                    )
                    tk.Label(stock_totals_frame, textvariable=stock_grand_var, bg="#f5f6f8", font=("Segoe UI", 9, "bold")).grid(
                        row=0, column=1, sticky="w", padx=4, pady=4
                    )
                    tk.Label(stock_totals_frame, text="Stock Tax %", bg="#f5f6f8", font=("Segoe UI", 9, "bold")).grid(
                        row=0, column=2, sticky="e", padx=6, pady=4
                    )
                    tax_combo = ttk.Combobox(
                        stock_totals_frame,
                        textvariable=field_vars["stock_tax_rate"],
                        values=("8", "10"),
                        state="readonly",
                        width=8,
                    )
                    tax_combo.grid(row=0, column=3, sticky="w", padx=4, pady=4)
                    tk.Label(
                        stock_totals_frame,
                        text="Applies to Unit Cost (pre-tax)",
                        bg="#f5f6f8",
                        fg="#546e7a",
                        font=("Segoe UI", 8, "italic"),
                    ).grid(row=0, column=4, sticky="w", padx=6, pady=4)
                    tk.Label(stock_totals_frame, text="Grand Tax Amount", bg="#f5f6f8", font=("Segoe UI", 9, "bold")).grid(
                        row=1, column=0, sticky="e", padx=6, pady=4
                    )
                    tk.Label(stock_totals_frame, textvariable=stock_grand_tax_var, bg="#f5f6f8", font=("Segoe UI", 9, "bold")).grid(
                        row=1, column=1, sticky="w", padx=4, pady=4
                    )
                    tk.Label(stock_totals_frame, text="Grand Total (Incl. Tax)", bg="#f5f6f8", font=("Segoe UI", 9, "bold")).grid(
                        row=1, column=2, sticky="e", padx=6, pady=4
                    )
                    tk.Label(stock_totals_frame, textvariable=stock_grand_incl_var, bg="#f5f6f8", font=("Segoe UI", 9, "bold")).grid(
                        row=1, column=3, sticky="w", padx=4, pady=4
                    )
                    tk.Label(stock_totals_frame, text="Note", bg="#f5f6f8").grid(
                        row=2, column=0, sticky="e", padx=6, pady=4
                    )
                    tk.Entry(stock_totals_frame, textvariable=field_vars["note"], width=70).grid(
                        row=2, column=1, columnspan=3, sticky="w", padx=6, pady=4
                    )

                    def recalc_stock_rows():
                        lines = []
                        grand_total = 0.0
                        grand_tax_total = 0.0
                        allowed_tax_rates = {8.0, 10.0}
                        selected_tax_rate = self.parse_float_input(field_vars["stock_tax_rate"].get())
                        if selected_tax_rate not in allowed_tax_rates:
                            selected_tax_rate = 8.0
                            field_vars["stock_tax_rate"].set("8")
                        for row in stock_state["rows"]:
                            row_date = self.parse_date_input(row["date"].get())
                            sku = row["product_sku"].get().strip()
                            unit_cost = self.parse_float_input(row["unit_cost"].get()) or 0.0
                            current_unit_price = self.parse_float_input(row["current_unit_price"].get()) or 0.0
                            unit_in = self.parse_int_input(row["unit_in"].get()) or 0
                            tax_rate = selected_tax_rate
                            pre_tax_total = unit_cost * unit_in
                            tax_amount = round(pre_tax_total * tax_rate / 100.0, 2)
                            total = round(pre_tax_total, 2)
                            row["tax_rate"].set(f"{tax_rate:.2f}")
                            row["tax_amount"].set(f"{tax_amount:,.2f}" if (unit_cost or unit_in) else "")
                            row["total"].set(f"{total:,.2f}" if (unit_cost or unit_in) else "")

                            if row_date or sku or unit_cost or current_unit_price or unit_in:
                                lines.append(
                                    {
                                        "date": row_date,
                                        "product_sku": sku,
                                        "unit_cost": unit_cost,
                                        "current_unit_price": current_unit_price,
                                        "unit_in": unit_in,
                                        "tax_rate": tax_rate,
                                        "tax_amount": tax_amount,
                                        "total": total,
                                    }
                                )
                                grand_total += total
                                grand_tax_total += tax_amount

                        stock_state["lines"] = lines
                        stock_grand_var.set(f"{grand_total:,.2f}")
                        stock_grand_tax_var.set(f"{grand_tax_total:,.2f}")
                        stock_grand_incl_var.set(f"{(grand_total + grand_tax_total):,.2f}")

                    def bind_stock_recalc(var):
                        var.trace_add("write", lambda *args: recalc_stock_rows())

                    def add_stock_row():
                        row_frame = tk.Frame(stock_rows_frame, bg="#f5f6f8")
                        row_frame.pack(fill="x", pady=1)
                        row = {
                            "frame": row_frame,
                            "date": tk.StringVar(value=datetime.now().date().isoformat()),
                            "product_sku": tk.StringVar(),
                            "unit_cost": tk.StringVar(),
                            "current_unit_price": tk.StringVar(),
                            "unit_in": tk.StringVar(value="1"),
                            "tax_rate": tk.StringVar(value="8.00"),
                            "tax_amount": tk.StringVar(),
                            "total": tk.StringVar(),
                        }

                        tk.Entry(row_frame, textvariable=row["date"], width=13).grid(row=0, column=0, padx=1)
                        sku_combo = ttk.Combobox(
                            row_frame,
                            textvariable=row["product_sku"],
                            values=registered_product_skus,
                            state="readonly",
                            width=14,
                        )
                        sku_combo.grid(row=0, column=1, padx=1)
                        self.bind_widget_sku_preview(sku_combo, lambda current=row: current["product_sku"].get())
                        tk.Entry(row_frame, textvariable=row["unit_cost"], width=16).grid(row=0, column=2, padx=1)
                        tk.Entry(row_frame, textvariable=row["current_unit_price"], width=16).grid(row=0, column=3, padx=1)
                        tk.Entry(row_frame, textvariable=row["unit_in"], width=9).grid(row=0, column=4, padx=1)
                        tk.Entry(row_frame, textvariable=row["tax_amount"], width=11, state="readonly").grid(row=0, column=5, padx=1)
                        tk.Entry(row_frame, textvariable=row["total"], width=11, state="readonly").grid(row=0, column=6, padx=1)

                        def remove_row():
                            if row in stock_state["rows"]:
                                stock_state["rows"].remove(row)
                            row_frame.destroy()
                            recalc_stock_rows()

                        tk.Button(row_frame, text="-", width=2, bg="#bdbdbd", command=remove_row).grid(row=0, column=7, padx=1)
                        stock_state["rows"].append(row)
                        for key in ("date", "product_sku", "unit_cost", "current_unit_price", "unit_in"):
                            bind_stock_recalc(row[key])
                        recalc_stock_rows()

                    def submit_stock_entry():
                        recalc_stock_rows()
                        lines = stock_state.get("lines", [])
                        selected_tax_rate = self.parse_float_input(field_vars["stock_tax_rate"].get())
                        if selected_tax_rate not in {8.0, 10.0}:
                            messagebox.showerror("Error", "Stock Tax % must be either 8 or 10.")
                            return
                        if not lines:
                            messagebox.showerror("Error", "Add at least one stock row.")
                            return

                        for idx, line in enumerate(lines, start=1):
                            if not line.get("date"):
                                messagebox.showerror("Error", f"Row {idx}: invalid date. Use YYYY-MM-DD format.")
                                return
                            sku = line.get("product_sku")
                            if not sku:
                                messagebox.showerror("Error", f"Row {idx}: Product SKU is required.")
                                return
                            if not self.product_exists(sku):
                                messagebox.showerror("Error", f"Row {idx}: Product SKU '{sku}' does not exist.")
                                return
                            if (line.get("unit_cost") or 0) <= 0:
                                messagebox.showerror("Error", f"Row {idx}: Unit Cost must be greater than 0.")
                                return
                            if (line.get("current_unit_price") or 0) <= 0:
                                messagebox.showerror("Error", f"Row {idx}: Current Unit Price must be greater than 0.")
                                return
                            if (line.get("unit_in") or 0) <= 0:
                                messagebox.showerror("Error", f"Row {idx}: Unit In must be greater than 0.")
                                return

                        payload = {
                            "date": lines[0]["date"],
                            "note": field_vars["note"].get().strip() or None,
                            "lines": lines,
                            "tax_rate": selected_tax_rate,
                        }

                        try:
                            self.submit_pending_entry("Stock", payload)
                            self.log_action("SUBMIT_ENTRY", f"Submitted Stock entry with {len(lines)} row(s) for approval")
                            messagebox.showinfo("Success", "Stock entry submitted for approval.")
                            build_fields("Stock")
                        except Exception as e:
                            messagebox.showerror("Error", f"Failed to submit Stock entry: {e}")

                    tk.Button(
                        btn_frame,
                        text="+",
                        bg="#9e9e9e",
                        fg="white",
                        width=3,
                        command=add_stock_row,
                    ).pack(side="left", padx=4)
                    tk.Button(
                        btn_frame,
                        text="Submit for Approval",
                        command=submit_stock_entry,
                        bg="#4CAF50",
                        fg="white",
                        width=20,
                    ).pack(side="left", padx=4)

                    add_stock_row()
                    return
                else:
                    fields = [
                        ("Event Date", "event_date"),
                        ("Event Name", "event_name"),
                        ("Cash In", "cash_in"),
                        ("Cash Out", "cash_out"),
                        ("Balance", "balance"),
                        ("Note", "note"),
                    ]

                for idx, (label, key) in enumerate(fields):
                    tk.Label(fields_frame, text=f"{label}:", bg="#f5f6f8").grid(
                        row=idx // 2, column=(idx % 2) * 2, sticky="e", padx=6, pady=4
                    )
                    var = tk.StringVar()
                    width = 20 if key != "note" else 44
                    tk.Entry(fields_frame, textvariable=var, width=width).grid(
                        row=idx // 2, column=(idx % 2) * 2 + 1, sticky="w", padx=6, pady=4
                    )
                    field_vars[key] = var

                today_str = datetime.now().date().isoformat()
                for key in ("sale_date", "cost_date", "date", "event_date"):
                    if key in field_vars and not field_vars[key].get():
                        field_vars[key].set(today_str)

                tk.Button(
                    btn_frame,
                    text="Smart Calculate",
                    command=lambda: smart_calculate(entry_type_var.get()),
                    bg="#607D8B",
                    fg="white",
                    width=18,
                ).pack(side="left", padx=4)
                tk.Button(
                    btn_frame,
                    text="Submit for Approval",
                    command=submit_entry,
                    bg="#4CAF50",
                    fg="white",
                    width=20,
                ).pack(side="left", padx=4)

            def smart_calculate(entry_type):
                if entry_type == "Sales":
                    units = self.parse_int_input(field_vars.get("units_sold", tk.StringVar()).get())
                    unit_price = self.parse_float_input(field_vars.get("unit_price", tk.StringVar()).get())
                    gross_sales = self.parse_float_input(field_vars.get("gross_sales", tk.StringVar()).get())
                    if gross_sales is None and units is not None and unit_price is not None:
                        field_vars["gross_sales"].set(f"{units * unit_price:.2f}")
                    elif unit_price is None and units is not None and gross_sales is not None and units != 0:
                        field_vars["unit_price"].set(f"{gross_sales / units:.2f}")
                elif entry_type == "Stock":
                    unit_cost = self.parse_float_input(field_vars.get("unit_cost", tk.StringVar()).get())
                    unit_in = self.parse_int_input(field_vars.get("unit_in", tk.StringVar()).get())
                    total = self.parse_float_input(field_vars.get("total", tk.StringVar()).get())
                    if total is None and unit_cost is not None and unit_in is not None:
                        field_vars["total"].set(f"{unit_cost * unit_in:.2f}")
                elif entry_type == "Timeline":
                    cash_in = self.parse_float_input(field_vars.get("cash_in", tk.StringVar()).get()) or 0
                    cash_out = self.parse_float_input(field_vars.get("cash_out", tk.StringVar()).get()) or 0
                    balance = self.parse_float_input(field_vars.get("balance", tk.StringVar()).get())
                    if balance is None:
                        field_vars["balance"].set(f"{cash_in - cash_out:.2f}")

            def submit_entry():
                entry_type = entry_type_var.get()
                smart_calculate(entry_type)

                payload = {key: var.get().strip() for key, var in field_vars.items()}
                date_key = {
                    "Sales": "sale_date",
                    "Costs": "cost_date",
                    "Stock": "date",
                    "Timeline": "event_date",
                }[entry_type]
                parsed_date = self.parse_date_input(payload.get(date_key))
                if not parsed_date:
                    messagebox.showerror("Error", "Invalid date. Use YYYY-MM-DD format.")
                    return
                payload[date_key] = parsed_date

                if entry_type == "Sales" and not payload.get("product_sku"):
                    messagebox.showerror("Error", "Product SKU is required for Sales entries.")
                    return
                if entry_type == "Stock" and not payload.get("product_sku"):
                    messagebox.showerror("Error", "Product SKU is required for Stock entries.")
                    return
                if entry_type in {"Sales", "Stock"} and not self.product_exists(payload.get("product_sku")):
                    messagebox.showerror("Error", f"Product SKU '{payload.get('product_sku')}' does not exist.")
                    return

                try:
                    self.submit_pending_entry(entry_type, payload)
                    self.log_action("SUBMIT_ENTRY", f"Submitted {entry_type} entry for approval")
                    messagebox.showinfo("Success", "Entry submitted for approval.")
                    build_fields(entry_type)
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to submit entry: {e}")

            entry_type_combo.bind("<<ComboboxSelected>>", lambda event=None: build_fields(entry_type_var.get()))
            build_fields(entry_type_var.get())

        def build_layout():
            for widget in frame.winfo_children():
                widget.destroy()

            is_dark = self.pos_ui_state["theme"] == "dark"
            high_contrast = self.pos_ui_state["high_contrast"]

            if is_dark:
                colors = {
                    "bg": "#1f242a",
                    "surface": "#2b323a",
                    "card": "#303841",
                    "header": "#222831",
                    "sidebar": "#1f272e",
                    "accent": "#4db6ac",
                    "danger": "#ef5350",
                    "text": "#f4f6f8",
                    "muted": "#b0bec5",
                }
            else:
                colors = {
                    "bg": "#f5f6f8",
                    "surface": "#ffffff",
                    "card": "#ffffff",
                    "header": "#ffffff",
                    "sidebar": "#263238",
                    "accent": "#2e7d32",
                    "danger": "#d32f2f",
                    "text": "#1c1e21",
                    "muted": "#546E7A",
                }

            if high_contrast:
                colors.update({
                    "bg": "#000000" if is_dark else "#ffffff",
                    "surface": "#000000" if is_dark else "#ffffff",
                    "card": "#000000" if is_dark else "#ffffff",
                    "header": "#000000" if is_dark else "#ffffff",
                    "sidebar": "#000000" if is_dark else "#111111",
                    "accent": "#00c853",
                    "danger": "#ff5252",
                    "text": "#ffffff" if is_dark else "#000000",
                    "muted": "#ffffff" if is_dark else "#000000",
                })

            frame.configure(bg=colors["bg"])

            header = tk.Frame(frame, bg=colors["header"], height=52)
            header.pack(fill="x")
            header.pack_propagate(False)

            tk.Label(
                header,
                text="Point of Sales",
                font=("Segoe UI", 14, "bold"),
                bg=colors["header"],
                fg=colors["text"],
            ).pack(side="left", padx=16)

            search_var = tk.StringVar(value=self.pos_ui_state.get("search", ""))
            search_entry = tk.Entry(
                header,
                textvariable=search_var,
                width=32,
                bg=colors["surface"],
                fg=colors["text"],
            )
            search_entry.pack(side="left", padx=8, pady=8)

            clock_var = tk.StringVar(value=datetime.now().strftime("%H:%M"))
            clock_label = tk.Label(
                header,
                textvariable=clock_var,
                bg=colors["header"],
                fg=colors["muted"],
                font=("Segoe UI", 10, "bold"),
            )
            clock_label.pack(side="right", padx=12)

            def tick_clock():
                clock_var.set(datetime.now().strftime("%H:%M"))
                clock_label.after(1000, tick_clock)

            tick_clock()

            tk.Button(
                header,
                text="Alerts",
                bg=colors["surface"],
                fg=colors["text"],
                width=8,
            ).pack(side="right", padx=6, pady=8)

            tk.Button(
                header,
                text="Profile",
                bg=colors["surface"],
                fg=colors["text"],
                width=8,
            ).pack(side="right", padx=6, pady=8)

            theme_frame = tk.Frame(header, bg=colors["header"])
            theme_frame.pack(side="right", padx=10)
            theme_var = tk.BooleanVar(value=is_dark)
            contrast_var = tk.BooleanVar(value=high_contrast)

            def toggle_theme():
                self.pos_ui_state["theme"] = "dark" if theme_var.get() else "light"
                build_layout()

            def toggle_contrast():
                self.pos_ui_state["high_contrast"] = contrast_var.get()
                build_layout()

            tk.Checkbutton(
                theme_frame,
                text="Dark",
                variable=theme_var,
                command=toggle_theme,
                bg=colors["header"],
                fg=colors["text"],
                activebackground=colors["header"],
                activeforeground=colors["text"],
                selectcolor=colors["header"],
            ).pack(side="left", padx=6)

            tk.Checkbutton(
                theme_frame,
                text="Contrast",
                variable=contrast_var,
                command=toggle_contrast,
                bg=colors["header"],
                fg=colors["text"],
                activebackground=colors["header"],
                activeforeground=colors["text"],
                selectcolor=colors["header"],
            ).pack(side="left", padx=6)

            body = tk.Frame(frame, bg=colors["bg"])
            body.pack(fill="both", expand=True)

            sidebar = tk.Frame(body, bg=colors["sidebar"], width=190)
            sidebar.pack(side="left", fill="y")
            sidebar.pack_propagate(False)

            tk.Label(
                sidebar,
                text="NAVIGATION",
                bg=colors["sidebar"],
                fg="#cfd8dc",
                font=("Segoe UI", 9, "bold"),
            ).pack(pady=(14, 6))

            nav_items = ["Dashboard", "Entry", "Customers", "Reports", "Settings"]
            current_nav = self.pos_ui_state.get("nav_view", "Dashboard")

            def on_nav_click(name):
                self.pos_ui_state["nav_view"] = name
                build_layout()

            for item in nav_items:
                tk.Button(
                    sidebar,
                    text=item,
                    bg=colors["accent"] if item == current_nav else "#37474F",
                    fg="white",
                    relief="flat",
                    height=1,
                    width=20,
                    command=lambda name=item: on_nav_click(name),
                ).pack(pady=4, padx=10)

            tk.Label(
                sidebar,
                text="QUICK ACTIONS",
                bg=colors["sidebar"],
                fg="#cfd8dc",
                font=("Segoe UI", 9, "bold"),
            ).pack(pady=(16, 6))

            action_frame = tk.Frame(sidebar, bg=colors["sidebar"])
            action_frame.pack(pady=4)

            def reset_sale():
                self.pos_ui_state["cart"].clear()
                update_cart()

            tk.Button(
                action_frame,
                text="New Sale",
                bg=colors["accent"],
                fg="white",
                width=18,
                command=reset_sale,
            ).pack(pady=4)

            def confirm_void():
                if messagebox.askyesno("Confirm", "Void current cart?"):
                    reset_sale()

            tk.Button(
                action_frame,
                text="Refund",
                bg="#546E7A",
                fg="white",
                width=18,
            ).pack(pady=4)
            tk.Button(
                action_frame,
                text="Void",
                bg=colors["danger"],
                fg="white",
                width=18,
                command=confirm_void,
            ).pack(pady=4)

            tk.Label(
                sidebar,
                text="CATEGORIES",
                bg=colors["sidebar"],
                fg="#cfd8dc",
                font=("Segoe UI", 9, "bold"),
            ).pack(pady=(16, 6))

            category_var = tk.StringVar(value=self.pos_ui_state.get("category", "All"))
            category_list = tk.Listbox(
                sidebar,
                height=8,
                exportselection=False,
                bg="#37474F",
                fg="white",
                selectbackground=colors["accent"],
                selectforeground="white",
            )
            category_list.pack(fill="x", padx=10, pady=6)

            products = load_products()
            categories = sorted({p["category"] for p in products})
            category_list.insert("end", "All")
            for category in categories:
                category_list.insert("end", category)

            if self.pos_ui_state.get("category") in categories:
                category_list.selection_set(categories.index(self.pos_ui_state["category"]) + 1)
            else:
                category_list.selection_set(0)

            center = tk.Frame(body, bg=colors["bg"])
            center.pack(side="left", fill="both", expand=True)

            center_header = tk.Frame(center, bg=colors["bg"])
            center_header.pack(fill="x", padx=16, pady=8)
            center_title = "Products"
            center_subtitle = "Tap to add, hold to review"
            if current_nav == "Entry":
                center_title = "Entry Form"
                center_subtitle = "Sales, Costs, Stock, Timeline"
            elif current_nav == "Reports":
                center_title = "Reports"
                center_subtitle = "Sales & Inventory reporting workspace"

            tk.Label(
                center_header,
                text=center_title,
                font=("Segoe UI", 12, "bold"),
                bg=colors["bg"],
                fg=colors["text"],
            ).pack(side="left")
            tk.Label(
                center_header,
                text=center_subtitle,
                font=("Segoe UI", 9),
                bg=colors["bg"],
                fg=colors["muted"],
            ).pack(side="left", padx=10)

            if current_nav == "Entry":
                inline_panel = tk.Frame(center, bg="#f5f6f8", bd=1, relief="solid")
                inline_panel.pack(fill="x", padx=16, pady=(0, 8))
                render_inline_entry_panel(inline_panel)

            if current_nav == "Settings":
                settings_panel = tk.Frame(center, bg=colors["surface"], bd=1, relief="solid")
                settings_panel.pack(fill="x", padx=16, pady=(0, 8))
                tk.Label(
                    settings_panel,
                    text="Settings",
                    font=("Segoe UI", 11, "bold"),
                    bg=colors["surface"],
                    fg=colors["text"],
                ).pack(anchor="w", padx=10, pady=(8, 4))
                tk.Button(
                    settings_panel,
                    text="Stock Adjust",
                    command=open_stock_adjustment_dialog,
                    bg=colors["accent"],
                    fg="white",
                    width=18,
                ).pack(anchor="w", padx=10, pady=(0, 10))
                tk.Button(
                    settings_panel,
                    text="Product Management",
                    command=self.open_product_management_popup,
                    bg=colors["accent"],
                    fg="white",
                    width=18,
                ).pack(anchor="w", padx=10, pady=(0, 10))

            if current_nav == "Reports":
                reports_panel = tk.Frame(center, bg=colors["surface"], bd=1, relief="solid")
                reports_panel.pack(fill="both", expand=True, padx=16, pady=(0, 12))

                reports_notebook = ttk.Notebook(reports_panel, style="App.TNotebook")
                reports_notebook.pack(fill="both", expand=True, padx=4, pady=4)

                sales_tab = tk.Frame(reports_notebook, bg=colors["surface"])
                reports_notebook.add(sales_tab, text="Sales")
                tk.Label(
                    sales_tab,
                    text="Sales records are display-only in Financial Data. Submit sales edits from this POS Reports workspace.",
                    bg=colors["surface"],
                    fg=colors["muted"],
                    font=("Segoe UI", 9, "italic"),
                ).pack(anchor="w", padx=10, pady=(10, 0))
                self.build_sales_reports_workspace(sales_tab, palette=colors)

                inventory_tab = tk.Frame(reports_notebook, bg=colors["surface"])
                reports_notebook.add(inventory_tab, text="Inventory")
                tk.Label(
                    inventory_tab,
                    text="Inventory history by period. Net Change = Units In - Units Sold for that period. Click a period to drill down into stock transactions.",
                    bg=colors["surface"],
                    fg=colors["muted"],
                    font=("Segoe UI", 9, "italic"),
                ).pack(anchor="w", padx=10, pady=(10, 0))
                self.build_stock_reports_workspace(inventory_tab, palette=colors, enable_edit=True)

                costs_tab = tk.Frame(reports_notebook, bg=colors["surface"])
                reports_notebook.add(costs_tab, text="Costs")
                tk.Label(
                    costs_tab,
                    text="Cost history by period. Click a period to drill down into individual cost records.",
                    bg=colors["surface"],
                    fg=colors["muted"],
                    font=("Segoe UI", 9, "italic"),
                ).pack(anchor="w", padx=10, pady=(10, 0))
                self.build_cost_reports_workspace(costs_tab, palette=colors, enable_edit=True)
                return

            product_canvas = tk.Canvas(center, bg=colors["bg"], highlightthickness=0)
            product_canvas.pack(side="left", fill="both", expand=True, padx=(16, 0), pady=(0, 12))
            product_scroll = ttk.Scrollbar(center, orient="vertical", command=product_canvas.yview)
            product_scroll.pack(side="left", fill="y", pady=(0, 12))
            product_canvas.configure(yscrollcommand=product_scroll.set)

            product_frame = tk.Frame(product_canvas, bg=colors["bg"])
            product_canvas.create_window((0, 0), window=product_frame, anchor="nw")

            for col in range(3):
                product_frame.grid_columnconfigure(col, weight=1)

            def filter_products():
                query = search_var.get().strip().lower()
                selected = category_var.get()
                filtered = []
                for prod in products:
                    if selected != "All" and prod["category"] != selected:
                        continue
                    haystack = f"{prod['name']} {prod['sku']} {prod['category']}".lower()
                    if query and query not in haystack:
                        continue
                    filtered.append(prod)
                return filtered

            def add_to_cart(product):
                refresh_inventory_snapshot()
                cart = self.pos_ui_state["cart"]
                current_qty = cart.get(product["sku"], {}).get("qty", 0)
                available = available_units_for_sku(product["sku"])
                next_qty = current_qty + 1
                projected = available - next_qty
                alert = stock_alert_text(product["sku"], projected)
                if alert:
                    messagebox.showwarning("Inventory Warning", f"Cart update warning: {alert}.")
                item = cart.get(product["sku"])
                if item:
                    item["qty"] += 1
                else:
                    cart[product["sku"]] = {
                        "sku": product["sku"],
                        "name": product["name"],
                        "unit_price": product["unit_price"],
                        "image_path": product.get("image_path"),
                        "qty": 1,
                    }
                update_cart()

            def render_products():
                refresh_inventory_snapshot()
                for child in product_frame.winfo_children():
                    child.destroy()
                items = filter_products()
                if not items:
                    tk.Label(
                        product_frame,
                        text="No products match your search.",
                        bg=colors["bg"],
                        fg=colors["muted"],
                        font=("Segoe UI", 10, "italic"),
                    ).grid(row=0, column=0, padx=20, pady=20, sticky="w")
                for idx, prod in enumerate(items):
                    available = available_units_for_sku(prod["sku"])
                    alert_level = self.stock_alert_level(available)
                    card = tk.Frame(product_frame, bg=colors["card"], bd=1, relief="solid")
                    card.grid(row=idx // 3, column=idx % 3, padx=8, pady=8, sticky="nsew")
                    tk.Label(
                        card,
                        text=prod["name"],
                        bg=colors["card"],
                        fg=colors["text"],
                        font=("Segoe UI", 10, "bold"),
                        wraplength=150,
                        justify="left",
                    ).pack(anchor="w", padx=10, pady=(8, 2))
                    image_preview = self.get_product_preview_image(prod["sku"], (108, 108), image_path=prod.get("image_path"))
                    image_label = tk.Label(
                        card,
                        image=image_preview,
                        bg=colors["card"],
                    )
                    image_label.image = image_preview
                    image_label.pack(anchor="w", padx=10, pady=(0, 4))

                    sku_label = tk.Label(
                        card,
                        text=f"SKU {prod['sku']}",
                        bg=colors["card"],
                        fg=colors["muted"],
                        font=("Segoe UI", 8),
                    )
                    sku_label.pack(anchor="w", padx=10)
                    sku_label.bind(
                        "<Enter>",
                        lambda event, sku=prod["sku"], path=prod.get("image_path"): self.show_sku_preview(
                            sku, event.x_root, event.y_root, image_path=path
                        ),
                    )
                    sku_label.bind("<Motion>", lambda event, sku=prod["sku"], path=prod.get("image_path"): self.show_sku_preview(
                        sku, event.x_root, event.y_root, image_path=path
                    ))
                    sku_label.bind("<Leave>", lambda event: self.schedule_sku_preview_hide())
                    tk.Label(
                        card,
                        text=f"Available: {available}",
                        bg=colors["card"],
                        fg=colors["danger"] if alert_level in {"critical", "low"} else colors["muted"],
                        font=("Segoe UI", 8),
                    ).pack(anchor="w", padx=10)
                    tk.Label(
                        card,
                        text=f"${self.format_cell(prod['unit_price'], 'money')}",
                        bg=colors["card"],
                        fg=colors["accent"],
                        font=("Segoe UI", 10, "bold"),
                    ).pack(anchor="w", padx=10, pady=(2, 8))
                    tk.Button(
                        card,
                        text="Add",
                        command=lambda p=prod: add_to_cart(p),
                        bg=colors["accent"],
                        fg="white",
                        width=10,
                    ).pack(padx=10, pady=(0, 10))

            def on_products_configure(event):
                product_canvas.configure(scrollregion=product_canvas.bbox("all"))

            product_frame.bind("<Configure>", on_products_configure)

            right = tk.Frame(body, bg=colors["surface"], width=260)
            right.pack(side="right", fill="y")
            right.pack_propagate(False)

            tk.Label(
                right,
                text="Cart Summary",
                font=("Segoe UI", 12, "bold"),
                bg=colors["surface"],
                fg=colors["text"],
            ).pack(pady=(12, 6))

            cart_frame = tk.Frame(right, bg=colors["surface"])
            cart_frame.pack(fill="both", expand=True, padx=12)

            cart_tree = ttk.Treeview(
                cart_frame,
                columns=("SKU", "Qty", "Unit", "Line"),
                show="headings",
                height=6,
            )
            for col, width in ("SKU", 60), ("Qty", 40), ("Unit", 60), ("Line", 70):
                cart_tree.heading(col, text=col)
                cart_tree.column(col, width=width, anchor="center")
            cart_tree.pack(fill="both", expand=True)

            def on_cart_hover(event):
                row_id = cart_tree.identify_row(event.y)
                col_id = cart_tree.identify_column(event.x)
                if not row_id or col_id != "#1":
                    self.schedule_sku_preview_hide()
                    return
                values = cart_tree.item(row_id).get("values", [])
                if not values:
                    self.schedule_sku_preview_hide()
                    return
                sku = str(values[0]).strip()
                cart_item = self.pos_ui_state["cart"].get(sku, {})
                self.show_sku_preview(sku, event.x_root, event.y_root, image_path=cart_item.get("image_path"))

            cart_tree.bind("<Motion>", on_cart_hover)
            cart_tree.bind("<Leave>", lambda event: self.schedule_sku_preview_hide())

            adjust_frame = tk.Frame(right, bg=colors["surface"])
            adjust_frame.pack(fill="x", padx=12, pady=6)

            def cart_selected():
                selection = cart_tree.selection()
                if not selection:
                    return None
                return cart_tree.item(selection[0])["values"][0]

            def adjust_qty(delta):
                sku = cart_selected()
                if not sku:
                    return
                item = self.pos_ui_state["cart"].get(sku)
                if not item:
                    return
                refresh_inventory_snapshot()
                available = available_units_for_sku(sku)
                next_qty = item["qty"] + delta
                projected = available - next_qty
                alert = stock_alert_text(sku, projected)
                if delta > 0 and alert:
                    messagebox.showwarning("Inventory Warning", f"Cart update warning: {alert}.")
                item["qty"] += delta
                if item["qty"] <= 0:
                    del self.pos_ui_state["cart"][sku]
                update_cart()

            tk.Button(
                adjust_frame,
                text="-",
                command=lambda: adjust_qty(-1),
                bg=colors["danger"],
                fg="white",
                width=4,
            ).pack(side="left", padx=4)
            tk.Button(
                adjust_frame,
                text="+",
                command=lambda: adjust_qty(1),
                bg=colors["accent"],
                fg="white",
                width=4,
            ).pack(side="left", padx=4)
            tk.Button(
                adjust_frame,
                text="Remove",
                command=lambda: adjust_qty(-999),
                bg="#546E7A",
                fg="white",
                width=8,
            ).pack(side="left", padx=6)

            details_frame = tk.Frame(right, bg=colors["surface"])
            details_frame.pack(fill="x", padx=12, pady=6)

            tk.Label(details_frame, text="Order ID", bg=colors["surface"], fg=colors["text"]).grid(
                row=0, column=0, sticky="w", pady=2
            )
            order_id_var = tk.StringVar()
            tk.Entry(details_frame, textvariable=order_id_var, width=18).grid(
                row=0, column=1, sticky="e", pady=2
            )

            tk.Label(details_frame, text="Channel", bg=colors["surface"], fg=colors["text"]).grid(
                row=1, column=0, sticky="w", pady=2
            )
            channel_var = tk.StringVar(value="POS")
            tk.Entry(details_frame, textvariable=channel_var, width=18).grid(
                row=1, column=1, sticky="e", pady=2
            )

            tk.Label(details_frame, text="Sale Date", bg=colors["surface"], fg=colors["text"]).grid(
                row=2, column=0, sticky="w", pady=2
            )
            sale_date_var = tk.StringVar(value=datetime.now().date().isoformat())
            tk.Entry(details_frame, textvariable=sale_date_var, width=18).grid(
                row=2, column=1, sticky="e", pady=2
            )

            tk.Label(details_frame, text="Promo", bg=colors["surface"], fg=colors["text"]).grid(
                row=3, column=0, sticky="w", pady=2
            )
            promo_var = tk.StringVar()
            tk.Entry(details_frame, textvariable=promo_var, width=18).grid(
                row=3, column=1, sticky="e", pady=2
            )

            tk.Label(details_frame, text="Tax %", bg=colors["surface"], fg=colors["text"]).grid(
                row=4, column=0, sticky="w", pady=2
            )
            tax_var = tk.StringVar(value="0")
            tk.Entry(details_frame, textvariable=tax_var, width=6).grid(
                row=4, column=1, sticky="e", pady=2
            )

            tk.Label(details_frame, text="Service Fee", bg=colors["surface"], fg=colors["text"]).grid(
                row=5, column=0, sticky="w", pady=2
            )
            service_var = tk.StringVar(value="0")
            tk.Entry(details_frame, textvariable=service_var, width=18).grid(
                row=5, column=1, sticky="e", pady=2
            )

            tk.Label(details_frame, text="Shipping", bg=colors["surface"], fg=colors["text"]).grid(
                row=6, column=0, sticky="w", pady=2
            )
            shipping_var = tk.StringVar(value="0")
            tk.Entry(details_frame, textvariable=shipping_var, width=18).grid(
                row=6, column=1, sticky="e", pady=2
            )

            tk.Label(details_frame, text="Note", bg=colors["surface"], fg=colors["text"]).grid(
                row=7, column=0, sticky="w", pady=2
            )
            note_var = tk.StringVar()
            tk.Entry(details_frame, textvariable=note_var, width=18).grid(
                row=7, column=1, sticky="e", pady=2
            )

            totals_frame = tk.Frame(right, bg=colors["surface"])
            totals_frame.pack(fill="x", padx=12, pady=6)

            subtotal_var = tk.StringVar(value="$0.00")
            discount_var = tk.StringVar(value="$0.00")
            tax_amount_var = tk.StringVar(value="$0.00")
            fee_var = tk.StringVar(value="$0.00")
            total_var = tk.StringVar(value="$0.00")
            stock_alert_var = tk.StringVar(value="")

            def totals_row(label, var, row, bold=False):
                tk.Label(
                    totals_frame,
                    text=label,
                    bg=colors["surface"],
                    fg=colors["muted"],
                    font=("Segoe UI", 9, "bold" if bold else "normal"),
                ).grid(row=row, column=0, sticky="w", pady=2)
                tk.Label(
                    totals_frame,
                    textvariable=var,
                    bg=colors["surface"],
                    fg=colors["text"],
                    font=("Segoe UI", 9, "bold" if bold else "normal"),
                ).grid(row=row, column=1, sticky="e", pady=2)

            totals_row("Subtotal", subtotal_var, 0)
            totals_row("Discount", discount_var, 1)
            totals_row("Tax", tax_amount_var, 2)
            totals_row("Fees", fee_var, 3)
            totals_row("Total", total_var, 4, bold=True)
            tk.Label(
                totals_frame,
                textvariable=stock_alert_var,
                bg=colors["surface"],
                fg=colors["danger"],
                font=("Segoe UI", 8, "bold"),
                wraplength=220,
                justify="left",
            ).grid(row=5, column=0, columnspan=2, sticky="w", pady=(4, 0))

            payment_frame = tk.Frame(right, bg=colors["surface"])
            payment_frame.pack(fill="x", padx=12, pady=6)

            tk.Label(
                payment_frame,
                text="Payment",
                bg=colors["surface"],
                fg=colors["text"],
                font=("Segoe UI", 10, "bold"),
            ).pack(anchor="w")

            payment_var = tk.StringVar(value="Cash")
            for option in ("Cash", "Card", "QR", "Split"):
                tk.Radiobutton(
                    payment_frame,
                    text=option,
                    variable=payment_var,
                    value=option,
                    bg=colors["surface"],
                    fg=colors["text"],
                    selectcolor=colors["surface"],
                ).pack(anchor="w")

            footer = tk.Frame(right, bg=colors["surface"])
            footer.pack(fill="x", padx=12, pady=10)

            def parse_promo(value, subtotal):
                text = value.strip()
                if not text:
                    return 0.0
                if text.endswith("%"):
                    pct = self.parse_float_input(text[:-1]) or 0
                    return subtotal * pct / 100.0
                amount = self.parse_float_input(text)
                return amount or 0.0

            def update_cart():
                for item in cart_tree.get_children():
                    cart_tree.delete(item)
                subtotal = 0.0
                stock_issues = []
                for item in self.pos_ui_state["cart"].values():
                    available = available_units_for_sku(item["sku"])
                    projected = available - item["qty"]
                    alert = stock_alert_text(item["sku"], projected)
                    if alert:
                        stock_issues.append(alert)
                    line_total = item["qty"] * item["unit_price"]
                    subtotal += line_total
                    cart_tree.insert(
                        "",
                        "end",
                        values=(
                            item["sku"],
                            item["qty"],
                            f"{item['unit_price']:.2f}",
                            f"{line_total:.2f}",
                        ),
                    )
                discount_amount = parse_promo(promo_var.get(), subtotal)
                tax_rate = self.parse_float_input(tax_var.get()) or 0.0
                service_fee = self.parse_float_input(service_var.get()) or 0.0
                shipping_fee = self.parse_float_input(shipping_var.get()) or 0.0
                tax_amount = max(subtotal - discount_amount, 0) * tax_rate / 100.0
                fee_total = service_fee + shipping_fee
                total = subtotal - discount_amount + tax_amount + fee_total

                subtotal_var.set(f"${subtotal:.2f}")
                discount_var.set(f"-${discount_amount:.2f}")
                tax_amount_var.set(f"${tax_amount:.2f}")
                fee_var.set(f"${fee_total:.2f}")
                total_var.set(f"${total:.2f}")
                if stock_issues:
                    stock_alert_var.set("Stock warning: " + "; ".join(stock_issues))
                else:
                    stock_alert_var.set("")

            def apply_sale():
                if not self.pos_ui_state["cart"]:
                    messagebox.showwarning("Empty Cart", "Add items before checkout.")
                    return

                stock_issues = validate_cart_stock_levels()
                if stock_issues:
                    issue_text = "; ".join([item[3] for item in stock_issues])
                    if not messagebox.askyesno(
                        "Inventory Warning",
                        f"Proceed with checkout despite inventory warning?\n{issue_text}",
                    ):
                        update_cart()
                        return

                sale_date = self.parse_date_input(sale_date_var.get())
                if not sale_date:
                    messagebox.showerror("Error", "Invalid sale date. Use YYYY-MM-DD format.")
                    return
                order_id = order_id_var.get().strip() or self.generate_receipt_no()
                channel = channel_var.get().strip() or "POS"
                service_fee = self.parse_float_input(service_var.get()) or 0.0
                shipping_fee = self.parse_float_input(shipping_var.get()) or 0.0
                note = note_var.get().strip() or None
                payment_method = payment_var.get().strip() or "Cash"

                subtotal = 0.0
                for item in self.pos_ui_state["cart"].values():
                    subtotal += item["qty"] * item["unit_price"]

                discount_amount = parse_promo(promo_var.get(), subtotal)
                tax_rate = self.parse_float_input(tax_var.get()) or 0.0
                tax_amount = max(subtotal - discount_amount, 0) * tax_rate / 100.0
                total = subtotal - discount_amount + tax_amount + service_fee + shipping_fee

                if total < 0:
                    messagebox.showerror("Error", "Total cannot be negative.")
                    return

                conn = None
                try:
                    conn = sqlite3.connect(FINANCIAL_DB)
                    cursor = conn.cursor()
                    batch_lines = []
                    for item in self.pos_ui_state["cart"].values():
                        if not self.product_exists(item["sku"], cursor):
                            raise ValueError(f"Product SKU '{item['sku']}' no longer exists.")
                        if item["qty"] is None or item["qty"] <= 0:
                            raise ValueError(f"Invalid quantity for SKU '{item['sku']}'.")
                        line_total = item["qty"] * item["unit_price"]
                        if subtotal > 0:
                            line_ratio = line_total / subtotal
                        else:
                            line_ratio = 0
                        line_discount = discount_amount * line_ratio
                        line_tax = tax_amount * line_ratio
                        gross_sales = line_total - line_discount + line_tax

                        line_note_parts = []
                        if note:
                            line_note_parts.append(note)
                        line_note_parts.append(f"payment={payment_method}")
                        if discount_amount:
                            line_note_parts.append(f"discount={line_discount:.2f}")
                        if tax_rate:
                            line_note_parts.append(f"tax_rate={tax_rate:.2f}")
                            line_note_parts.append(f"tax_amount={line_tax:.2f}")
                        line_note = "; ".join(line_note_parts)

                        batch_lines.append(
                            {
                                "product_sku": item["sku"],
                                "units_sold": item["qty"],
                                "unit_price": item["unit_price"],
                                "gross_sales": gross_sales,
                                "service_fee": service_fee * line_ratio,
                                "shipping_fee": shipping_fee * line_ratio,
                                "line_note": line_note or None,
                            }
                        )
                    conn.close()

                    pending_id = self.submit_pending_entry(
                        "SalesBatch",
                        {
                            "sale_date": sale_date,
                            "order_id": order_id,
                            "channel": channel,
                            "payment_method": payment_method,
                            "subtotal": subtotal,
                            "discount_amount": discount_amount,
                            "tax_rate": tax_rate,
                            "tax_amount": tax_amount,
                            "service_fee": service_fee,
                            "shipping_fee": shipping_fee,
                            "total": total,
                            "note": note,
                            "lines": batch_lines,
                        },
                    )

                    self.log_action(
                        "SUBMIT_ENTRY",
                        f"Submitted POS checkout order {order_id} for approval as SalesBatch #{pending_id} ({len(batch_lines)} line items)",
                    )
                    messagebox.showinfo(
                        "Submitted",
                        f"POS checkout submitted for approval.\nOrder ID: {order_id}\nPending entry ID: {pending_id}\nLine items: {len(batch_lines)}",
                    )
                    reset_sale()
                    refresh_inventory_snapshot()
                    render_products()
                except Exception as e:
                    if conn is not None:
                        conn.close()
                    self.log_action("POS_SALE_FAILED", f"error={e}")
                    messagebox.showerror("Error", f"Failed to complete sale: {e}")

            tk.Button(
                footer,
                text="Submit for Approval",
                bg=colors["accent"],
                fg="white",
                width=20,
                height=2,
                command=apply_sale,
            ).pack()

            status_frame = tk.Frame(frame, bg=colors["bg"])
            status_frame.pack(fill="x")
            tk.Label(
                status_frame,
                text="Status: Connected   Last sync: just now",
                bg=colors["bg"],
                fg=colors["muted"],
                font=("Segoe UI", 8),
            ).pack(side="left", padx=16, pady=4)
            tk.Button(
                status_frame,
                text="?",
                bg=colors["bg"],
                fg=colors["muted"],
                width=2,
            ).pack(side="right", padx=16, pady=4)

            def on_category_select(event=None):
                selection = category_list.curselection()
                if not selection:
                    return
                self.pos_ui_state["category"] = category_list.get(selection[0])
                category_var.set(self.pos_ui_state["category"])
                render_products()

            def on_search_change(event=None):
                self.pos_ui_state["search"] = search_var.get()
                render_products()

            category_list.bind("<<ListboxSelect>>", on_category_select)
            search_entry.bind("<KeyRelease>", on_search_change)
            promo_var.trace_add("write", lambda *args: update_cart())
            tax_var.trace_add("write", lambda *args: update_cart())
            service_var.trace_add("write", lambda *args: update_cart())
            shipping_var.trace_add("write", lambda *args: update_cart())

            def add_first_match(event=None):
                matches = filter_products()
                if matches:
                    add_to_cart(matches[0])

            search_entry.bind("<Return>", add_first_match)
            def refresh_pos_views():
                refresh_inventory_snapshot()
                render_products()
                update_cart()

            ui_refresh["callback"] = refresh_pos_views
            render_products()
            update_cart()
            search_entry.focus_set()

        build_layout()

    def create_approval_panel(self, notebook):
        frame = tk.Frame(notebook, bg="white")
        notebook.add(frame, text="Approval")
        self.build_approval_panel(frame)

    def build_approval_panel(self, frame):
        for widget in frame.winfo_children():
            widget.destroy()

        bg = self.ui_palette["bg"]
        surface = self.ui_palette["surface"]

        # ── Toolbar: filter + action buttons ──────────────────────────────────
        toolbar = tk.Frame(frame, bg=bg)
        toolbar.pack(fill="x", padx=10, pady=(8, 4))

        tk.Label(toolbar, text="Filter:", bg=bg, font=("Segoe UI", 9)).pack(side="left", padx=(0, 4))
        filter_var = tk.StringVar(value="Pending")
        filter_combo = ttk.Combobox(
            toolbar, textvariable=filter_var,
            values=["All", "Pending", "Approved", "Rejected"],
            state="readonly", width=12,
        )
        filter_combo.pack(side="left", padx=(0, 16))

        btn_frame = tk.Frame(toolbar, bg=bg)
        btn_frame.pack(side="right")
        tk.Button(btn_frame, text="✓  Approve", command=lambda: approve_selected(),
                  bg="#16a34a", fg="white", font=("Segoe UI", 9, "bold"),
                  relief="flat", padx=10, pady=4).pack(side="left", padx=4)
        tk.Button(btn_frame, text="✗  Reject", command=lambda: reject_selected(),
                  bg="#dc2626", fg="white", font=("Segoe UI", 9, "bold"),
                  relief="flat", padx=10, pady=4).pack(side="left", padx=4)
        tk.Button(btn_frame, text="⟳  Refresh", command=lambda: load_entries(),
                  bg="#475569", fg="white", font=("Segoe UI", 9),
                  relief="flat", padx=10, pady=4).pack(side="left", padx=4)

        # ── Queue table ────────────────────────────────────────────────────────
        table_frame = tk.Frame(frame, bg=surface)
        table_frame.pack(fill="both", expand=True, padx=10, pady=4)

        tree = ttk.Treeview(
            table_frame,
            columns=("ID", "Type", "Entry Type", "Status", "Submitted By", "Created At"),
            show="headings",
            style="App.Treeview",
        )
        col_widths = {"ID": 50, "Type": 130, "Entry Type": 110, "Status": 90,
                      "Submitted By": 120, "Created At": 150}
        for col, w in col_widths.items():
            tree.heading(col, text=col)
            tree.column(col, width=w, anchor="w")

        # Status badge colours
        tree.tag_configure("PENDING",  background="#fef3c7", foreground="#92400e")
        tree.tag_configure("APPROVED", background="#dcfce7", foreground="#14532d")
        tree.tag_configure("REJECTED", background="#fee2e2", foreground="#7f1d1d")

        tree.grid(row=0, column=0, sticky="nsew")
        y_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
        y_scroll.grid(row=0, column=1, sticky="ns")
        tree.configure(yscrollcommand=y_scroll.set)
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        # ── Diff panel: Field / Before / After treeview ───────────────────────
        diff_header = tk.Frame(frame, bg=bg)
        diff_header.pack(fill="x", padx=10, pady=(6, 0))
        tk.Label(diff_header, text="Change Details", font=("Segoe UI", 9, "bold"),
                 bg=bg, fg=self.ui_palette["text"]).pack(side="left")

        diff_frame = tk.Frame(frame, bg=surface,
                              highlightbackground=self.ui_state_colors["neutral_border"],
                              highlightthickness=1)
        diff_frame.pack(fill="x", padx=10, pady=(2, 8))

        diff_tree = ttk.Treeview(
            diff_frame,
            columns=("Field", "Before", "After"),
            show="headings",
            height=6,
            style="App.Treeview.Dense",
        )
        diff_tree.heading("Field",  text="Field")
        diff_tree.heading("Before", text="Before")
        diff_tree.heading("After",  text="After")
        diff_tree.column("Field",  width=180, anchor="w")
        diff_tree.column("Before", width=260, anchor="w")
        diff_tree.column("After",  width=260, anchor="w")
        diff_tree.tag_configure("before_val", foreground="#dc2626")
        diff_tree.tag_configure("after_val",  foreground="#16a34a")
        diff_tree.tag_configure("meta_row",   foreground="#374151")
        diff_tree.pack(fill="x", side="left", expand=True)
        diff_scroll = ttk.Scrollbar(diff_frame, orient="vertical", command=diff_tree.yview)
        diff_scroll.pack(side="right", fill="y")
        diff_tree.configure(yscrollcommand=diff_scroll.set)

        def _populate_diff(entry_type, payload):
            for row in diff_tree.get_children():
                diff_tree.delete(row)

            def _meta(field, value):
                diff_tree.insert("", "end", values=(field, str(value) if value is not None else "", ""),
                                 tags=("meta_row",))

            def _diff_rows(changed, before, after):
                for key in changed:
                    bval = before.get(key, "")
                    aval = after.get(key, "")
                    iid = diff_tree.insert("", "end", values=(key, str(bval), str(aval)))
                    # Colour the Before and After cells via row tag won't colour individual cells,
                    # so we insert two separate sub-rows for changed fields to give contrast
                    diff_tree.item(iid, tags=("meta_row",))

            if entry_type in ("SalesEdit", "StockEdit", "CostEdit"):
                id_key = {"SalesEdit": "sale_id", "StockEdit": "stock_id", "CostEdit": "cost_id"}[entry_type]
                _meta(id_key, payload.get(id_key))
                _meta("reason", payload.get("reason"))
                changed = payload.get("changed_fields") or []
                before  = payload.get("before") or {}
                after   = payload.get("after")  or {}
                diff_tree.insert("", "end", values=("── Changed Fields ──", "", ""), tags=("meta_row",))
                for key in changed:
                    bval = str(before.get(key, ""))
                    aval = str(after.get(key,  ""))
                    diff_tree.insert("", "end",
                                     values=(f"  {key}", f"  {bval}", ""),
                                     tags=("before_val",))
                    diff_tree.insert("", "end",
                                     values=("", "", f"  {aval}"),
                                     tags=("after_val",))
            elif entry_type == "SalesBatch":
                _meta("order_id",       payload.get("order_id"))
                _meta("sale_date",      payload.get("sale_date"))
                _meta("channel",        payload.get("channel"))
                _meta("payment_method", payload.get("payment_method"))
                _meta("subtotal",       payload.get("subtotal"))
                _meta("discount",       payload.get("discount_amount"))
                _meta("tax_rate",       payload.get("tax_rate"))
                _meta("tax_amount",     payload.get("tax_amount"))
                _meta("service_fee",    payload.get("service_fee"))
                _meta("total",          payload.get("total"))
                diff_tree.insert("", "end", values=("── Line Items ──", "", ""), tags=("meta_row",))
                for ln in (payload.get("lines") or []):
                    diff_tree.insert("", "end", values=(
                        f"  {ln.get('product_sku')}",
                        f"  qty={ln.get('units_sold')}  @{ln.get('unit_price')}",
                        f"  gross={ln.get('gross_sales')}",
                    ), tags=("meta_row",))
            else:
                for k, v in payload.items():
                    _meta(k, v)

        def load_entries():
            for item in tree.get_children():
                tree.delete(item)
            for row in diff_tree.get_children():
                diff_tree.delete(row)
            status_filter = filter_var.get()
            try:
                conn = sqlite3.connect(FINANCIAL_DB)
                cursor = conn.cursor()
                if status_filter == "All":
                    cursor.execute(
                        "SELECT id, entry_type, status, created_by, created_at FROM PendingEntries ORDER BY created_at DESC"
                    )
                else:
                    cursor.execute(
                        "SELECT id, entry_type, status, created_by, created_at FROM PendingEntries WHERE status = ? ORDER BY created_at DESC",
                        (status_filter.upper(),),
                    )
                rows = cursor.fetchall()
                conn.close()
                user_ids = list({row[3] for row in rows if row[3] is not None})
                user_map = {}
                if user_ids:
                    try:
                        sec_conn = sqlite3.connect(SECURITY_DB)
                        sec_cursor = sec_conn.cursor()
                        placeholders = ",".join("?" * len(user_ids))
                        sec_cursor.execute(
                            f"SELECT user_id, username FROM Users WHERE user_id IN ({placeholders})",
                            user_ids,
                        )
                        user_map = {r[0]: r[1] for r in sec_cursor.fetchall()}
                        sec_conn.close()
                    except Exception:
                        pass
                for row in rows:
                    entry_type = row[1]
                    if str(entry_type).startswith("Product"):
                        approval_type = "Product Change"
                    elif entry_type == "SalesEdit":
                        approval_type = "Sales Edit"
                    elif entry_type == "StockEdit":
                        approval_type = "Stock Edit"
                    elif entry_type == "CostEdit":
                        approval_type = "Cost Edit"
                    elif entry_type == "SalesBatch":
                        approval_type = "POS Checkout"
                    else:
                        approval_type = "Financial Entry"
                    status = row[2]
                    created_by_display = user_map.get(row[3], str(row[3]) if row[3] is not None else "")
                    tag = status if status in ("PENDING", "APPROVED", "REJECTED") else "meta_row"
                    tree.insert("", "end",
                                values=(row[0], approval_type, entry_type, status, created_by_display, row[4]),
                                tags=(tag,))
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load entries: {e}")

        def on_select(event=None):
            selection = tree.selection()
            if not selection:
                return
            item = tree.item(selection[0])
            entry_id = item["values"][0]
            try:
                conn = sqlite3.connect(FINANCIAL_DB)
                cursor = conn.cursor()
                cursor.execute("SELECT entry_type, payload FROM PendingEntries WHERE id = ?", (entry_id,))
                row = cursor.fetchone()
                conn.close()
                if row:
                    entry_type, payload_json = row
                    payload = json.loads(payload_json)
                    _populate_diff(entry_type, payload)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load entry details: {e}")

        def _select_next_pending():
            """After an action, select the next PENDING row if any."""
            for iid in tree.get_children():
                vals = tree.item(iid, "values")
                if vals and str(vals[3]).upper() == "PENDING":
                    tree.selection_set(iid)
                    tree.see(iid)
                    on_select()
                    return

        def approve_selected():
            selection = tree.selection()
            if not selection:
                messagebox.showwarning("Warning", "Select an entry to approve")
                return
            item = tree.item(selection[0])
            entry_id = item["values"][0]
            if messagebox.askyesno("Confirm Approval", f"Approve entry #{entry_id}?"):
                try:
                    self.apply_pending_entry(entry_id)
                    self.log_action("APPROVE_ENTRY", f"Approved entry {entry_id}")
                    load_entries()
                    _select_next_pending()
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to approve entry: {e}")

        def reject_selected():
            selection = tree.selection()
            if not selection:
                messagebox.showwarning("Warning", "Select an entry to reject")
                return
            item = tree.item(selection[0])
            entry_id = item["values"][0]
            reason = simpledialog.askstring("Reject Entry", "Reason for rejection:")
            if reason is None:
                return
            try:
                self.reject_pending_entry(entry_id, reason)
                self.log_action("REJECT_ENTRY", f"Rejected entry {entry_id}")
                load_entries()
                _select_next_pending()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to reject entry: {e}")

        filter_combo.bind("<<ComboboxSelected>>", lambda e: load_entries())
        tree.bind("<<TreeviewSelect>>", on_select)
        load_entries()

    def reject_pending_entry(self, entry_id, reason):
        conn = sqlite3.connect(FINANCIAL_DB)
        try:
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE")
            cursor.execute(
                "UPDATE PendingEntries SET status = 'IN_PROGRESS' WHERE id = ? AND status = 'PENDING'",
                (entry_id,),
            )
            if cursor.rowcount == 0:
                raise ValueError("Pending entry not found or already being processed.")
            cursor.execute(
                "SELECT entry_type, created_by FROM PendingEntries WHERE id = ? AND status = 'IN_PROGRESS'",
                (entry_id,),
            )
            row = cursor.fetchone()
            if not row:
                raise ValueError("Pending entry could not be loaded for rejection.")
            entry_type, created_by = row
            self.validate_pending_entry_approval_permission(entry_type, created_by)
            cursor.execute(
                """
                UPDATE PendingEntries
                SET status = 'REJECTED', rejected_reason = ?, approved_by = ?, approved_at = CURRENT_TIMESTAMP
                WHERE id = ? AND status = 'IN_PROGRESS'
                """,
                (reason, self.current_user['user_id'], entry_id),
            )
            if cursor.rowcount == 0:
                raise ValueError("Pending entry rejection could not be finalized.")
            conn.commit()
        except Exception as e:
            conn.rollback()
            self.log_action("REJECT_ENTRY_FAILED", f"entry_id={entry_id}, error={e}")
            raise
        finally:
            conn.close()

    def apply_pending_entry(self, entry_id):
        conn = sqlite3.connect(FINANCIAL_DB)
        try:
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE")
            cursor.execute(
                "UPDATE PendingEntries SET status = 'IN_PROGRESS' WHERE id = ? AND status = 'PENDING'",
                (entry_id,),
            )
            if cursor.rowcount == 0:
                raise ValueError("Pending entry not found or already being processed.")

            cursor.execute(
                "SELECT entry_type, payload, created_by FROM PendingEntries WHERE id = ? AND status = 'IN_PROGRESS'",
                (entry_id,),
            )
            row = cursor.fetchone()
            if not row:
                raise ValueError("Pending entry could not be loaded for approval.")

            entry_type, payload_json, created_by = row
            self.validate_pending_entry_approval_permission(entry_type, created_by)
            payload = json.loads(payload_json)
            if entry_type == "Sales":
                sku = payload.get("product_sku")
                if not self.product_exists(sku, cursor):
                    raise ValueError(f"Product SKU '{sku}' not found for Sales entry")
                units_sold = self.parse_int_input(payload.get("units_sold"))
                cursor.execute(
                    """
                    SELECT
                        COALESCE((SELECT SUM(unit_in) FROM Stock WHERE product_sku = ?), 0)
                        -
                        COALESCE((SELECT SUM(units_sold) FROM Sales WHERE product_sku = ?), 0)
                    """,
                    (sku, sku),
                )
                available = self.parse_int_input(cursor.fetchone()[0]) or 0
                projected = available - (units_sold or 0)
                cursor.execute(
                    """
                    INSERT INTO Sales (sale_date, order_id, channel, product_sku, units_sold, unit_price, gross_sales, service_fee, shipping_fee, note)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        payload.get("sale_date"),
                        payload.get("order_id"),
                        payload.get("channel"),
                        sku,
                        units_sold,
                        self.parse_float_input(payload.get("unit_price")),
                        self.parse_float_input(payload.get("gross_sales")),
                        self.parse_float_input(payload.get("service_fee")),
                        self.parse_float_input(payload.get("shipping_fee")),
                        payload.get("note"),
                    ),
                )
                cursor.execute(
                    "UPDATE Sales SET approved_by = ?, approved_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (self.current_user['user_id'], cursor.lastrowid),
                )
                alert_level = self.stock_alert_level(projected)
                if alert_level in {"critical", "low"}:
                    cursor.execute(
                        """
                        INSERT INTO Logs (log_date, log_type, product_sku, details)
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            payload.get("sale_date"),
                            "StockWarning",
                            sku,
                            f"Approval warning: projected stock {projected} after Sales approval",
                        ),
                    )
            elif entry_type == "SalesBatch":
                sale_date = payload.get("sale_date")
                order_id = payload.get("order_id") or self.generate_receipt_no()
                channel = payload.get("channel") or "POS"
                note = payload.get("note")
                payment_method = payload.get("payment_method")
                lines = payload.get("lines") or []
                if not lines:
                    raise ValueError("Sales batch payload does not contain any line items.")

                for line in lines:
                    sku = line.get("product_sku")
                    if not self.product_exists(sku, cursor):
                        raise ValueError(f"Product SKU '{sku}' not found for Sales batch entry")
                    units_sold = self.parse_int_input(line.get("units_sold"))
                    if units_sold is None or units_sold <= 0:
                        raise ValueError(f"Invalid units_sold for SKU '{sku}' in Sales batch entry")
                    cursor.execute(
                        """
                        SELECT
                            COALESCE((SELECT SUM(unit_in) FROM Stock WHERE product_sku = ?), 0)
                            -
                            COALESCE((SELECT SUM(units_sold) FROM Sales WHERE product_sku = ?), 0)
                        """,
                        (sku, sku),
                    )
                    available = self.parse_int_input(cursor.fetchone()[0]) or 0
                    projected = available - units_sold

                    line_note_parts = []
                    if note:
                        line_note_parts.append(str(note).strip())
                    if payment_method:
                        line_note_parts.append(f"payment={payment_method}")
                    if line.get("line_note"):
                        line_note_parts.append(str(line.get("line_note")).strip())
                    line_note = "; ".join([part for part in line_note_parts if part]) or None

                    cursor.execute(
                        """
                        INSERT INTO Sales (sale_date, order_id, channel, product_sku, units_sold, unit_price, gross_sales, service_fee, shipping_fee, note)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            sale_date,
                            order_id,
                            channel,
                            sku,
                            units_sold,
                            self.parse_float_input(line.get("unit_price")),
                            self.parse_float_input(line.get("gross_sales")),
                            self.parse_float_input(line.get("service_fee")),
                            self.parse_float_input(line.get("shipping_fee")),
                            line_note,
                        ),
                    )
                    cursor.execute(
                        "UPDATE Sales SET approved_by = ?, approved_at = CURRENT_TIMESTAMP WHERE id = ?",
                        (self.current_user['user_id'], cursor.lastrowid),
                    )

                    alert_level = self.stock_alert_level(projected)
                    if alert_level in {"critical", "low"}:
                        cursor.execute(
                            """
                            INSERT INTO Logs (log_date, log_type, product_sku, details)
                            VALUES (?, ?, ?, ?)
                            """,
                            (
                                sale_date,
                                "StockWarning",
                                sku,
                                f"Approval warning: projected stock {projected} after Sales batch approval; order_id={order_id}",
                            ),
                        )
            elif entry_type == "SalesReceipt":
                sale_date = payload.get("sale_date")
                receipt_no = payload.get("receipt_no") or self.generate_receipt_no()
                customer = payload.get("customer") or {}
                products = payload.get("products") or []
                services = payload.get("services") or []
                tax_rate = self.parse_float_input(payload.get("tax_rate")) or 0.0
                subtotal = self.parse_float_input(payload.get("subtotal")) or 0.0
                service_total = self.parse_float_input(payload.get("service_total")) or 0.0
                tax_amount = self.parse_float_input(payload.get("tax_amount")) or 0.0
                total = self.parse_float_input(payload.get("total")) or 0.0

                customer_name = str(customer.get("name") or "").strip()
                customer_phone = str(customer.get("phone") or "").strip()
                customer_email = str(customer.get("email") or "").strip()
                customer_address = str(customer.get("address") or "").strip()
                if not all([customer_name, customer_phone, customer_email, customer_address]):
                    raise ValueError("Customer name, phone, email, and address are required")

                norm_phone = self.normalize_phone(customer_phone)
                norm_email = self.normalize_email(customer_email)
                norm_address = self.normalize_address(customer_address)

                cursor.execute(
                    """
                    SELECT id, norm_phone, norm_email, norm_address
                    FROM CustomerProfiles
                    WHERE status = 'ACTIVE'
                    """
                )
                matched_customer_id = None
                best_score = 0
                for customer_row in cursor.fetchall():
                    score = 0
                    if norm_phone and customer_row[1] and norm_phone == customer_row[1]:
                        score += 1
                    if norm_email and customer_row[2] and norm_email == customer_row[2]:
                        score += 1
                    if norm_address and customer_row[3] and norm_address == customer_row[3]:
                        score += 1
                    if score >= 2 and score > best_score:
                        best_score = score
                        matched_customer_id = customer_row[0]

                if matched_customer_id is None:
                    cursor.execute(
                        """
                        INSERT INTO CustomerProfiles (
                            full_name, phone, email, address, norm_phone, norm_email, norm_address, status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, 'ACTIVE')
                        """,
                        (
                            customer_name,
                            customer_phone,
                            customer_email,
                            customer_address,
                            norm_phone,
                            norm_email,
                            norm_address,
                        ),
                    )
                    matched_customer_id = cursor.lastrowid
                else:
                    cursor.execute(
                        """
                        UPDATE CustomerProfiles
                        SET full_name = ?, phone = ?, email = ?, address = ?,
                            norm_phone = ?, norm_email = ?, norm_address = ?
                        WHERE id = ?
                        """,
                        (
                            customer_name,
                            customer_phone,
                            customer_email,
                            customer_address,
                            norm_phone,
                            norm_email,
                            norm_address,
                            matched_customer_id,
                        ),
                    )

                cursor.execute(
                    """
                    INSERT INTO SalesReceipts (
                        pending_entry_id, customer_id, receipt_no, sale_date, tax_rate, subtotal,
                        service_total, tax_amount, total, status, pdf_path, note, created_by, approved_by,
                        approved_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'APPROVED', ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    (
                        entry_id,
                        matched_customer_id,
                        receipt_no,
                        sale_date,
                        tax_rate,
                        subtotal,
                        service_total,
                        tax_amount,
                        total,
                        payload.get("pdf_path"),
                        payload.get("note"),
                        created_by,
                        self.current_user['user_id'],
                    ),
                )
                receipt_id = cursor.lastrowid

                all_lines = []
                all_lines.extend(products)
                all_lines.extend(services)
                taxable_total = subtotal + service_total
                for line in all_lines:
                    line_type = line.get("line_type") or ("Product" if line in products else "Service")
                    item_name = line.get("item_name")
                    sku = line.get("product_sku")
                    unit_price = self.parse_float_input(line.get("unit_price")) or 0.0
                    quantity = self.parse_int_input(line.get("quantity")) or 0
                    line_total = self.parse_float_input(line.get("line_total")) or (unit_price * quantity)

                    if line_type == "Product" and sku and not self.product_exists(sku, cursor):
                        raise ValueError(f"Product SKU '{sku}' not found for receipt line")

                    cursor.execute(
                        """
                        INSERT INTO SalesReceiptLines (receipt_id, line_type, item_name, product_sku, unit_price, quantity, line_total)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (receipt_id, line_type, item_name, sku, unit_price, quantity, line_total),
                    )

                    line_tax = (line_total / taxable_total * tax_amount) if taxable_total > 0 else 0.0
                    gross_sales = line_total + line_tax
                    cursor.execute(
                        """
                        INSERT INTO Sales (
                            sale_date, order_id, channel, product_sku, units_sold,
                            unit_price, gross_sales, vat_rate, vat_amount, service_fee, shipping_fee, note,
                            approved_by, approved_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                        """,
                        (
                            sale_date,
                            receipt_no,
                            "POS",
                            sku,
                            quantity if line_type == "Product" else quantity,
                            unit_price,
                            gross_sales,
                            tax_rate,
                            line_tax,
                            0.0,
                            0.0,
                            f"ReceiptLine:{line_type}:{item_name}; customer_id={matched_customer_id}",
                            self.current_user['user_id'],
                        ),
                    )

                cursor.execute(
                    """
                    UPDATE CustomerMatchFlags
                    SET status = 'RESOLVED', reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP,
                        review_note = COALESCE(review_note, 'Resolved during SalesReceipt approval')
                    WHERE pending_entry_id = ?
                    """,
                    (self.current_user['user_id'], entry_id),
                )
            elif entry_type == "SalesEdit":
                self.validate_sales_edit_approval_permission(created_by)

                sale_id = self.parse_int_input(payload.get("sale_id"))
                if not sale_id:
                    raise ValueError("Sales edit payload is missing a valid sale_id.")

                after = payload.get("after")
                if not isinstance(after, dict):
                    raise ValueError("Sales edit payload is missing an 'after' object.")

                existing = self.get_sales_row_by_id(sale_id, cursor=cursor)
                if not existing:
                    raise ValueError(f"Sales record #{sale_id} was not found.")

                sku = str(after.get("product_sku") or "").strip()
                if sku and not self.product_exists(sku, cursor):
                    raise ValueError(f"Product SKU '{sku}' does not exist.")

                sale_date = self.parse_date_input(after.get("sale_date"))
                if not sale_date:
                    raise ValueError("Sale Date is required and must be YYYY-MM-DD.")

                units_sold = self.parse_int_input(after.get("units_sold"))
                if units_sold is None:
                    raise ValueError("Units Sold must be a valid integer.")

                def require_float_value(field_key):
                    parsed = self.parse_float_input(after.get(field_key))
                    if parsed is None:
                        raise ValueError(f"{field_key.replace('_', ' ').title()} must be a valid number.")
                    return parsed

                unit_price = require_float_value("unit_price")
                service_fee = require_float_value("service_fee")
                shipping_fee = require_float_value("shipping_fee")

                vat_rate_raw = after.get("vat_rate")
                if vat_rate_raw is None:
                    vat_rate_raw = existing.get("vat_rate")
                if vat_rate_raw is None:
                    vat_rate_raw = 0.0
                vat_rate = self.parse_float_input(vat_rate_raw)
                managed_sales_tax_rates = {0.0, 8.0, 10.0}
                if vat_rate is None or vat_rate not in managed_sales_tax_rates:
                    raise ValueError("Tax % must be one of: 0%, 8%, 10%.")
                pre_tax_total = unit_price * units_sold
                gross_sales = round(pre_tax_total * (100.0 + vat_rate) / 100.0, 2)
                vat_amount = round(gross_sales * vat_rate / (100.0 + vat_rate), 2) if vat_rate > 0 else 0.0

                cursor.execute(
                    """
                    UPDATE Sales
                    SET sale_date = ?, order_id = ?, channel = ?, product_sku = ?,
                        units_sold = ?, unit_price = ?, gross_sales = ?,
                        vat_rate = ?, vat_amount = ?, service_fee = ?, shipping_fee = ?, note = ?
                    WHERE id = ?
                    """,
                    (
                        sale_date,
                        (str(after.get("order_id") or "").strip() or None),
                        (str(after.get("channel") or "").strip() or None),
                        (sku or None),
                        units_sold,
                        unit_price,
                        gross_sales,
                        vat_rate,
                        vat_amount,
                        service_fee,
                        shipping_fee,
                        (str(after.get("note") or "").strip() or None),
                        sale_id,
                    ),
                )
                if cursor.rowcount == 0:
                    raise ValueError(f"Sales record #{sale_id} was not updated.")

                cursor.execute(
                    "UPDATE Sales SET approved_by = ?, approved_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (self.current_user['user_id'], sale_id),
                )
                changed_fields = payload.get("changed_fields") or []
                reason = payload.get("reason")
                self.log_action(
                    "APPLY_SALES_EDIT",
                    f"approved_by={self.current_user['user_id']}, sale_id={sale_id}, changed={','.join(changed_fields)}, reason={reason}",
                )
            elif entry_type == "StockEdit":
                self.validate_stock_edit_approval_permission(created_by)

                stock_id = self.parse_int_input(payload.get("stock_id"))
                if not stock_id:
                    raise ValueError("Stock edit payload is missing a valid stock_id.")

                after = payload.get("after")
                if not isinstance(after, dict):
                    raise ValueError("Stock edit payload is missing an 'after' object.")

                existing = self.get_stock_row_by_id(stock_id, cursor=cursor)
                if not existing:
                    raise ValueError(f"Stock record #{stock_id} was not found.")

                stock_date = self.parse_date_input(after.get("date"))
                if not stock_date:
                    raise ValueError("Date is required and must be YYYY-MM-DD.")

                sku = str(after.get("product_sku") or "").strip()
                if not sku:
                    raise ValueError("Product SKU is required.")
                if not self.product_exists(sku, cursor):
                    raise ValueError(f"Product SKU '{sku}' does not exist.")

                unit_cost = self.parse_float_input(after.get("unit_cost"))
                if unit_cost is None:
                    raise ValueError("Unit Cost must be a valid number.")

                current_unit_price = self.parse_float_input(after.get("current_unit_price"))
                if current_unit_price is None or current_unit_price <= 0:
                    raise ValueError("Current Unit Price is required and must be greater than 0.")

                unit_in = self.parse_int_input(after.get("unit_in"))
                if unit_in is None or unit_in <= 0:
                    raise ValueError("Unit In must be a valid integer greater than 0.")

                tax_rate = self.parse_float_input(after.get("tax_rate"))
                if tax_rate not in {8.0, 10.0}:
                    raise ValueError("Stock Tax % must be either 8 or 10")

                pre_tax_total = unit_cost * unit_in
                tax_amount = round(pre_tax_total * tax_rate / 100.0, 2)
                total = round(pre_tax_total, 2)

                cursor.execute(
                    """
                    UPDATE Stock
                    SET date = ?, product_sku = ?, unit_cost = ?, current_unit_price = ?,
                        unit_in = ?, tax_rate = ?, tax_amount = ?, total = ?, note = ?,
                        approved_by = ?, approved_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (
                        stock_date,
                        sku,
                        unit_cost,
                        current_unit_price,
                        unit_in,
                        tax_rate,
                        tax_amount,
                        total,
                        (str(after.get("note") or "").strip() or None),
                        self.current_user['user_id'],
                        stock_id,
                    ),
                )
                if cursor.rowcount == 0:
                    raise ValueError(f"Stock record #{stock_id} was not updated.")

                cursor.execute(
                    """
                    UPDATE Products
                    SET unit_cost = ?, current_unit_price = ?
                    WHERE sku = ?
                    """,
                    (unit_cost, current_unit_price, sku),
                )

                changed_fields = payload.get("changed_fields") or []
                reason = payload.get("reason")
                self.log_action(
                    "APPLY_STOCK_EDIT",
                    f"approved_by={self.current_user['user_id']}, stock_id={stock_id}, changed={','.join(changed_fields)}, reason={reason}",
                )
            elif entry_type == "Costs":
                cost_type = str(payload.get("cost_type") or "").strip()
                if not cost_type:
                    raise ValueError("Cost Type is required.")

                amount = self.parse_float_input(payload.get("amount"))
                if amount is None:
                    raise ValueError("Amount must be a valid number.")

                cost_date_raw = payload.get("cost_date")
                if cost_date_raw is None:
                    cost_date_raw = payload.get("date")
                cost_date = self.parse_date_input(cost_date_raw)
                if not cost_date:
                    raise ValueError("Cost Date is required and must be YYYY-MM-DD.")

                cursor.execute(
                    """
                    INSERT INTO Costs (cost_type, cost_date, amount, note)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        cost_type,
                        cost_date,
                        amount,
                        (str(payload.get("note") or "").strip() or None),
                    ),
                )

                self.log_action(
                    "APPLY_COST",
                    f"approved_by={self.current_user['user_id']}, cost_type={cost_type}, cost_date={cost_date}, amount={amount:.2f}",
                )
            elif entry_type == "CostEdit":
                self.validate_cost_edit_approval_permission(created_by)

                cost_id = self.parse_int_input(payload.get("cost_id"))
                if not cost_id:
                    raise ValueError("Cost edit payload is missing a valid cost_id.")

                after = payload.get("after")
                if not isinstance(after, dict):
                    raise ValueError("Cost edit payload is missing an 'after' object.")

                existing = self.get_cost_row_by_id(cost_id, cursor=cursor)
                if not existing:
                    raise ValueError(f"Cost record #{cost_id} was not found.")

                cost_date = self.parse_date_input(after.get("cost_date"))
                if not cost_date:
                    raise ValueError("Cost Date is required and must be YYYY-MM-DD.")

                cost_type = str(after.get("cost_type") or "").strip()
                if not cost_type:
                    raise ValueError("Cost Type is required.")

                amount = self.parse_float_input(after.get("amount"))
                if amount is None:
                    raise ValueError("Amount must be a valid number.")

                vat_rate = self.parse_float_input(after.get("vat_rate"))
                if vat_rate is None:
                    vat_rate = self.parse_float_input(existing.get("vat_rate"))
                if vat_rate is None:
                    vat_rate = 0.0
                if vat_rate < 0 or vat_rate > 100:
                    raise ValueError("VAT % must be between 0 and 100.")

                vat_amount = round(amount * vat_rate / 100.0, 2)

                cursor.execute(
                    """
                    UPDATE Costs
                    SET cost_type = ?, cost_date = ?, amount = ?, vat_rate = ?, vat_amount = ?, note = ?
                    WHERE id = ?
                    """,
                    (
                        cost_type,
                        cost_date,
                        amount,
                        vat_rate,
                        vat_amount,
                        (str(after.get("note") or "").strip() or None),
                        cost_id,
                    ),
                )
                if cursor.rowcount == 0:
                    raise ValueError(f"Cost record #{cost_id} was not updated.")

                changed_fields = payload.get("changed_fields") or []
                reason = payload.get("reason")
                self.log_action(
                    "APPLY_COST_EDIT",
                    f"approved_by={self.current_user['user_id']}, cost_id={cost_id}, changed={','.join(changed_fields)}, reason={reason}",
                )
            elif entry_type == "Stock":
                stock_lines = payload.get("lines")
                allowed_tax_rates = {8.0, 10.0}
                if isinstance(stock_lines, list) and stock_lines:
                    for line in stock_lines:
                        sku = line.get("product_sku")
                        if not self.product_exists(sku, cursor):
                            raise ValueError(f"Product SKU '{sku}' not found for Stock entry")
                        unit_cost = self.parse_float_input(line.get("unit_cost")) or 0.0
                        current_unit_price = self.parse_float_input(line.get("current_unit_price"))
                        if current_unit_price is None or current_unit_price <= 0:
                            raise ValueError(f"Current Unit Price is required and must be greater than 0 for SKU '{sku}'")
                        unit_in = self.parse_int_input(line.get("unit_in")) or 0
                        if unit_in <= 0:
                            raise ValueError(f"Unit In must be greater than 0 for SKU '{sku}'")
                        line_tax_rate = self.parse_float_input(line.get("tax_rate"))
                        payload_tax_rate = self.parse_float_input(payload.get("tax_rate"))
                        if line_tax_rate in allowed_tax_rates:
                            tax_rate = line_tax_rate
                        elif payload_tax_rate in allowed_tax_rates:
                            tax_rate = payload_tax_rate
                        elif line_tax_rate is None and payload_tax_rate is None:
                            tax_rate = 8.0
                        else:
                            raise ValueError("Stock Tax % must be either 8 or 10")
                        pre_tax_total = unit_cost * unit_in
                        tax_amount = round(pre_tax_total * tax_rate / 100.0, 2)
                        total = round(pre_tax_total, 2)

                        cursor.execute(
                            """
                            INSERT INTO Stock (date, product_sku, unit_cost, current_unit_price, unit_in, tax_rate, tax_amount, total, note)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                line.get("date") or payload.get("date"),
                                sku,
                                unit_cost,
                                current_unit_price,
                                unit_in,
                                tax_rate,
                                tax_amount,
                                total,
                                payload.get("note"),
                            ),
                        )
                        cursor.execute(
                            """
                            UPDATE Products
                            SET unit_cost = ?, current_unit_price = ?
                            WHERE sku = ?
                            """,
                            (unit_cost, current_unit_price, sku),
                        )
                else:
                    sku = payload.get("product_sku")
                    if not self.product_exists(sku, cursor):
                        raise ValueError(f"Product SKU '{sku}' not found for Stock entry")
                    unit_cost = self.parse_float_input(payload.get("unit_cost")) or 0.0
                    current_unit_price = self.parse_float_input(
                        payload.get("current_unit_price", payload.get("unit_price"))
                    )
                    if current_unit_price is None or current_unit_price <= 0:
                        raise ValueError("Current Unit Price is required and must be greater than 0")
                    unit_in = self.parse_int_input(payload.get("unit_in")) or 0
                    if unit_in <= 0:
                        raise ValueError("Unit In must be greater than 0")
                    payload_tax_rate = self.parse_float_input(payload.get("tax_rate"))
                    if payload_tax_rate in allowed_tax_rates:
                        tax_rate = payload_tax_rate
                    elif payload_tax_rate is None:
                        tax_rate = 8.0
                    else:
                        raise ValueError("Stock Tax % must be either 8 or 10")
                    pre_tax_total = unit_cost * unit_in
                    tax_amount = round(pre_tax_total * tax_rate / 100.0, 2)
                    total = round(pre_tax_total, 2)

                    cursor.execute(
                        """
                        INSERT INTO Stock (date, product_sku, unit_cost, current_unit_price, unit_in, tax_rate, tax_amount, total, note)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            payload.get("date"),
                            sku,
                            unit_cost,
                            current_unit_price,
                            unit_in,
                            tax_rate,
                            tax_amount,
                            total,
                            payload.get("note"),
                        ),
                    )
                    cursor.execute(
                        """
                        UPDATE Products
                        SET unit_cost = ?, current_unit_price = ?
                        WHERE sku = ?
                        """,
                        (unit_cost, current_unit_price, sku),
                    )
            elif entry_type == "Timeline":
                cursor.execute(
                    """
                    INSERT INTO Timeline (event_date, event_name, cash_in, cash_out, balance, note)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        payload.get("event_date"),
                        payload.get("event_name"),
                        self.parse_float_input(payload.get("cash_in")),
                        self.parse_float_input(payload.get("cash_out")),
                        self.parse_float_input(payload.get("balance")),
                        payload.get("note"),
                    ),
                )
            elif entry_type == "ProductAdd":
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO Products (sku, name, category, unit_cost, current_unit_price, image_path)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        payload.get("sku"),
                        payload.get("name"),
                        payload.get("category"),
                        self.parse_float_input(payload.get("unit_cost")),
                        self.parse_float_input(payload.get("current_unit_price", payload.get("unit_price"))),
                        payload.get("image_path"),
                    ),
                )
            elif entry_type == "ProductUpdate":
                updates = []
                params = []
                if payload.get("unit_cost") is not None:
                    updates.append("unit_cost = ?")
                    params.append(self.parse_float_input(payload.get("unit_cost")))
                proposed_current_price = payload.get("current_unit_price", payload.get("unit_price"))
                if proposed_current_price is not None:
                    updates.append("current_unit_price = ?")
                    params.append(self.parse_float_input(proposed_current_price))
                if payload.get("image_path") is not None:
                    updates.append("image_path = ?")
                    params.append(payload.get("image_path"))
                if not updates:
                    raise ValueError("No updates provided")
                params.append(payload.get("sku"))
                cursor.execute(
                    f"UPDATE Products SET {', '.join(updates)} WHERE sku = ?",
                    tuple(params),
                )
                if cursor.rowcount == 0:
                    raise ValueError("SKU not found for update")
            elif entry_type == "ProductRemove":
                cursor.execute("DELETE FROM Products WHERE sku = ?", (payload.get("sku"),))
                if cursor.rowcount == 0:
                    raise ValueError("SKU not found for removal")
            else:
                raise ValueError(f"Unsupported entry type: {entry_type}")

            cursor.execute(
                """
                UPDATE PendingEntries
                SET status = 'APPROVED', approved_by = ?, approved_at = CURRENT_TIMESTAMP
                WHERE id = ? AND status = 'IN_PROGRESS'
                """,
                (self.current_user['user_id'], entry_id),
            )
            if cursor.rowcount == 0:
                raise ValueError("Pending entry approval could not be finalized.")
            conn.commit()
        except Exception as e:
            conn.rollback()
            self.log_action("APPROVAL_FAILED", f"entry_id={entry_id}, error={e}")
            raise
        finally:
            conn.close()

    def show_user_management(self):
        for widget in self.content_area.winfo_children():
            widget.destroy()

        tk.Label(self.content_area, text="User Management",
                font=("Segoe UI", 18, "bold"), bg="white").pack(pady=20)

        can_add_any = len(PERMISSIONS.get(self.current_level, {}).get('can_add_users', [])) > 0
        can_remove_any = len(PERMISSIONS.get(self.current_level, {}).get('can_remove_users', [])) > 0
        can_edit_any = self.current_level in {3, 4}

        btn_frame = tk.Frame(self.content_area, bg="white")
        btn_frame.pack(pady=10)

        if can_add_any:
            tk.Button(btn_frame, text="Add User", command=self.add_user_dialog,
                     bg="#4CAF50", fg="white", width=15, height=2).pack(side="left", padx=10)

        if can_remove_any:
            tk.Button(btn_frame, text="Remove User", command=self.remove_user_dialog,
                     bg="#f44336", fg="white", width=15, height=2).pack(side="left", padx=10)

        if can_edit_any:
            def edit_selected_user():
                selection = tree.selection()
                if not selection:
                    messagebox.showwarning("Warning", "Select a user to edit")
                    return
                target_user_id = self.parse_int_input(selection[0])
                if not target_user_id:
                    messagebox.showerror("Error", "Could not determine selected user ID")
                    return
                self.edit_user_dialog(target_user_id)

            tk.Button(btn_frame, text="Edit Selected User", command=edit_selected_user,
                     bg="#1976d2", fg="white", width=18, height=2).pack(side="left", padx=10)

        if not can_add_any and not can_remove_any and not can_edit_any:
            tk.Label(self.content_area, text="Insufficient permissions for user management",
                    fg="red", bg="white").pack(pady=20)
            return

        tk.Label(self.content_area, text="Existing Users:", bg="white", font=("Segoe UI", 12, "bold")).pack(pady=10)

        list_frame = tk.Frame(self.content_area, bg="white")
        list_frame.pack(pady=10, padx=20, fill="both", expand=True)

        tree = ttk.Treeview(list_frame, columns=("ID", "Username", "Name", "Role", "Level"), show="headings")
        tree.heading("ID", text="ID")
        tree.heading("Username", text="Username")
        tree.heading("Name", text="Name")
        tree.heading("Role", text="Role")
        tree.heading("Level", text="Security Level")

        tree.column("ID", width=50)
        tree.column("Username", width=150)
        tree.column("Name", width=200)
        tree.column("Role", width=150)
        tree.column("Level", width=150)

        try:
            conn = sqlite3.connect(SECURITY_DB)
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, display_id, username, first_name, last_name, role, security_level FROM Users")
            users = cursor.fetchall()
            conn.close()

            for user in users:
                name = f"{user[3]} {user[4]}" if user[3] and user[4] else "N/A"
                level = SECURITY_LEVELS.get(user[6], "Unknown")
                visible_id = user[1] if user[1] else str(user[0])
                tree.insert("", "end", iid=str(user[0]), values=(visible_id, user[2], name, user[5], level))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load users: {e}")

        tree.pack(fill="both", expand=True)

    def edit_user_dialog(self, target_user_id):
        target_user = self.get_security_user_record(target_user_id)
        if not target_user:
            messagebox.showerror("Error", "Selected user was not found.")
            return

        target_level = target_user.get('security_level')
        if not self.can_edit_user_level(target_level):
            messagebox.showerror(
                "Access Denied",
                f"Level {self.current_level} ({SECURITY_LEVELS.get(self.current_level, 'Unknown')}) cannot edit Level {target_level} users."
            )
            return
        if target_level == 5:
            messagebox.showerror(
                "Access Denied",
                "Level 5 users cannot be edited through User Management."
            )
            return

        dialog = tk.Toplevel(self.root)
        dialog.title(f"Edit User: {target_user.get('username')}")
        dialog.geometry("430x520")

        tk.Label(dialog, text=f"Editing Level {target_level} ({SECURITY_LEVELS.get(target_level, 'Unknown')}) user",
                fg="blue", font=("Segoe UI", 9, "italic")).grid(row=0, column=0, columnspan=2, pady=5)

        fields = [
            ("ID:", "display_id"),
            ("Username:", "username"),
            ("First Name:", "first_name"),
            ("Last Name:", "last_name"),
            ("Date of Birth (YYYY-MM-DD):", "dob"),
            ("Role:", "role"),
            ("New Password (optional):", "password"),
        ]

        entries = {}
        for i, (label, key) in enumerate(fields, start=1):
            tk.Label(dialog, text=label).grid(row=i, column=0, padx=10, pady=5, sticky="e")
            initial_value = ""
            if key != "password":
                initial_value = "" if target_user.get(key) is None else str(target_user.get(key))
            entry = tk.Entry(dialog, width=30, show="*" if key == "password" else "")
            entry.insert(0, initial_value)
            entry.grid(row=i, column=1, padx=10, pady=5)
            entries[key] = entry

        def save_user_changes():
            try:
                user_data = {key: entry.get().strip() for key, entry in entries.items()}

                if not user_data['display_id'] or not user_data['username'] or not user_data['first_name'] or not user_data['last_name']:
                    messagebox.showerror("Error", "ID, username, first name, and last name are required")
                    return

                dob_value = user_data['dob'] or None
                if dob_value and not self.parse_date_input(dob_value):
                    messagebox.showerror("Error", "Date of Birth must use YYYY-MM-DD format")
                    return

                if user_data['password']:
                    password_error = self.validate_password_policy(user_data['password'])
                    if password_error:
                        messagebox.showerror("Error", password_error)
                        return

                conn = sqlite3.connect(SECURITY_DB)
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT user_id FROM Users WHERE username = ? AND user_id <> ?",
                    (user_data['username'], target_user_id),
                )
                duplicate = cursor.fetchone()
                if duplicate:
                    conn.close()
                    messagebox.showerror("Error", f"Username '{user_data['username']}' is already in use.")
                    return

                cursor.execute(
                    "SELECT user_id FROM Users WHERE display_id = ? AND user_id <> ?",
                    (user_data['display_id'], target_user_id),
                )
                duplicate_id = cursor.fetchone()
                if duplicate_id:
                    conn.close()
                    messagebox.showerror("Error", f"ID '{user_data['display_id']}' is already in use.")
                    return

                cursor.execute("SELECT security_level FROM Users WHERE user_id = ?", (target_user_id,))
                current_row = cursor.fetchone()
                if not current_row:
                    conn.close()
                    messagebox.showerror("Error", "Target user no longer exists.")
                    return
                current_target_level = current_row[0]
                if not self.can_edit_user_level(current_target_level) or current_target_level == 5:
                    conn.close()
                    messagebox.showerror("Access Denied", "You no longer have permission to edit this user.")
                    return

                changed_fields = []
                update_parts = []
                update_values = []
                for field_key in ("display_id", "username", "first_name", "last_name", "dob", "role"):
                    new_value = user_data[field_key] or None
                    old_value = target_user.get(field_key)
                    if str(old_value or "") != str(new_value or ""):
                        changed_fields.append(field_key)
                        update_parts.append(f"{field_key} = ?")
                        update_values.append(new_value)

                if user_data['password']:
                    changed_fields.append("password_reset")
                    update_parts.append("password_hash = ?")
                    update_values.append(bcrypt.hashpw(user_data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8'))

                if not changed_fields:
                    conn.close()
                    messagebox.showinfo("No Changes", "No changes were made.")
                    return

                update_values.append(target_user_id)
                cursor.execute(
                    f"UPDATE Users SET {', '.join(update_parts)} WHERE user_id = ?",
                    tuple(update_values),
                )
                conn.commit()
                conn.close()

                self.log_action(
                    "EDIT_USER",
                    f"Edited user_id={target_user_id}, username={user_data['username']}, changed={','.join(changed_fields)}",
                )
                if target_user_id == self.current_user['user_id']:
                    self.refresh_current_user_profile()
                messagebox.showinfo("Success", "User updated successfully")
                dialog.destroy()
                self.show_user_management()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to update user: {e}")

        tk.Button(dialog, text="Save Changes", command=save_user_changes, bg="#1976d2", fg="white", width=20).grid(
            row=len(fields)+1, column=0, columnspan=2, pady=20
        )

    def add_user_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Add New User")
        dialog.geometry("400x550")

        allowed_levels = PERMISSIONS.get(self.current_level, {}).get('can_add_users', [])
        if not allowed_levels:
            messagebox.showerror("Error", "You don't have permission to add users")
            dialog.destroy()
            return

        allowed_str = ", ".join([f"Level {l} ({SECURITY_LEVELS[l]})" for l in allowed_levels])
        tk.Label(dialog, text=f"You can add: {allowed_str}",
                fg="blue", font=("Segoe UI", 9, "italic")).grid(row=0, column=0, columnspan=2, pady=5)

        fields = [
            ("ID:", "display_id"),
            ("Username:", "username"),
            ("Password:", "password"),
            ("First Name:", "first_name"),
            ("Last Name:", "last_name"),
            ("Date of Birth (YYYY-MM-DD):", "dob"),
            ("Role:", "role")
        ]

        entries = {}
        for i, (label, key) in enumerate(fields, start=1):
            tk.Label(dialog, text=label).grid(row=i, column=0, padx=10, pady=5, sticky="e")
            entry = tk.Entry(dialog, width=30, show="*" if key == "password" else "")
            entry.grid(row=i, column=1, padx=10, pady=5)
            entries[key] = entry

        tk.Label(dialog, text="Security Level:").grid(row=len(fields)+1, column=0, padx=10, pady=5, sticky="e")
        level_var = tk.IntVar(value=allowed_levels[0])
        level_combo = ttk.Combobox(dialog, textvariable=level_var, values=allowed_levels, width=28, state="readonly")
        level_combo.grid(row=len(fields)+1, column=1, padx=10, pady=5)

        def save_user():
            try:
                user_data = {key: entry.get() for key, entry in entries.items()}
                user_data['security_level'] = level_var.get()

                if not self.can_add_user_level(user_data['security_level']):
                    messagebox.showerror(
                        "Access Denied",
                        f"You don't have permission to add Level {user_data['security_level']} users.\n\n"
                        f"You can only add: {allowed_str}"
                    )
                    return

                if not all([user_data['display_id'], user_data['username'], user_data['password']]):
                    messagebox.showerror("Error", "ID, username, and password are required")
                    return

                password_hash = bcrypt.hashpw(user_data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

                conn = sqlite3.connect(SECURITY_DB)
                cursor = conn.cursor()
                cursor.execute("SELECT user_id FROM Users WHERE display_id = ?", (user_data['display_id'],))
                if cursor.fetchone():
                    conn.close()
                    messagebox.showerror("Error", f"ID '{user_data['display_id']}' is already in use.")
                    return
                cursor.execute(
                    "INSERT INTO Users (display_id, username, password_hash, security_level, first_name, last_name, dob, role, access_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (user_data['display_id'], user_data['username'], password_hash, user_data['security_level'],
                     user_data['first_name'], user_data['last_name'], user_data['dob'],
                     user_data['role'], None)
                )
                conn.commit()
                conn.close()

                self.log_action("ADD_USER", f"Added user: {user_data['username']} (Level {user_data['security_level']})")
                messagebox.showinfo("Success", "User added successfully")
                dialog.destroy()
                self.show_user_management()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to add user: {e}")

        tk.Button(dialog, text="Save User", command=save_user, bg="#4CAF50", fg="white", width=20).grid(
            row=len(fields)+2, column=0, columnspan=2, pady=20
        )

    def remove_user_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Remove User")
        dialog.geometry("300x150")

        tk.Label(dialog, text="Enter username to remove:").pack(pady=20)
        username_entry = tk.Entry(dialog, width=30)
        username_entry.pack(pady=10)

        def delete_user():
            username = username_entry.get()
            if not username:
                messagebox.showerror("Error", "Username is required")
                return

            try:
                conn = sqlite3.connect(SECURITY_DB)
                cursor = conn.cursor()
                cursor.execute("SELECT security_level FROM Users WHERE username = ?", (username,))
                target_user = cursor.fetchone()

                if not target_user:
                    conn.close()
                    messagebox.showerror("Error", f"User '{username}' not found.")
                    return

                target_level = target_user[0]

                if not self.can_remove_user_level(target_level):
                    conn.close()
                    allowed_levels = PERMISSIONS.get(self.current_level, {}).get('can_remove_users', [])
                    allowed_str = ", ".join([f"Level {l}" for l in allowed_levels]) if allowed_levels else "none"
                    messagebox.showerror(
                        "Access Denied",
                        f"Level {self.current_level} ({SECURITY_LEVELS[self.current_level]}) cannot remove Level {target_level} users.\n\n"
                        f"You can only remove: {allowed_str}"
                    )
                    return

                if self.current_level == 4 and target_level == 5:
                    conn.close()
                    messagebox.showerror(
                        "Access Denied",
                        "Level 4 (Owner) cannot remove Level 5 (Police/Government) users.\n\n"
                        "Level 5 is immutable by owner.\n"
                        "Only Level 5 can manage Level 5 users."
                    )
                    return

                if target_level == 5:
                    cursor.execute("SELECT COUNT(*) FROM Users WHERE security_level = 5")
                    level5_count = cursor.fetchone()[0]

                    if level5_count <= 1:
                        conn.close()
                        messagebox.showerror(
                            "Access Denied",
                            "Cannot remove the last Level 5 (Police/Government) user.\n\n"
                            "At least one Level 5 user must exist in the system at all times."
                        )
                        return

                if messagebox.askyesno("Confirm", f"Are you sure you want to remove user '{username}'?"):
                    cursor.execute("DELETE FROM Users WHERE username = ?", (username,))
                    conn.commit()
                    conn.close()

                    self.log_action("REMOVE_USER", f"Removed user: {username} (Level {target_level})")
                    messagebox.showinfo("Success", f"User '{username}' removed successfully")
                    dialog.destroy()
                    self.show_user_management()
                else:
                    conn.close()

            except Exception as e:
                messagebox.showerror("Error", f"Failed to remove user: {e}")

        tk.Button(dialog, text="Remove User", command=delete_user, bg="#f44336", fg="white", width=20).pack(pady=10)

    def show_audit_logs(self):
        for widget in self.content_area.winfo_children():
            widget.destroy()

        tk.Label(self.content_area, text="Audit Logs (Immutable)",
                font=("Segoe UI", 18, "bold"), bg="white").pack(pady=20)

        list_frame = tk.Frame(self.content_area, bg="white")
        list_frame.pack(pady=10, padx=20, fill="both", expand=True)

        tree = ttk.Treeview(list_frame, columns=("Time", "User", "Action", "Details"), show="headings")
        tree.heading("Time", text="Timestamp")
        tree.heading("User", text="User ID")
        tree.heading("Action", text="Action")
        tree.heading("Details", text="Details")

        tree.column("Time", width=180)
        tree.column("User", width=80)
        tree.column("Action", width=150)
        tree.column("Details", width=300)

        try:
            conn = sqlite3.connect(LOGS_DB)
            cursor = conn.cursor()
            cursor.execute("SELECT timestamp, user_id, action, details FROM AuditLog ORDER BY timestamp DESC LIMIT 100")
            logs = cursor.fetchall()
            conn.close()

            for log in logs:
                tree.insert("", "end", values=log)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load logs: {e}")

        tree.pack(fill="both", expand=True)
        tk.Label(self.content_area, text="Note: Audit logs cannot be modified or deleted",
                fg="red", bg="white", font=("Segoe UI", 9, "italic")).pack(pady=5)

    def show_governance(self):
        for widget in self.content_area.winfo_children():
            widget.destroy()

        SecurityGovernance, _ = self._get_governance_api()
        tk.Label(self.content_area, text="Security Governance (Dual-Control)",
                font=("Segoe UI", 18, "bold"), bg="white").pack(pady=20)

        level5_count = SecurityGovernance.get_level5_count()
        count_text = f"Level 5 Users in System: {level5_count}"
        count_color = "#4CAF50" if level5_count >= 2 else "#ff6f00"
        tk.Label(self.content_area, text=count_text, bg="white", fg=count_color,
                font=("Segoe UI", 12, "bold")).pack(pady=10)

        if level5_count < 2:
            tk.Label(self.content_area, text="Minimum 2 Level 5 users required for removal",
                    bg="white", fg="red", font=("Segoe UI", 10, "italic")).pack(pady=5)

        if self.current_level == 4:
            self.show_owner_governance()
        elif self.current_level == 5:
            self.show_level5_governance()

    def show_owner_governance(self):
        SecurityGovernance, _ = self._get_governance_api()
        tk.Label(self.content_area, text="Owner Actions",
                font=("Segoe UI", 14, "bold"), bg="white").pack(pady=20)

        btn_frame = tk.Frame(self.content_area, bg="white")
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="Request Level 5 Removal", command=self.request_level5_removal,
                 bg="#FF9800", fg="white", width=25, height=2).pack(side="left", padx=10)

        tk.Label(self.content_area, text="Removal Requests Status",
                font=("Segoe UI", 12, "bold"), bg="white").pack(pady=20)

        list_frame = tk.Frame(self.content_area, bg="white")
        list_frame.pack(pady=10, padx=20, fill="both", expand=True)

        tree = ttk.Treeview(list_frame, columns=("ID", "User to Remove", "Status", "Reason", "Created"), show="headings")
        tree.heading("ID", text="Request ID")
        tree.heading("User to Remove", text="User to Remove")
        tree.heading("Status", text="Status")
        tree.heading("Reason", text="Reason")
        tree.heading("Created", text="Created")

        tree.column("ID", width=50)
        tree.column("User to Remove", width=150)
        tree.column("Status", width=100)
        tree.column("Reason", width=200)
        tree.column("Created", width=150)

        try:
            requests = SecurityGovernance.get_pending_removal_requests()
            for req in requests:
                tree.insert("", "end", values=(
                    req['request_id'],
                    req['user_to_remove_username'],
                    req['status'],
                    req['reason'] or "N/A",
                    req['created_date']
                ))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load removal requests: {e}")

        tree.pack(fill="both", expand=True)

    def show_level5_governance(self):
        SecurityGovernance, DualControlError = self._get_governance_api()
        tk.Label(self.content_area, text="Level 5 Authority Actions",
                font=("Segoe UI", 14, "bold"), bg="white").pack(pady=20)

        tk.Label(self.content_area, text="Pending Removal Requests Requiring Your Approval",
                font=("Segoe UI", 12, "bold"), bg="white").pack(pady=10)

        list_frame = tk.Frame(self.content_area, bg="white")
        list_frame.pack(pady=10, padx=20, fill="both", expand=True)

        tree = ttk.Treeview(list_frame, columns=("ID", "User to Remove", "Requested By", "Reason", "Created"), show="headings")
        tree.heading("ID", text="Request ID")
        tree.heading("User to Remove", text="User to Remove")
        tree.heading("Requested By", text="Requested By")
        tree.heading("Reason", text="Reason")
        tree.heading("Created", text="Created")

        tree.column("ID", width=50)
        tree.column("User to Remove", width=150)
        tree.column("Requested By", width=150)
        tree.column("Reason", width=200)
        tree.column("Created", width=150)

        try:
            requests = SecurityGovernance.get_pending_removal_requests()

            if not requests:
                tk.Label(self.content_area, text="No pending removal requests",
                        bg="white", fg="green", font=("Segoe UI", 10)).pack(pady=20)
            else:
                for req in requests:
                    tree.insert("", "end", values=(
                        req['request_id'],
                        req['user_to_remove_username'],
                        req['requested_by_username'],
                        req['reason'] or "N/A",
                        req['created_date']
                    ))

                tree.pack(fill="both", expand=True)

                btn_frame = tk.Frame(self.content_area, bg="white")
                btn_frame.pack(pady=20)

                def approve_selected():
                    selection = tree.selection()
                    if not selection:
                        messagebox.showwarning("Warning", "Please select a request to approve")
                        return

                    item = tree.item(selection[0])
                    request_id = item['values'][0]

                    if messagebox.askyesno("Confirm", f"Approve removal request #{request_id}?"):
                        try:
                            SecurityGovernance.approve_level5_removal(request_id, self.current_user['user_id'])
                            self.log_action("APPROVE_LEVEL5_REMOVAL", f"Approved removal request {request_id}")
                            messagebox.showinfo("Success", "Removal approved and executed")
                            self.show_governance()
                        except DualControlError as e:
                            messagebox.showerror("Error", str(e))

                def reject_selected():
                    selection = tree.selection()
                    if not selection:
                        messagebox.showwarning("Warning", "Please select a request to reject")
                        return

                    item = tree.item(selection[0])
                    request_id = item['values'][0]

                    if messagebox.askyesno("Confirm", f"Reject removal request #{request_id}?"):
                        try:
                            SecurityGovernance.reject_level5_removal(request_id, self.current_user['user_id'])
                            self.log_action("REJECT_LEVEL5_REMOVAL", f"Rejected removal request {request_id}")
                            messagebox.showinfo("Success", "Removal request rejected")
                            self.show_governance()
                        except DualControlError as e:
                            messagebox.showerror("Error", str(e))

                tk.Button(btn_frame, text="Approve Selected", command=approve_selected,
                         bg="#4CAF50", fg="white", width=20, height=2).pack(side="left", padx=10)
                tk.Button(btn_frame, text="Reject Selected", command=reject_selected,
                         bg="#f44336", fg="white", width=20, height=2).pack(side="left", padx=10)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load requests: {e}")

    def request_level5_removal(self):
        SecurityGovernance, DualControlError = self._get_governance_api()
        if SecurityGovernance.get_level5_count() < 2:
            messagebox.showerror("Error", "Cannot remove Level 5 user: only 1 Level 5 user exists. Minimum 2 required for removal.")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Request Level 5 User Removal")
        dialog.geometry("400x300")

        conn = sqlite3.connect(SECURITY_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, username, first_name, last_name FROM Users WHERE security_level = 5")
        level5_users = [dict(row) for row in cursor.fetchall()]
        conn.close()

        if not level5_users:
            messagebox.showerror("Error", "No Level 5 users found")
            dialog.destroy()
            return

        tk.Label(dialog, text="Select Level 5 User to Remove:").pack(pady=10)

        user_var = tk.StringVar()
        user_combo = ttk.Combobox(dialog, textvariable=user_var, width=40)
        user_combo['values'] = [f"{u['username']} - {u['first_name']} {u['last_name']}" for u in level5_users]
        user_combo.pack(pady=10)

        tk.Label(dialog, text="Reason for Removal:").pack(pady=10)
        reason_text = tk.Text(dialog, height=8, width=50)
        reason_text.pack(pady=10)

        def submit_request():
            if not user_var.get() or not reason_text.get("1.0", "end-1c"):
                messagebox.showerror("Error", "Please select a user and provide a reason")
                return

            selected_text = user_var.get()
            selected_user = next(u for u in level5_users if f"{u['username']} - {u['first_name']} {u['last_name']}" == selected_text)
            user_id = selected_user['user_id']
            reason = reason_text.get("1.0", "end-1c")

            try:
                request_id = SecurityGovernance.request_level5_removal(
                    self.current_user['user_id'],
                    user_id,
                    reason
                )
                messagebox.showinfo("Success", f"Removal request {request_id} created. Awaiting Level 5 approval.")
                dialog.destroy()
                self.show_governance()
            except DualControlError as e:
                messagebox.showerror("Error", str(e))

        tk.Button(dialog, text="Submit Request", command=submit_request,
                 bg="#FF9800", fg="white", width=20, height=2).pack(pady=20)

    def logout(self):
        self.log_action("LOGOUT", "User logged out")
        self.current_user = None
        self.current_level = None
        self.show_login()


if __name__ == "__main__":
    root = tk.Tk()
    app = FinanceSystem(root)
    root.mainloop()
