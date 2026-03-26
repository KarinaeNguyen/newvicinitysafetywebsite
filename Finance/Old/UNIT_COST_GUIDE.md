# Unit Cost Tracking - How It Works

## ✅ Fixed: Unit Cost is No Longer Fixed!

### What Changed:
- **Before:** Unit cost was static per product
- **Now:** Unit cost is **required for every purchase** and automatically calculates **weighted average**

---

## 📥 Recording Purchases (Inventory In)

### Use Option 4: "Record Purchase"

```
python app.py menu
→ Choose: 4. Record Purchase (Inventory In)
```

**You will be prompted for:**
1. Reference/PO Number (optional)
2. Date (optional, defaults to today)
3. **SKU** (required)
4. **Quantity** (required)
5. **Unit Cost** (REQUIRED - the cost you paid for this batch)
6. Vendor/Supplier (optional)
7. Notes (optional)

---

## 🧮 Weighted Average Cost Calculation

Every time you purchase, the system calculates:

```
New Avg Cost = (Old Quantity × Old Avg Cost + New Quantity × New Unit Cost) / Total Quantity
```

### Example: HM2SA-1W

**Starting:** Empty inventory

**Purchase 1:** 16 units @ 487,500 VND
- On hand: 16
- Avg cost: **487,500**

**Purchase 2:** 6 units @ 562,500 VND
- On hand: 22
- Avg cost: (16 × 487,500 + 6 × 562,500) / 22 = **506,818**

**Purchase 3:** 1 unit @ 562,500 VND
- On hand: 23
- Avg cost: (22 × 506,818 + 1 × 562,500) / 23 = **509,241**

**Sales:** -20 units
- On hand: 3
- Avg cost: **509,241** (stays the same - sales don't change avg cost)

---

## 📊 Why Weighted Average?

### Benefits:
- ✅ **Accurate COGS** — Know your true cost per unit
- ✅ **Profit tracking** — Calculate actual profit per sale
- ✅ **Price inflation** — Handles changing supplier prices
- ✅ **Audit trail** — Every purchase cost is logged

### Example Profit Calculation:
```
Sale: 1 unit @ 750,000 VND
Avg Cost: 509,241 VND
Profit: 750,000 - 509,241 = 240,759 VND
Margin: 32%
```

---

## 🔍 Viewing Cost History

### See all movements for a product:

```
python app.py menu
→ Choose: 2. Products
→ Choose: 1. View movements for SKU
→ Enter: HM2SA-1W
```

You'll see:
- Date of each transaction
- Qty delta (+purchases, -sales)
- Unit cost for that specific purchase
- Running total

---

## ⚠️ Important Notes

### 1. Unit Cost is REQUIRED for Purchases
If you forget to enter unit cost, you'll get an error:
```
Error: PURCHASE requires unit_cost (must be > 0)
```

### 2. Sales Don't Need Unit Cost
Sales use the **unit_price** (selling price), not unit cost.

### 3. Average Cost Updates Automatically
You don't calculate anything manually - the system does it!

### 4. Historical Data is Preserved
- Old purchases retain their original cost in `product_movements`
- Product table shows current **weighted average**

---

## 📋 Quick Commands

### Record Purchase:
```bash
python app.py menu
→ 4. Record Purchase
```

### View Product Costs:
```bash
python app.py show-products
```

### View Movement History:
```bash
python app.py menu
→ 2. Products
→ 1. View movements for SKU
```

### Export Data:
```bash
python app.py menu
→ 7. Export Data
```

---

## 🎯 Best Practices

1. **Always enter unit cost for purchases** — Required for accurate tracking
2. **Use actual purchase price** — Don't use selling price or estimated price
3. **Include currency conversions** — If buying in USD, convert to VND first
4. **Record immediately** — Don't batch purchases with different costs
5. **Check avg cost after purchase** — System shows updated avg cost

---

## Example Workflow

### Receiving New Inventory:

1. Receive shipment from supplier
2. Check invoice for unit cost
3. Run: `python app.py menu`
4. Choose: `4. Record Purchase`
5. Enter:
   - SKU: `HM2SA-1W`
   - Qty: `10`
   - Unit Cost: `550000` (from invoice)
   - Vendor: `Supplier ABC`
6. System shows:
   ```
   ✓ Purchase recorded
   SKU: HM2SA-1W
   Quantity: +10
   Unit Cost: 550000
   
   Updated Product Info:
   On Hand: 13
   Avg Cost: 515432.14
   ```

Done! Your inventory is updated with the new weighted average cost.

---

**No more manual calculations! The system handles it all automatically.** 🎉
