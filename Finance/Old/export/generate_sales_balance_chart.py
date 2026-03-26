import pandas as pd
import matplotlib.pyplot as plt

# Read sales and balance data from cash flow CSV
csv_path = "import_data/Sales Management-Mastersheet - Cash Flow (2).csv"
df = pd.read_csv(csv_path, header=1)

# Extract months and sales/balance rows
months = [
    'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
]
sales_row = df[df.iloc[:,0].str.contains('Total Sales', na=False)].iloc[0,2:14]
balance_row = df[df.iloc[:,0].str.contains('Net Balance', na=False)].iloc[0,2:14]
cost_row = df[df.iloc[:,0].str.contains('Total Cost', na=False)].iloc[0,2:14]

# Clean currency formatting
def parse_vnd(val):
    if isinstance(val, str):
        return float(val.replace('₫','').replace(',','').replace('"','').strip() or 0)
    return float(val)

sales = sales_row.apply(parse_vnd).values
balance = balance_row.apply(parse_vnd).values
cost = cost_row.apply(parse_vnd).values


# Plot
fig, ax1 = plt.subplots(figsize=(10,6))

color_sales = 'tab:blue'
color_cost = 'tab:red'
color_balance = 'tab:green'

ax1.set_xlabel('Month (2025)')
ax1.set_ylabel('Total Sales / Cost (VND)')

bar1 = ax1.bar(months, sales, color=color_sales, alpha=0.6, label='Total Sales')
line_cost, = ax1.plot(months, cost, color=color_cost, marker='s', linestyle='--', label='Total Cost')
ax1.tick_params(axis='y')

ax2 = ax1.twinx()
ax2.set_ylabel('Net Balance (VND)', color=color_balance)
line2, = ax2.plot(months, balance, color=color_balance, marker='o', label='Net Balance')
ax2.tick_params(axis='y', labelcolor=color_balance)

# Add legends for all
fig.legend([bar1, line_cost, line2], ['Total Sales', 'Total Cost', 'Net Balance'], loc='upper left', bbox_to_anchor=(0.1, 0.92))

plt.title('2025 Sales and Net Balance')
fig.tight_layout()
plt.savefig('export/sales_balance_2025.png')
plt.close()
print('Chart saved as export/sales_balance_2025.png')
