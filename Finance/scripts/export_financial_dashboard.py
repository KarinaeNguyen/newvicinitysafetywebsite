"""
Weekly Financial Dashboard Export Script
Exports financial data to HTML, JSON, and generates reports for GitHub Pages hosting
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import csv

def resolve_base_dir() -> Path:
    """Find the Finance base directory"""
    start_dir = Path(__file__).resolve().parent
    for candidate in [start_dir, *start_dir.parents]:
        if (candidate / "db").exists() and (candidate / "security").exists():
            return candidate
    return start_dir

BASE_DIR = resolve_base_dir()
DB_PATH = BASE_DIR / "db" / "FinancialDatabase.db"
EXPORT_DIR = BASE_DIR.parent / "financial-reports"  # Website root level

def get_db():
    """Connect to financial database"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_current_balance():
    """Get latest balance"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT amount FROM Balance ORDER BY balance_date DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 0.0

def get_sales_summary(days=30):
    """Get sales summary for last N days"""
    conn = get_db()
    cursor = conn.cursor()
    
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    
    cursor.execute(f"""
        SELECT 
            COUNT(*) as total_orders,
            SUM(units_sold) as total_units,
            SUM(gross_sales) as total_sales,
            SUM(vat_amount) as total_vat
        FROM Sales
        WHERE sale_date >= '{start_date}'
    """)
    
    row = cursor.fetchone()
    conn.close()
    
    return {
        'period_days': days,
        'total_orders': row[0] or 0,
        'total_units': row[1] or 0,
        'total_sales': float(row[2] or 0.0),
        'total_vat': float(row[3] or 0.0)
    }

def get_inventory_summary():
    """Get current inventory status"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            p.sku,
            p.name,
            COALESCE(SUM(s.unit_in), 0) as units_in_stock,
            p.unit_cost,
            COALESCE(SUM(s.unit_in), 0) * p.unit_cost as total_value
        FROM Products p
        LEFT JOIN Stock s ON p.sku = s.product_sku
        GROUP BY p.sku, p.name, p.unit_cost
        ORDER BY p.name
    """)
    
    inventory = []
    for row in cursor.fetchall():
        inventory.append({
            'sku': row[0],
            'name': row[1],
            'units': row[2],
            'unit_cost': float(row[3] or 0.0),
            'total_value': float(row[4] or 0.0)
        })
    
    conn.close()
    return inventory

def get_sales_by_product():
    """Get sales breakdown by product"""
    conn = get_db()
    cursor = conn.cursor()
    
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    cursor.execute(f"""
        SELECT 
            s.product_sku,
            p.name,
            SUM(s.units_sold) as units,
            SUM(s.gross_sales) as sales
        FROM Sales s
        LEFT JOIN Products p ON s.product_sku = p.sku
        WHERE s.sale_date >= '{start_date}'
        GROUP BY s.product_sku, p.name
        ORDER BY sales DESC
    """)
    
    sales = []
    for row in cursor.fetchall():
        sales.append({
            'sku': row[0],
            'name': row[1] or 'Unknown',
            'units': row[2] or 0,
            'sales': float(row[3] or 0.0)
        })
    
    conn.close()
    return sales

def generate_html_dashboard(export_date):
    """Generate HTML dashboard"""
    
    balance = get_current_balance()
    sales_30d = get_sales_summary(30)
    inventory = get_inventory_summary()
    top_products = get_sales_by_product()[:5]
    
    total_inventory_value = sum(item['total_value'] for item in inventory)
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Vicinity Safety - Financial Dashboard</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        
        .header {{
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }}
        
        .header h1 {{
            color: #333;
            margin-bottom: 10px;
        }}
        
        .last-updated {{
            color: #666;
            font-size: 14px;
        }}
        
        .metrics {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .metric-card {{
            background: white;
            padding: 25px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border-left: 4px solid #667eea;
        }}
        
        .metric-label {{
            color: #999;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 10px;
        }}
        
        .metric-value {{
            color: #333;
            font-size: 28px;
            font-weight: bold;
        }}
        
        .metric-change {{
            color: #999;
            font-size: 12px;
            margin-top: 8px;
        }}
        
        .section {{
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }}
        
        .section h2 {{
            color: #333;
            margin-bottom: 20px;
            font-size: 20px;
            border-bottom: 2px solid #f0f0f0;
            padding-bottom: 10px;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        th {{
            background: #f8f8f8;
            color: #666;
            padding: 12px;
            text-align: left;
            font-size: 12px;
            text-transform: uppercase;
            font-weight: 600;
            border-bottom: 2px solid #e0e0e0;
        }}
        
        td {{
            padding: 12px;
            border-bottom: 1px solid #f0f0f0;
            color: #333;
        }}
        
        tr:hover {{
            background: #fafafa;
        }}
        
        .currency {{
            font-family: 'Courier New', monospace;
            font-weight: 600;
        }}
        
        .positive {{
            color: #28a745;
        }}
        
        .negative {{
            color: #dc3545;
        }}
        
        .footer {{
            text-align: center;
            color: white;
            margin-top: 40px;
            font-size: 12px;
        }}
        
        @media (max-width: 600px) {{
            .metrics {{
                grid-template-columns: 1fr;
            }}
            
            .metric-value {{
                font-size: 22px;
            }}
            
            table {{
                font-size: 12px;
            }}
            
            th, td {{
                padding: 8px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Vicinity Safety - Financial Dashboard</h1>
            <div class="last-updated">Last updated: {export_date.strftime('%B %d, %Y at %H:%M UTC')}</div>
        </div>
        
        <div class="metrics">
            <div class="metric-card">
                <div class="metric-label">Current Balance</div>
                <div class="metric-value currency positive">£{balance:,.2f}</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">Sales (30 Days)</div>
                <div class="metric-value currency">£{sales_30d['total_sales']:,.2f}</div>
                <div class="metric-change">{sales_30d['total_orders']} orders</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">Inventory Value</div>
                <div class="metric-value currency">£{total_inventory_value:,.2f}</div>
                <div class="metric-change">{len(inventory)} products</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">30-Day VAT</div>
                <div class="metric-value currency">£{sales_30d['total_vat']:,.2f}</div>
            </div>
        </div>
        
        <div class="section">
            <h2>Top Selling Products (30 Days)</h2>
            <table>
                <thead>
                    <tr>
                        <th>Product</th>
                        <th>Units Sold</th>
                        <th>Revenue</th>
                    </tr>
                </thead>
                <tbody>
"""
    
    if top_products:
        for product in top_products:
            html += f"""                    <tr>
                        <td>{product['name']}</td>
                        <td>{product['units']}</td>
                        <td class="currency">£{product['sales']:,.2f}</td>
                    </tr>
"""
    else:
        html += """                    <tr>
                        <td colspan="3" style="text-align: center; color: #999;">No sales data available</td>
                    </tr>
"""
    
    html += """                </tbody>
            </table>
        </div>
        
        <div class="section">
            <h2>Current Inventory</h2>
            <table>
                <thead>
                    <tr>
                        <th>Product</th>
                        <th>SKU</th>
                        <th>Units</th>
                        <th>Unit Cost</th>
                        <th>Total Value</th>
                    </tr>
                </thead>
                <tbody>
"""
    
    if inventory:
        for item in inventory:
            html += f"""                    <tr>
                        <td>{item['name']}</td>
                        <td style="font-family: monospace;">{item['sku']}</td>
                        <td>{item['units']}</td>
                        <td class="currency">£{item['unit_cost']:,.2f}</td>
                        <td class="currency">£{item['total_value']:,.2f}</td>
                    </tr>
"""
    else:
        html += """                    <tr>
                        <td colspan="5" style="text-align: center; color: #999;">No inventory data available</td>
                    </tr>
"""
    
    html += """                </tbody>
            </table>
        </div>
        
        <div class="footer">
            <p>This is a static financial dashboard generated weekly from your Vicinity Safety database.</p>
            <p>Data is auto-updated and committed to GitHub Pages every 7 days.</p>
        </div>
    </div>
</body>
</html>
"""
    
    return html

def export_data_json():
    """Export all financial data to JSON"""
    data = {
        'export_date': datetime.now().isoformat(),
        'balance': get_current_balance(),
        'sales_30d': get_sales_summary(30),
        'sales_90d': get_sales_summary(90),
        'inventory': get_inventory_summary(),
        'top_products': get_sales_by_product()
    }
    return data

def main():
    """Main export function"""
    
    # Create export directory if it doesn't exist
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    
    export_date = datetime.now()
    
    # Generate HTML dashboard
    print(f"Generating HTML dashboard...")
    html_content = generate_html_dashboard(export_date)
    html_path = EXPORT_DIR / "index.html"
    
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"✓ HTML dashboard saved to: {html_path}")
    
    # Export JSON data
    print(f"Exporting JSON data...")
    json_data = export_data_json()
    json_path = EXPORT_DIR / "financial-data.json"
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, default=str)
    print(f"✓ JSON data saved to: {json_path}")
    
    print(f"\n✓ Export complete! Files are ready for GitHub commit.")
    print(f"  - Dashboard: {html_path}")
    print(f"  - Data: {json_path}")

if __name__ == "__main__":
    main()
