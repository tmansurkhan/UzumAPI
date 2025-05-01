import os
import json
import requests
import gspread
from google.oauth2.service_account import Credentials
from collections import defaultdict
from datetime import datetime, timedelta
from dotenv import load_dotenv

# 1. Load environment variables from .env file
load_dotenv()

# 2. Get variables from environment
uzum_api_token = os.getenv("UZUM_API_TOKEN")
telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")

# 3. Load Google Service Account credentials from JSON string in .env
with open(os.getenv("GOOGLE_APPLICATION_CREDENTIALS")) as f:
    service_account_info = json.load(f)
scopes = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_info(google_creds_dict, scopes=scopes)
client = gspread.authorize(credentials)

# 4. Open Google Sheet and worksheet
spreadsheet = client.open("Orders")
worksheet = spreadsheet.sheet1
data = worksheet.get_all_values()

# 5. Column mapping
header = data[0]
rows = data[1:]

column_indices = {col_name: idx for idx, col_name in enumerate(header)}
date_col = column_indices.get("L")
sku_col = column_indices.get("D")
price_col = column_indices.get("E")
quantity_col = column_indices.get("H")
cost_price_col = column_indices.get("K")
sold_price_col = column_indices.get("I")

# 6. Filter for today's date
today_str = datetime.now().strftime("%d.%m.%Y")
today_orders = [row for row in rows if len(row) > date_col and today_str in row[date_col]]

# 7. Calculate metrics
sku_data = defaultdict(lambda: {"quantity": 0, "sales": 0, "profit": 0})

for row in today_orders:
    try:
        sku = row[sku_col].split("-")[0]  # Extract SKU prefix
        quantity = int(row[quantity_col]) if row[quantity_col] else 0
        cost_price = int(row[cost_price_col]) if row[cost_price_col] else 0
        sold_price = int(row[sold_price_col]) if row[sold_price_col] else 0

        profit = (sold_price - cost_price) * quantity
        sales = sold_price * quantity

        sku_data[sku]["quantity"] += quantity
        sku_data[sku]["sales"] += sales
        sku_data[sku]["profit"] += profit
    except Exception as e:
        print(f"Error processing row: {row} -> {e}")

# 8. Prepare Telegram message
if sku_data:
    message_lines = [f"📦 *Kunlik hisobot* — *{today_str}*"]
    total_sales = 0
    total_profit = 0

    for sku, values in sku_data.items():
        message_lines.append(
            f"🔹 *{sku}*\n"
            f"   - Soni: {values['quantity']}\n"
            f"   - Savdo: {values['sales']} so'm\n"
            f"   - Foyda: {values['profit']} so'm"
        )
        total_sales += values["sales"]
        total_profit += values["profit"]

    message_lines.append(f"\n💰 *Jami savdo:* {total_sales} so'm")
    message_lines.append(f"📈 *Jami foyda:* {total_profit} so'm")

    message = "\n".join(message_lines)

    # 9. Send message via Telegram
    telegram_url = f"https://api.telegram.org/bot{telegram_bot_token}/sendMessage"
    payload = {
        "chat_id": telegram_chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    response = requests.post(telegram_url, json=payload)

    if response.status_code == 200:
        print("✅ Hisobot Telegramga yuborildi!")
    else:
        print("❌ Telegramga yuborishda xatolik:", response.text)
else:
    print("📭 Bugungi kun uchun hech qanday buyurtma topilmadi.")
