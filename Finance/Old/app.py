"""CLI interface for logging and database management."""

import typer
import json
from typing import Optional
from rich.console import Console
from rich.table import Table

from core.db import init_db, get_session
from core.services import LogService, ServiceError
from core.validate import ValidationError
from core.config import get_config
from core.queries import DashboardQueries

app = typer.Typer(help="Accounting & Inventory Log System")
console = Console()


@app.command()
def init():
    """Initialize database tables."""
    try:
        init_db()
        console.print("[green]✓[/green] Database initialized successfully")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def add(force_type: Optional[str] = typer.Option(None, help="Skip detection and force this log type")):
    """Add a new log entry interactively."""
    
    config = get_config()
    session = get_session()
    service = LogService(session)
    
    try:
        payload = {}
        
        # Phase 1: Common fields
        console.print("\n[bold]Common Fields[/bold]")
        
        ref_no = typer.prompt("Reference No", default="", show_default=False)
        if ref_no:
            payload["ref_no"] = ref_no
        
        date_str = typer.prompt("Date (YYYY-MM-DD)", default="", show_default=False)
        if date_str:
            payload["date"] = date_str
        
        # Phase 2: Product/inventory fields
        console.print("\n[bold]Product/Inventory Fields[/bold]")
        
        sku = typer.prompt("SKU", default="", show_default=False)
        if sku:
            payload["sku"] = sku
        
        barcode = typer.prompt("Barcode (optional)", default="", show_default=False)
        if barcode:
            payload["barcode"] = barcode
        
        name = typer.prompt("Product Name (optional)", default="", show_default=False)
        if name:
            payload["name"] = name
        
        qty_str = typer.prompt("Quantity (optional)", default="", show_default=False)
        if qty_str:
            payload["qty"] = qty_str
        
        qty_delta_str = typer.prompt("Qty Delta / Adjustment (optional)", default="", show_default=False)
        if qty_delta_str:
            payload["qty_delta"] = qty_delta_str
        
        unit_count_str = typer.prompt("Unit Count (optional)", default="", show_default=False)
        if unit_count_str:
            payload["unit_count"] = unit_count_str
        
        # Phase 3: Pricing fields
        console.print("\n[bold]Pricing Fields[/bold]")
        
        unit_cost_str = typer.prompt("Unit Cost (optional)", default="", show_default=False)
        if unit_cost_str:
            payload["unit_cost"] = unit_cost_str
        
        unit_price_str = typer.prompt("Unit Price (optional)", default="", show_default=False)
        if unit_price_str:
            payload["unit_price"] = unit_price_str
        
        amount_str = typer.prompt("Amount (optional)", default="", show_default=False)
        if amount_str:
            payload["amount"] = amount_str
        
        # Phase 4: Party & transaction fields
        console.print("\n[bold]Party & Transaction[/bold]")
        
        customer = typer.prompt("Customer (optional)", default="", show_default=False)
        if customer:
            payload["customer"] = customer
        
        vendor = typer.prompt("Vendor (optional)", default="", show_default=False)
        if vendor:
            payload["vendor"] = vendor
        
        payment_method = typer.prompt("Payment Method (optional)", default="", show_default=False)
        if payment_method:
            payload["payment_method"] = payment_method
        
        # Phase 5: Additional fields
        console.print("\n[bold]Additional[/bold]")
        
        category = typer.prompt("Category (optional)", default="", show_default=False)
        if category:
            payload["category"] = category
        
        reason = typer.prompt("Reason (optional)", default="", show_default=False)
        if reason:
            payload["reason"] = reason
        
        discount_str = typer.prompt("Discount (optional)", default="", show_default=False)
        if discount_str:
            payload["discount"] = discount_str
        
        tax_str = typer.prompt("Tax (optional)", default="", show_default=False)
        if tax_str:
            payload["tax"] = tax_str
        
        shipping_str = typer.prompt("Shipping (optional)", default="", show_default=False)
        if shipping_str:
            payload["shipping"] = shipping_str
        
        notes = typer.prompt("Notes (optional)", default="", show_default=False)
        if notes:
            payload["notes"] = notes
        
        # Insert log
        log_entry, detection = service.insert_log(payload, force_log_type=force_type)
        
        console.print(f"\n[green]✓ Log entry created (ID: {log_entry.id})[/green]")
        console.print(f"  Type: [bold]{detection.log_type}[/bold]")
        console.print(f"  Confidence: {detection.confidence}")
        
        if detection.confidence == "low":
            console.print(f"  All scores: {detection.candidate_scores}")
        
        session.close()
    
    except ValidationError as e:
        console.print(f"[red]Validation Error: {e}[/red]")
        raise typer.Exit(1)
    except ServiceError as e:
        console.print(f"[red]Service Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def show_products():
    """Show all products in inventory."""
    session = get_session()
    queries = DashboardQueries(session)
    
    products = queries.get_all_products()
    
    table = Table(title="Products")
    table.add_column("SKU", style="cyan")
    table.add_column("Name", style="magenta")
    table.add_column("On Hand", justify="right")
    table.add_column("Avg Cost", justify="right", style="yellow")
    table.add_column("Unit Price", justify="right", style="green")
    table.add_column("Margin", justify="right")
    table.add_column("Total Value", justify="right")
    
    for p in products:
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
    session.close()


@app.command()
def show_kpis():
    """Show KPI summary."""
    session = get_session()
    queries = DashboardQueries(session)
    
    kpis = queries.get_kpis()
    
    table = Table(title="KPIs")
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    
    table.add_row("Total Products", str(kpis["total_products"]))
    table.add_row("Units on Hand", str(kpis["total_units_on_hand"]))
    table.add_row("Inventory Value", f"${kpis['inventory_value']:.2f}")
    table.add_row("Total Logs", str(kpis["total_logs"]))
    
    console.print(table)
    session.close()


@app.command()
def show_recent():
    """Show recent log entries."""
    session = get_session()
    queries = DashboardQueries(session)
    
    logs = queries.get_recent_logs(limit=20)
    
    table = Table(title="Recent Logs")
    table.add_column("ID", justify="right")
    table.add_column("Type", style="cyan")
    table.add_column("Created", style="magenta")
    table.add_column("Ref No")
    table.add_column("Party")
    
    for log in logs:
        table.add_row(
            str(log["id"]),
            log["log_type"],
            log["created_at"][:10],  # Date only
            log["ref_no"] or "",
            log["counterparty"] or ""
        )
    
    console.print(table)
    session.close()


@app.command()
def menu():
    """🎯 Interactive menu system (recommended)."""
    from cli_menu import MenuSystem
    menu_sys = MenuSystem()
    menu_sys.main_menu()


if __name__ == "__main__":
    app()
