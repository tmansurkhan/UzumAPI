# --- Telegram va Google Sheets kutubxonalarini chaqiramiz ---
import os
import json
import gspread
import requests
import pandas as pd
import matplotlib.pyplot as plt
from google.oauth2.service_account import Credentials

# --- Google Sheets'ga ulanish ---
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

service_account_info = json.loads(os.environ["GOOGLE_APPLICATION_CREDENTIALS"])
creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPE)
client = gspread.authorize(creds)
spreadsheet = client.open("Uzum API")  # Google Sheets fayl nomi

# --- Telegram bot uchun sozlamalar ---
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        print("✅ Matnli xabar yuborildi!")
    else:
        print(f"⚠️ Matn yuborishda xatolik: {response.text}")

def send_telegram_photo(photo_path):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    with open(photo_path, 'rb') as photo:
        response = requests.post(url, files={'photo': photo}, data={'chat_id': TELEGRAM_CHAT_ID})
    if response.status_code == 200:
        print("✅ Rasm yuborildi!")
    else:
        print(f"⚠️ Rasm yuborishda xatolik: {response.text}")

def fetch_and_send_hour_info():
    hour_info_sheet = spreadsheet.worksheet("hour_info")
    values = hour_info_sheet.get_all_values()

    if len(values) < 2:
        print("⚠️ Ma'lumot topilmadi.")
        return

    # A2, B2, C2, D2 ma'lumotlarini o'qib olamiz
    time_range = values[1][0] if len(values[1]) > 0 else "Noma'lum"
    total_products_sold = values[1][1] if len(values[1]) > 1 else "0"
    total_sales = values[1][2] if len(values[1]) > 2 else "0"
    total_withdrawn = values[1][3] if len(values[1]) > 3 else "0"  # D2

    # --- 1. Matnli xabar tayyorlaymiz ---
    message = f"""🕰 <b>Vaqt oralig'i:</b> {time_range}
📦 <b>Jami mahsulotlar:</b> {total_products_sold} dona
💰 <b>Jami savdo:</b> {total_sales} so'm
🏦 <b>Jami yechib olishga:</b> {total_withdrawn} so'm"""

    send_telegram_message(message)

    # --- 2. E:G ustunlar ma'lumotlarini olib rasmga aylantiramiz ---
    headers = values[0][4:7]  # E, F, G ustunlar nomlari
    rows = [row[4:7] for row in values[1:] if len(row) >= 7]

    if not rows:
        print("⚠️ SKU sotuv ma'lumotlari topilmadi.")
        return

    df = pd.DataFrame(rows, columns=headers)

    # DataFrame'ni rasmga chizamiz
    fig, ax = plt.subplots(figsize=(8, len(df) * 0.6))
    ax.axis('tight')
    ax.axis('off')
    table = ax.table(cellText=df.values, colLabels=df.columns, cellLoc='center', loc='center')
    fig.tight_layout()

    image_path = "hour_table.png"
    plt.savefig(image_path, dpi=200)

    # Rasmni Telegramga yuboramiz
    send_telegram_photo(image_path)

# --- Asosiy ishga tushirish ---
if __name__ == "__main__":
    fetch_and_send_hour_info()
