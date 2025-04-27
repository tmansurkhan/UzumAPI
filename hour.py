# --- hour.py ---

import os
import json
import gspread
from google.oauth2.service_account import Credentials
from collections import defaultdict
from datetime import datetime, timedelta

# --- 1. Google Sheets'ga ulanish ---
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

service_account_info = json.loads(os.environ["GOOGLE_APPLICATION_CREDENTIALS"])
creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPE)
client = gspread.authorize(creds)
spreadsheet = client.open("Uzum API")  # Sizning faylingiz nomi

# --- 2. Helper: Sheetni olish yoki yaratish funksiyasi ---
def get_or_create_sheet(title, rows=100, cols=10):
    try:
        return spreadsheet.worksheet(title)
    except gspread.exceptions.WorksheetNotFound:
        return spreadsheet.add_worksheet(title=title, rows=rows, cols=cols)

# --- 3. Oxirgi 1 soatlik ma'lumotlarni tayyorlash ---
def process_last_hour_orders():
    orders_sheet = get_or_create_sheet("Orders")
    hour_info_sheet = get_or_create_sheet("hour_info", 100, 10)

    # hour_info sahifani tozalab, yangi sarlavha yozamiz
    hour_info_sheet.clear()
    hour_info_sheet.append_row([
        "Time Range", "Total Products Sold", "Total Sales", "Total Withdrawn Profit", 
        "SKU", "Withdrawn", "Sold Quantity"
    ])

    orders_data = orders_sheet.get_all_values()

    current_time = datetime.utcnow() + timedelta(hours=5)
    one_hour_ago = current_time - timedelta(hours=1)

    total_products_sold = 0
    total_sales = 0
    total_withdrawn_profit = 0
    sku_sales = defaultdict(lambda: {"sold_qty": 0, "withdrawn": 0})

    for row in orders_data[1:]:
        try:
            order_time = datetime.strptime(row[12], "%Y-%m-%d %H:%M")
            if one_hour_ago <= order_time <= current_time:
                quantity = int(row[7])         # Sold quantity
                sell_price = float(row[4])     # Sale price
                withdrawn_profit = float(row[8])  # Withdrawn profit
                sku = row[3]                   # SKU code
                withdrawn = int(row[7])    # Available quantity

                total_products_sold += quantity
                total_sales += sell_price * quantity
                total_withdrawn_profit += withdrawn_profit * quantity

                # Ma'lumotlarni yig'amiz
                sku_sales[sku]["sold_qty"] += quantity
                sku_sales[sku]["withdrawn"] = withdrawn

        except Exception as e:
            print(f"⚠️ Ma'lumotni o'qishda xatolik: {e}")
            continue

    time_range = f"{one_hour_ago.strftime('%Y-%m-%d %H:%M')} - {current_time.strftime('%Y-%m-%d %H:%M')}"

    rows_to_write = []

    if total_products_sold > 0:
        # Birinchi qator: umumiy statistikani yozamiz
        rows_to_write.append([
            time_range,
            total_products_sold,
            total_sales,
            total_withdrawn_profit,
            "", "", ""
        ])

        # Har bir SKU uchun alohida qator tayyorlaymiz
        for sku, data in sku_sales.items():
            rows_to_write.append([
                "", "", "", "",
                sku,
                data["withdrawn"],
                data["sold_qty"]
            ])
    else:
        # Agar sotuv bo'lmasa
        rows_to_write.append([
            time_range, 0, 0, 0, "No sales", 0, 0
        ])

    # Barcha qatorlarni bir martada yozamiz
    hour_info_sheet.append_rows(rows_to_write, value_input_option="USER_ENTERED")

    print("✅ So'nggi 1 soatlik ma'lumotlar 'hour_info' sahifasiga tartibli yozildi.")

# --- 4. Asosiy ishga tushirish ---
if __name__ == "__main__":
    process_last_hour_orders()
