# --- 6. Oxirgi 1 soatlik ma'lumotlar: hour_info ---
from datetime import datetime, timedelta

hour_info_sheet = get_or_create_sheet("hour_info", 100, 10)
hour_info_sheet.clear()
hour_info_sheet.append_row([
    "Time Range", "Total Products Sold", "Total Sales", "Total Withdrawn Profit", "SKU", "Sold Quantity"
])

# "Orders" sahifasidagi barcha ma'lumotlarni olish
orders_data = orders_sheet.get_all_values()

# Hozirgi vaqt (UTC + 5 soat qilib)
current_time = datetime.utcnow() + timedelta(hours=5)
one_hour_ago = current_time - timedelta(hours=1)

# Statistikani tayyorlash
total_products_sold = 0
total_sales = 0
total_withdrawn_profit = 0
sku_sales = defaultdict(int)

for row in orders_data[1:]:
    try:
        order_time = datetime.strptime(row[12], "%Y-%m-%d %H:%M")
        if one_hour_ago <= order_time <= current_time:
            quantity = int(row[7])
            sell_price = float(row[4])
            withdrawn_profit = float(row[9])
            sku = row[3]

            total_products_sold += quantity
            total_sales += sell_price * quantity
            total_withdrawn_profit += withdrawn_profit * quantity
            sku_sales[sku] += quantity

    except Exception as e:
        print(f"⚠️ Xatolik vaqtni tekshirishda: {e}")
        continue

# Natijani tayyorlash
time_range = f"{one_hour_ago.strftime('%Y-%m-%d %H:%M')} - {current_time.strftime('%Y-%m-%d %H:%M')}"
rows_to_write = []

if total_products_sold > 0:
    # Har bir SKU bo‘yicha alohida qator yozish
    for sku, qty in sku_sales.items():
        rows_to_write.append([
            time_range,
            total_products_sold,
            total_sales,
            total_withdrawn_profit,
            sku,
            qty
        ])
else:
    rows_to_write.append([time_range, 0, 0, 0, "No sales", 0])

hour_info_sheet.append_rows(rows_to_write, value_input_option="USER_ENTERED")
print("✅ Oxirgi 1 soatlik ma’lumotlar 'hour_info' sahifasiga yozildi.")
