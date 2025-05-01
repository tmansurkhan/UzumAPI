import os
import json
import requests
import gspread
from google.oauth2.service_account import Credentials
from collections import defaultdict
from datetime import datetime
from dotenv import load_dotenv

# 1. Load environment variables
load_dotenv()

# 2. Get credentials and tokens
telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
with open(os.getenv("GOOGLE_APPLICATION_CREDENTIALS")) as f:
    service_account_info = json.load(f)

# 3. Google credentials
with open(google_credentials_path) as f:
    creds_data = json.load(f)

scopes = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_info(creds_data, scopes=scopes)
client = gspread.authorize(credentials)

# 4. Open spreadsheet and get data
spreadsheet = client.open("Orders")
worksheet = spreadsheet.sheet1
data = worksheet.get_all_values()

if not data:
    print("❌ Jadval bo‘sh!")
    exit()

header = data[0]
rows = data[1:]

# 5. Column index mapping
def col_index(name):
    return header.index(name) if name in header else -1

date_col = col_index("date")             # Column L
sku_col = col_index("ProductTitle")      # Column D
quantity_col = col_index("amount")       # Column H
cost_price_col = col_index("purchasePrice")  # Column K
sold_price_col = col_index("sellerProfit")   # Column I

# 6. Filter today's rows
today_str = datetime.now().strftime("%Y-%m-%d")  # Format: 2024-05-01
today_orders = [row for row in rows if len(row) > date_col and today_str in row[date_col]]

# 7. Aggregate data
sku_data = defaultdict(lambda: {"quantity": 0, "sales": 0, "profit": 0})
for row in today_orders:
    try:
        sku = row[sku_col].split("-")[0] if "-" in row[sku_col] else row[sku_col]
        quantity = int(row[quantity_col]) if row[quantity_col] else 0
        cost = int(row[cost_price_col]) if row[cost_price_col] else 0
        sold = int(row[sold_price_col]) if row[sold_price_col] else 0

        profit = (sold - cost) * quantity
        sales = sold * quantity

        sku_data[sku]["quantity"] += quantity
        sku_data[sku]["sales"] += sales
        sku_data[sku]["profit"] += profit
    except Exception as e:
        print(f"⚠️ Satrda xatolik: {row} -> {e}")

# 8. Prepare Telegram message
if sku_data:
    message_lines = [f"📦 *Kunlik hisobot* — *{today_str}*"]
    total_sales = 0
    total_profit = 0

    for sku, vals in sku_data.items():
        message_lines.append(
            f"🔹 *{sku}*\n"
            f"   - Soni: {vals['quantity']}\n"
            f"   - Savdo: {vals['sales']} so'm\n"
            f"   - Foyda: {vals['profit']} so'm"
        )
        total_sales += vals["sales"]
        total_profit += vals["profit"]

    message_lines.append(f"\n💰 *Jami savdo:* {total_sales} so'm")
    message_lines.append(f"📈 *Jami foyda:* {total_profit} so'm")

    telegram_url = f"https://api.telegram.org/bot{telegram_bot_token}/sendMessage"
    payload = {
        "chat_id": telegram_chat_id,
        "text": "\n".join(message_lines),
        "parse_mode": "Markdown"
    }

    res = requests.post(telegram_url, json=payload)
    if res.status_code == 200:
        print("✅ Telegramga yuborildi!")
    else:
        print("❌ Xatolik:", res.text)
else:
    print("📭 Bugungi buyurtmalar yo‘q.")
