import os
import json
import gspread
import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials

# --- Google Sheets'ga ulanish ---
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
service_account_info = json.loads(os.environ["GOOGLE_APPLICATION_CREDENTIALS"])
creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPE)
client = gspread.authorize(creds)
spreadsheet = client.open("Uzum API")

# --- Telegram token va chat ID ---
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

def pin_message(message_id):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/pinChatMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "message_id": message_id,
        "disable_notification": True
    }
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        print("📌 Xabar pin qilindi!")
    else:
        print(f"⚠️ Pin qilishda xatolik: {response.text}")

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
            print("✅ Rasm va matn yuborildi!")
            message_id = response.json()["result"]["message_id"]
            pin_message(message_id)
        else:
            print(f"⚠️ Xatolik: {response.text}")

def fetch_and_send_daily_info():
    orders_sheet = spreadsheet.worksheet("Orders")
    values = orders_sheet.get_all_values()

    if len(values) < 2:
        print("⚠️ Ma'lumotlar topilmadi.")
        return

    data = values[1:]

    yesterday = (datetime.today() - timedelta(days=1)).date()

    total_quantity = 0
    total_sales = 0
    total_withdrawn = 0
    total_profit = 0
    filtered_rows = []

    for row in data:
        try:
            date_str = row[12].split()[0]  # M ustun — index 12
            row_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except (IndexError, ValueError):
            continue

        if row_date != yesterday:
            continue

        try:
            quantity = int(row[7]) if row[7] else 0       # H ustun — index 7
            price = int(row[4]) if row[4] else 0          # E ustun — index 4
            withdrawn = int(row[8]) if row[8] else 0      # I ustun — index 8
            cost = int(row[10]) if row[10] else 0         # K ustun — index 10
        except (IndexError, ValueError):
            continue

        if quantity == 0:
            continue

        total_quantity += quantity
        total_sales += price
        total_withdrawn += withdrawn
        total_profit += withdrawn - cost

        sku = row[3]  # D ustun — SKU (index 3)
        filtered_rows.append([sku, quantity, price])

    if not filtered_rows:
        print("❌ Kechagi sana bo‘yicha hech qanday ma’lumot topilmadi.")
        return

    # DataFrame yaratib, SKU bo‘yicha guruhlab va kamayish tartibida saralab olish
    df = pd.DataFrame(filtered_rows, columns=["SKU", "Soni", "Narxi"])
    df_grouped = df.groupby("SKU", as_index=False).sum()
    df_grouped = df_grouped.sort_values(by="Soni", ascending=False)

    # Jadvalni rasmga chiqarish
    plt.figure(figsize=(8, 4 + len(df_grouped) * 0.25))
    plt.axis('tight')
    plt.axis('off')
    table = plt.table(cellText=df_grouped.values, colLabels=df_grouped.columns, loc='center', cellLoc='center')
    table.scale(1, 1.5)
    plt.tight_layout()
    img_path = "daily_summary.png"
    plt.savefig(img_path, dpi=200)
    plt.close()

    caption = f"""🗓 <b>Sana:</b> {yesterday.strftime('%Y-%m-%d')}
📦 <b>Jami sotilgan mahsulotlar:</b> {total_quantity} dona
💰 <b>Jami tushum:</b> {total_sales} so'm
🏦 <b>Jami yechilgan:</b> {total_withdrawn} so'm
📈 <b>Sof foyda:</b> {total_profit} so'm"""

    send_photo_with_caption(img_path, caption)

# --- Asosiy ---
if __name__ == "__main__":
    fetch_and_send_daily_info()
