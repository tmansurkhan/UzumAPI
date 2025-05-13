# --- Kutubxonalarni chaqirish ---
import os
import json
import requests
import gspread
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from collections import defaultdict
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

# --- Muhit o'zgaruvchilarini yuklash (.env fayldan) ---
load_dotenv()

# --- Telegram ma'lumotlari ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# --- Google Sheets'ga ulanish uchun credential ---
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

with open("service_account.json") as f:
    service_account_info = json.load(f)

creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPE)
client = gspread.authorize(creds)

# --- Google Sheets faylini ochish va 'nakladnoy' varog'ini tanlash ---
spreadsheet = client.open("Uzum API")
worksheet = spreadsheet.worksheet("Orders")
data = worksheet.get_all_values()

if not data:
    print("❌ Jadval bo‘sh!")
    exit()

header = data[0]
rows = data[1:]

# --- Ustun nomi asosida indeks aniqlash funksiyasi ---
def col_index(name):
    return header.index(name) if name in header else -1

# --- Ustun indekslari ---
date_col = col_index("DateCreated")
sku_col = col_index("ProductTitle")
quantity_col = col_index("QuantityAccepted")
cost_price_col = col_index("PurchasePrice")
sold_price_col = col_index("SellerProfit")  # Bu ustun mavjud bo‘lishi kerak

# --- Bugungi sanani olish va filtrlash ---
today_str = datetime.now().strftime("%Y-%m-%d")
today_orders = [row for row in rows if len(row) > date_col and today_str in row[date_col]]

# --- Ma'lumotlarni yig'ish ---
sku_data = defaultdict(lambda: {"quantity": 0, "sales": 0, "profit": 0})

for row in today_orders:
    try:
        sku = row[sku_col].split("-")[0].strip() if "-" in row[sku_col] else row[sku_col].strip()
        quantity = int(row[quantity_col]) if row[quantity_col] else 0
        cost = int(row[cost_price_col]) if row[cost_price_col] else 0
        sold = int(row[sold_price_col]) if row[sold_price_col] else 0

        profit = (sold - cost) * quantity
        sales = sold * quantity

        sku_data[sku]["quantity"] += quantity
        sku_data[sku]["sales"] += sales
        sku_data[sku]["profit"] += profit
    except Exception as e:
        print(f"⚠️ Xatolik: {row} -> {e}")

# --- Telegramga rasm yuborish funksiyasi ---
def send_photo_with_caption(photo_path, caption):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    with open(photo_path, "rb") as photo_file:
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "caption": caption,
            "parse_mode": "HTML"
        }
        files = {"photo": photo_file}
        response = requests.post(url, data=payload, files=files)
        if response.status_code == 200:
            print("✅ Telegramga rasm yuborildi!")
        else:
            print(f"❌ Xatolik: {response.text}")

# --- Jadvalni tayyorlash va Telegramga yuborish ---
if sku_data:
    df = pd.DataFrame([{
        "SKU": sku,
        "Soni": vals["quantity"],
        "Savdo": vals["sales"],
        "Foyda": vals["profit"]
    } for sku, vals in sku_data.items()])

    total_sales = df["Savdo"].sum()
    total_profit = df["Foyda"].sum()

    # Jadvaldan rasm yaratish
    plt.figure(figsize=(8, 4))
    plt.axis('off')
    table = plt.table(cellText=df.values, colLabels=df.columns, loc='center', cellLoc='center')
    table.scale(1, 1.5)
    plt.tight_layout()

    image_path = "daily_report.png"
    plt.savefig(image_path, dpi=200)
    plt.close()

    caption = f"""📊 <b>Kunlik hisobot — {today_str}</b>
💰 <b>Jami savdo:</b> {total_sales} so'm
📈 <b>Jami foyda:</b> {total_profit} so'm"""

    send_photo_with_caption(image_path, caption)
else:
    print("📭 Bugungi buyurtmalar topilmadi.")
