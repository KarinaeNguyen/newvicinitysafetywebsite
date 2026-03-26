"""Interactive terminal menu system for accounting."""

from typing import Optional, List, Dict, Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.align import Align
import csv
import json
from datetime import datetime

from core.db import init_db, get_session
from core.services import LogService, ServiceError
from core.validate import ValidationError
from core.queries import DashboardQueries
from core.models import LogEntry, Product, ProductMovement
from sqlalchemy import desc

console = Console()


class MenuSystem:
    """Interactive terminal menu system."""

    def __init__(self):
        self.session = get_session()
        self.queries = DashboardQueries(self.session)
        self.service = LogService(self.session)

    def main_menu(self):
        """Main menu loop."""
        init_db()
        
        while True:
            console.clear()
            console.print(Panel.fit(
                "[bold cyan]📊 Accounting & Inventory System[/bold cyan]",
                border_style="cyan"
            ))
            
            console.print("\n[bold]Main Menu[/bold]\n")
            options = [
                ("1", "📝 Add New Log Entry"),
                ("2", "📦 Products"),
                ("3", "➕ Add Product"),
                ("4", "� Record Purchase (Inventory In)"),
                ("5", "📊 View Sales"),
                ("6", "🔍 Search"),
                ("7", "📤 Export Data"),
                ("8", "📥 Import Data (CSV)"),
                ("9", "📈 Reports"),
                ("s", "⚙️  Settings"),
                ("0", "❌ Exit"),
            ]
            
            for key, label in options:
                console.print(f"  {key}. {label}")
            
            choice = console.input("\n[bold cyan]→[/bold cyan] Select option: ").strip()
            
            if choice == "1":
                self.add_log_menu()
            elif choice == "2":
                self.view_products_menu()
            elif choice == "3":
                self.add_product()
            elif choice == "4":
                self.record_purchase()
            elif choice == "5":
                self.view_sales_menu()
            elif choice == "6":
                self.search_menu()
            elif choice == "7":
                self.export_menu()
            elif choice == "8":
                self.import_menu()
            elif choice == "9":
                self.reports_menu()
            elif choice == "s" or choice == "S":
                self.settings_menu()
            elif choice == "0":
                console.print("[yellow]Goodbye![/yellow]")
                break
            else:
                console.print("[red]Invalid option[/red]")
                console.input("Press Enter to continue...")

    def add_log_menu(self):
        """Add new log entry interactive form."""
        console.clear()
        console.print("[bold]➕ Add New Log Entry[/bold]\n")
        
        payload = {}
        
        # Phase 1: Reference & Date
        console.print("[bold cyan]Phase 1: Reference & Date[/bold cyan]")
        ref_no = Prompt.ask("Reference No", default="")
        if ref_no:
            payload["ref_no"] = ref_no
        
        date_str = Prompt.ask("Date (YYYY-MM-DD)", default="")
        if date_str:
            payload["date"] = date_str
        
        # Phase 2: Product
        console.print("\n[bold cyan]Phase 2: Product[/bold cyan]")
        sku = Prompt.ask("SKU", default="")
        if sku:
            payload["sku"] = sku
        
        barcode = Prompt.ask("Barcode (optional)", default="")
        if barcode:
            payload["barcode"] = barcode
        
        name = Prompt.ask("Product Name (optional)", default="")
        if name:
            payload["name"] = name
        
        qty_str = Prompt.ask("Quantity (optional)", default="")
        if qty_str:
            payload["qty"] = qty_str
        
        qty_delta_str = Prompt.ask("Qty Delta (optional)", default="")
        if qty_delta_str:
            payload["qty_delta"] = qty_delta_str
        
        # Phase 3: Pricing
        console.print("\n[bold cyan]Phase 3: Pricing[/bold cyan]")
        console.print("[yellow]Note: Unit Cost is REQUIRED for purchases (inventory in)[/yellow]")
        unit_cost_str = Prompt.ask("Unit Cost (required for purchases)", default="")
        if unit_cost_str:
            payload["unit_cost"] = unit_cost_str
        
        unit_price_str = Prompt.ask("Unit Price (selling price, optional)", default="")
        if unit_price_str:
            payload["unit_price"] = unit_price_str
        
        amount_str = Prompt.ask("Amount (total, optional)", default="")
        if amount_str:
            payload["amount"] = amount_str
        
        # Phase 4: Party
        console.print("\n[bold cyan]Phase 4: Party[/bold cyan]")
        customer = Prompt.ask("Customer (optional)", default="")
        if customer:
            payload["customer"] = customer
        
        vendor = Prompt.ask("Vendor (optional)", default="")
        if vendor:
            payload["vendor"] = vendor
        
        # Phase 5: Additional
        console.print("\n[bold cyan]Phase 5: Additional[/bold cyan]")
        notes = Prompt.ask("Notes (optional)", default="")
        if notes:
            payload["notes"] = notes
        
        category = Prompt.ask("Category (optional)", default="")
        if category:
            payload["category"] = category
        
        # Insert
        try:
            log, detection = self.service.insert_log(payload)
            console.print(f"\n[green]✓ Log created (ID: {log.id})[/green]")
            console.print(f"  Type: [bold]{detection.log_type}[/bold]")
            console.print(f"  Confidence: {detection.confidence}")
        except (ValidationError, ServiceError) as e:
            console.print(f"[red]Error: {e}[/red]")
        
        console.input("\nPress Enter to continue...")

    def view_products_menu(self):
        """View and manage products."""
        console.clear()
        
        while True:
            products = self.queries.get_all_products()
            
            if not products:
                console.print("[yellow]No products found[/yellow]")
            else:
                # Show table
                table = Table(title="Products", show_header=True, header_style="bold cyan")
                table.add_column("SKU", style="cyan")
                table.add_column("Name", style="magenta")
                table.add_column("On Hand", justify="right")
                table.add_column("Avg Cost", justify="right", style="yellow")
                table.add_column("Unit Price", justify="right", style="green")
                table.add_column("Margin", justify="right")
                table.add_column("Value", justify="right")
                
                for p in products[:50]:  # Limit to 50 for display
                    value = (p["on_hand"] or 0) * (p["unit_price"] or 0)
                    cost = p["unit_cost"] or 0
                    price = p["unit_price"] or 0
                    margin = ""
                    if cost > 0 and price > 0:
                        margin_pct = ((price - cost) / price) * 100
                        margin = f"{margin_pct:.1f}%"
                    
                    table.add_row(
                        p["sku"],
                        p["name"] or "",
                        str(p["on_hand"]),
                        f"${cost:.2f}" if cost else "",
                        f"${price:.2f}" if price else "",
                        margin,
                        f"${value:.2f}"
                    )
                
                console.print(table)
            
            # Menu
            console.print("\n[bold]Options:[/bold]")
            console.print("  1. View movements for SKU")
            console.print("  2. Edit product")
            console.print("  3. Add product")
            console.print("  4. Remove product")
            console.print("  0. Back")
            
            choice = console.input("\n[bold cyan]→[/bold cyan] Select: ").strip()
            
            if choice == "1":
                sku = Prompt.ask("Enter SKU")
                self.view_movements(sku)
            elif choice == "2":
                self.edit_product()
            elif choice == "3":
                self.add_product()
            elif choice == "4":
                self.remove_product()
            elif choice == "0":
                break
            else:
                console.print("[red]Invalid option[/red]")

    def view_sales_menu(self):
        """View sales transactions."""
        console.clear()
        console.print("[bold]📊 Sales Transactions[/bold]\n")
        
        sales = self.queries.get_sales_summary(limit=50)
        
        if not sales:
            console.print("[yellow]No sales found[/yellow]")
            console.input("Press Enter to continue...")
            return
        
        table = Table(title="Recent Sales", show_header=True, header_style="bold cyan")
        table.add_column("ID", justify="right")
        table.add_column("Date", style="cyan")
        table.add_column("SKU", style="magenta")
        table.add_column("Qty", justify="right")
        table.add_column("Amount", justify="right")
        table.add_column("Customer")
        
        for s in sales:
            table.add_row(
                str(s["id"]),
                s["created_at"][:10],
                s["sku"] or "",
                str(s["qty"]) if s["qty"] else "",
                f"${s['amount']:.2f}" if s["amount"] else "",
                s["customer"] or ""
            )
        
        console.print(table)
        console.input("\nPress Enter to continue...")

    def search_menu(self):
        """Search logs and products."""
        console.clear()
        console.print("[bold]🔍 Search[/bold]\n")
        
        console.print("1. Search by SKU")
        console.print("2. Search by customer/vendor")
        console.print("3. Search by reference")
        console.print("4. Search by date range")
        console.print("0. Back\n")
        
        choice = console.input("[bold cyan]→[/bold cyan] Select: ").strip()
        
        if choice == "1":
            self.search_sku()
        elif choice == "2":
            self.search_party()
        elif choice == "3":
            self.search_reference()
        elif choice == "4":
            self.search_date_range()

    def search_sku(self):
        """Search by SKU."""
        sku = Prompt.ask("Enter SKU").strip().upper()
        
        products = self.session.query(Product).filter(
            Product.sku.ilike(f"%{sku}%")
        ).all()
        
        if not products:
            console.print(f"[yellow]No products found with SKU: {sku}[/yellow]")
        else:
            for p in products:
                console.print(f"\n[bold]{p.sku}[/bold]")
                console.print(f"  Name: {p.name}")
                console.print(f"  On Hand: {p.on_hand}")
                console.print(f"  Unit Price: ${p.unit_price or 0:.2f}")
        
        console.input("\nPress Enter to continue...")

    def search_party(self):
        """Search by customer/vendor."""
        party = Prompt.ask("Enter customer/vendor name").strip()
        
        logs = self.session.query(LogEntry).filter(
            LogEntry.counterparty.ilike(f"%{party}%")
        ).order_by(desc(LogEntry.created_at)).limit(20).all()
        
        if not logs:
            console.print(f"[yellow]No transactions found for: {party}[/yellow]")
        else:
            table = Table(title=f"Transactions: {party}")
            table.add_column("ID", justify="right")
            table.add_column("Date")
            table.add_column("Type")
            table.add_column("Ref No")
            
            for log in logs:
                table.add_row(
                    str(log.id),
                    log.created_at[:10],
                    log.log_type,
                    log.ref_no or ""
                )
            
            console.print(table)
        
        console.input("\nPress Enter to continue...")

    def search_reference(self):
        """Search by reference."""
        ref = Prompt.ask("Enter reference number").strip()
        
        logs = self.session.query(LogEntry).filter(
            LogEntry.ref_no.ilike(f"%{ref}%")
        ).all()
        
        if not logs:
            console.print(f"[yellow]No logs found with ref: {ref}[/yellow]")
        else:
            for log in logs:
                console.print(f"\n[bold]ID {log.id}[/bold] - {log.ref_no}")
                console.print(f"  Type: {log.log_type}")
                console.print(f"  Date: {log.created_at}")
                console.print(f"  Notes: {log.notes}")
        
        console.input("\nPress Enter to continue...")

    def search_date_range(self):
        """Search by date range."""
        start_date = Prompt.ask("Start date (YYYY-MM-DD)").strip()
        end_date = Prompt.ask("End date (YYYY-MM-DD)").strip()
        
        logs = self.session.query(LogEntry).filter(
            LogEntry.created_at >= start_date,
            LogEntry.created_at <= end_date
        ).order_by(desc(LogEntry.created_at)).limit(50).all()
        
        if not logs:
            console.print("[yellow]No logs found in date range[/yellow]")
        else:
            table = Table(title=f"Logs: {start_date} to {end_date}")
            table.add_column("ID", justify="right")
            table.add_column("Date")
            table.add_column("Type")
            table.add_column("Party")
            table.add_column("Ref No")
            
            for log in logs:
                table.add_row(
                    str(log.id),
                    log.created_at[:10],
                    log.log_type,
                    log.counterparty or "",
                    log.ref_no or ""
                )
            
            console.print(table)
        
        console.input("\nPress Enter to continue...")

    def export_menu(self):
        """Export data to CSV or JSON."""
        console.clear()
        console.print("[bold]📤 Export Data[/bold]\n")
        
        console.print("1. Export all products")
        console.print("2. Export all logs")
        console.print("3. Export sales only")
        console.print("4. Export purchases only")
        console.print("0. Back\n")
        
        choice = console.input("[bold cyan]→[/bold cyan] Select: ").strip()
        
        if choice == "1":
            self.export_products()
        elif choice == "2":
            self.export_logs()
        elif choice == "3":
            self.export_sales()
        elif choice == "4":
            self.export_purchases()

    def export_products(self):
        """Export products to CSV."""
        filename = f"products_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        products = self.queries.get_all_products()
        
        with open(filename, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["sku", "barcode", "name", "unit_cost", "unit_price", "on_hand", "updated_at"])
            writer.writeheader()
            writer.writerows(products)
        
        console.print(f"[green]✓ Exported to {filename}[/green]")
        console.input("Press Enter to continue...")

    def export_logs(self):
        """Export all logs to CSV."""
        filename = f"logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        logs = self.session.query(LogEntry).order_by(desc(LogEntry.created_at)).all()
        
        with open(filename, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["id", "created_at", "log_type", "ref_no", "counterparty", "notes"])
            writer.writeheader()
            for log in logs:
                writer.writerow({
                    "id": log.id,
                    "created_at": log.created_at,
                    "log_type": log.log_type,
                    "ref_no": log.ref_no,
                    "counterparty": log.counterparty,
                    "notes": log.notes
                })
        
        console.print(f"[green]✓ Exported to {filename}[/green]")
        console.input("Press Enter to continue...")

    def export_sales(self):
        """Export sales to CSV."""
        filename = f"sales_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        sales = self.queries.get_sales_summary(limit=1000)
        
        with open(filename, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["id", "created_at", "sku", "qty", "amount", "customer"])
            writer.writeheader()
            writer.writerows(sales)
        
        console.print(f"[green]✓ Exported to {filename}[/green]")
        console.input("Press Enter to continue...")

    def export_purchases(self):
        """Export purchases to CSV."""
        filename = f"purchases_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        logs = self.session.query(LogEntry).filter_by(log_type="PURCHASE").order_by(desc(LogEntry.created_at)).limit(1000).all()
        
        with open(filename, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["id", "created_at", "sku", "qty", "vendor", "ref_no"])
            writer.writeheader()
            for log in logs:
                payload = json.loads(log.payload_json)
                writer.writerow({
                    "id": log.id,
                    "created_at": log.created_at,
                    "sku": payload.get("sku"),
                    "qty": payload.get("qty"),
                    "vendor": log.counterparty,
                    "ref_no": log.ref_no
                })
        
        console.print(f"[green]✓ Exported to {filename}[/green]")
        console.input("Press Enter to continue...")

    def import_menu(self):
        """Import data from CSV."""
        console.clear()
        console.print("[bold]📥 Import Data[/bold]\n")
        
        filename = Prompt.ask("Enter CSV filename")
        
        try:
            with open(filename, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                count = 0
                
                for row in reader:
                    try:
                        self.service.insert_log(row)
                        count += 1
                    except (ValidationError, ServiceError) as e:
                        console.print(f"[yellow]Row {count + 1}: {e}[/yellow]")
                
                console.print(f"[green]✓ Imported {count} rows[/green]")
        except FileNotFoundError:
            console.print(f"[red]File not found: {filename}[/red]")
        
        console.input("Press Enter to continue...")

    def reports_menu(self):
        """Reports and analytics."""
        console.clear()
        console.print("[bold]📈 Reports[/bold]\n")
        
        kpis = self.queries.get_kpis()
        
        # KPI Summary
        table = Table(title="Summary KPIs", show_header=False)
        table.add_row("Total Products", str(kpis["total_products"]))
        table.add_row("Total Units", str(kpis["total_units_on_hand"]))
        table.add_row("Inventory Value", f"${kpis['inventory_value']:,.2f}")
        table.add_row("Total Logs", str(kpis["total_logs"]))
        
        console.print(table)
        
        # Low stock
        console.print("\n[bold]Low Stock Alert[/bold]")
        low_stock = self.queries.get_low_stock_products(threshold=10)
        
        if low_stock:
            table = Table(title="Products Below 10 Units")
            table.add_column("SKU")
            table.add_column("On Hand", justify="right")
            table.add_column("Unit Price", justify="right")
            
            for p in low_stock:
                table.add_row(
                    p["sku"],
                    str(p["on_hand"]),
                    f"${p['unit_price']:.2f}" if p["unit_price"] else ""
                )
            
            console.print(table)
        else:
            console.print("[green]✓ All products well-stocked[/green]")
        
        console.input("\nPress Enter to continue...")

    def settings_menu(self):
        """Settings and configuration."""
        console.clear()
        console.print("[bold]⚙️  Settings[/bold]\n")
        
        console.print("1. View database path")
        console.print("2. View config")
        console.print("3. Reinitialize database")
        console.print("0. Back\n")
        
        choice = console.input("[bold cyan]→[/bold cyan] Select: ").strip()
        
        if choice == "1":
            import os
            db_path = os.getenv("ACCOUNTING_DB_PATH", "accounting.db")
            console.print(f"\n[cyan]Database: {db_path}[/cyan]")
        elif choice == "2":
            from core.config import get_config
            config = get_config()
            console.print(f"\n[cyan]Log Types: {', '.join(config.get_log_types())}[/cyan]")
        elif choice == "3":
            if Confirm.ask("Reinitialize database? (All data will be cleared)"):
                init_db()
                console.print("[green]✓ Database reinitialized[/green]")
        
        console.input("\nPress Enter to continue...")

    def view_movements(self, sku: str):
        """View inventory movements for a SKU."""
        console.clear()
        console.print(f"[bold]Movements for {sku}[/bold]\n")
        
        movements = self.queries.get_movement_history(sku, limit=50)
        
        if not movements:
            console.print("[yellow]No movements found[/yellow]")
        else:
            table = Table(title=f"Movement History: {sku}")
            table.add_column("ID", justify="right")
            table.add_column("Date")
            table.add_column("Qty Delta", justify="right")
            table.add_column("Unit Price", justify="right")
            
            for m in movements:
                qty_style = "green" if m["qty_delta"] > 0 else "red"
                table.add_row(
                    str(m["id"]),
                    m["created_at"][:10],
                    f"[{qty_style}]{m['qty_delta']:+d}[/{qty_style}]",
                    f"${m['unit_price']:.2f}" if m["unit_price"] else ""
                )
            
            console.print(table)
        
        console.input("\nPress Enter to continue...")

    def add_product(self):
        """Add a product via PRODUCT_UPDATE log."""
        console.clear()
        console.print("[bold]➕ Add Product[/bold]\n")

        sku = Prompt.ask("SKU").strip().upper()
        name = Prompt.ask("Product Name (optional)", default="")
        barcode = Prompt.ask("Barcode (optional)", default="")
        unit_cost = Prompt.ask("Unit Cost (optional)", default="")
        unit_price = Prompt.ask("Unit Price (optional)", default="")

        payload = {
            "sku": sku,
            "name": name or None,
            "barcode": barcode or None,
            "unit_cost": unit_cost or None,
            "unit_price": unit_price or None,
        }

        try:
            log, detection = self.service.insert_log(payload, force_log_type="PRODUCT_UPDATE")
            console.print(f"\n[green]✓ Product created (Log ID: {log.id})[/green]")
        except (ValidationError, ServiceError) as e:
            console.print(f"[red]Error: {e}[/red]")

        console.input("\nPress Enter to continue...")

    def record_purchase(self):
        """Record a purchase (inventory in) - requires unit cost."""
        console.clear()
        console.print("[bold]📥 Record Purchase (Inventory In)[/bold]\n")
        console.print("[cyan]This will add units to inventory and update average cost.[/cyan]\n")

        ref_no = Prompt.ask("Reference/PO Number (optional)", default="")
        date_str = Prompt.ask("Date (YYYY-MM-DD, or leave blank for today)", default="")
        sku = Prompt.ask("SKU").strip().upper()
        qty = Prompt.ask("Quantity")
        
        console.print("\n[yellow]⚠️  Unit Cost is REQUIRED for purchases[/yellow]")
        console.print("[dim]This cost will be used to calculate weighted average cost[/dim]")
        unit_cost = Prompt.ask("Unit Cost (per unit)")
        
        vendor = Prompt.ask("Vendor/Supplier (optional)", default="")
        notes = Prompt.ask("Notes (optional)", default="")

        payload = {
            "sku": sku,
            "qty": qty,
            "unit_cost": unit_cost,
            "vendor": vendor or None,
            "ref_no": ref_no or None,
            "date": date_str or None,
            "notes": notes or None,
        }

        try:
            log, detection = self.service.insert_log(payload, force_log_type="PURCHASE")
            console.print(f"\n[green]✓ Purchase recorded (Log ID: {log.id})[/green]")
            console.print(f"  SKU: {sku}")
            console.print(f"  Quantity: +{qty}")
            console.print(f"  Unit Cost: {unit_cost}")
            
            # Show updated product info
            product = self.session.query(Product).filter_by(sku=sku).first()
            if product:
                console.print(f"\n[cyan]Updated Product Info:[/cyan]")
                console.print(f"  On Hand: {product.on_hand}")
                console.print(f"  Avg Cost: {product.unit_cost:.2f}" if product.unit_cost else "  Avg Cost: N/A")
        except (ValidationError, ServiceError) as e:
            console.print(f"[red]Error: {e}[/red]")

        console.input("\nPress Enter to continue...")

    def remove_product(self):
        """Remove a product and its movements (logs remain)."""
        console.clear()
        console.print("[bold]🗑️  Remove Product[/bold]\n")

        sku = Prompt.ask("Enter SKU to remove").strip().upper()
        product = self.session.query(Product).filter_by(sku=sku).first()

        if not product:
            console.print("[yellow]Product not found[/yellow]")
            console.input("\nPress Enter to continue...")
            return

        confirm = Confirm.ask(
            f"This will delete product {sku} and its movement history. Continue?"
        )
        if not confirm:
            return

        self.session.query(ProductMovement).filter_by(sku=sku).delete()
        self.session.delete(product)
        self.session.commit()
        console.print(f"[green]✓ Product {sku} removed[/green]")
        console.input("\nPress Enter to continue...")

    def edit_product(self):
        """Edit a product."""
        sku = Prompt.ask("Enter SKU to edit").strip().upper()
        
        product = self.session.query(Product).filter_by(sku=sku).first()
        
        if not product:
            console.print("[red]Product not found[/red]")
            return
        
        console.print(f"\n[bold]Editing {sku}[/bold]")
        console.print(f"  Name: {product.name}")
        console.print(f"  Unit Price: ${product.unit_price or 0:.2f}")
        console.print(f"  On Hand: {product.on_hand}")
        
        name = Prompt.ask("New name (press Enter to skip)", default="")
        if name:
            product.name = name
        
        price_str = Prompt.ask("New unit price (press Enter to skip)", default="")
        if price_str:
            try:
                product.unit_price = float(price_str)
            except ValueError:
                console.print("[red]Invalid price[/red]")
        
        self.session.commit()
        console.print("[green]✓ Product updated[/green]")
        console.input("Press Enter to continue...")
