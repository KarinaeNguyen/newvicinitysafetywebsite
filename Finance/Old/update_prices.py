"""Update product prices from sales history."""

import json
from core.db import get_session
from core.models import LogEntry, Product

session = get_session()

# Get all SALES logs
sales_logs = session.query(LogEntry).filter_by(log_type="SALES").all()

updated = 0
for log in sales_logs:
    payload = json.loads(log.payload_json)
    sku = payload.get("sku")
    unit_price = payload.get("unit_price")
    
    if sku and unit_price:
        product = session.query(Product).filter_by(sku=sku).first()
        if product:
            product.unit_price = unit_price
            updated += 1

session.commit()
print(f"✓ Updated {updated} product prices from sales history")

# Show updated products
products = session.query(Product).all()
print("\nUpdated Products:")
for p in products:
    cost = p.unit_cost if p.unit_cost else 0
    price = p.unit_price if p.unit_price else 0
    print(f"  {p.sku}: ${price:.2f} (On hand: {p.on_hand}, Avg cost: ${cost:.2f})")

session.close()
