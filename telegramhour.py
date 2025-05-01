# --- Kutubxonalarni chaqirish ---
import os
import json
import gspread
import requests
import pandas as pd
import matplotlib.pyplot as plt
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

# --- .env faylni yuklash ---
load_dotenv()

# --- Google Sheets'ga ulanish ---
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

with open("service_account.json") as f:
    service_account_info = json.load(f)
creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPE)
client = gspread.authorize(creds)
spreadsheet = client.open("Uzum API")  # Sheets fayl nomi

# --- Telegram token va chat ID ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# --- Telegramga rasm va caption yuborish ---
def send_photo_with_caption(photo_path, caption):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    with open(photo_path, "rb") as photo_file:
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "caption": caption,
            "parse_mode": "HTML"
        }
        files = {
            "photo": photo_file
        }
        response = requests.post(url, data=payload, files=files)
        if response.status_code == 200:
            print("✅ Rasm va matn yuborildi!")
        else:
            print(f"⚠️ Xatolik: {response.text}")

# --- 'hour_info' sahifasidan ma'lumot olib, Telegramga yuborish ---
def fetch_and_send_hour_info():
    hour_info_sheet = spreadsheet.worksheet("hour_info")
    values = hour_info_sheet.get_all_values()

    if len(values) < 2:
        print("⚠️ Ma'lumot topilmadi.")
        return

    # Umumiy statistikalar
    time_range = values[1][0] if len(values[1]) > 0 else "Noma'lum"
    total_products_sold = values[1][1] if len(values[1]) > 1 else "0"
    total_sales = values[1][2] if len(values[1]) > 2 else "0"
    total_withdrawn = values[1][3] if len(values[1]) > 3 else "0"

    # SKU ma'lumotlarini DataFrame ga o'qish
    sku_data = values[2:]
    if not sku_data:
        print("⚠️ SKU ma'lumotlari topilmadi.")
        return

    sku_df = pd.DataFrame(sku_data, columns=["", "", "", "", "SKU", "Withdrawn", "Sold"])
    plot_df = sku_df[["SKU", "Withdrawn", "Sold"]].dropna()

    if plot_df.empty:
        print("⚠️ Grafik uchun mos ma'lumot yo'q.")
        return

    # Jadvaldan rasm tayyorlash
    plt.figure(figsize=(8, 4))
    plt.axis('off')
    table = plt.table(cellText=plot_df.values, colLabels=plot_df.columns, loc='center', cellLoc='center')
    table.scale(1, 1.5)
    plt.tight_layout()

    img_path = "sku_table.png"
    plt.savefig(img_path, dpi=200)
    plt.close()

    # Telegram caption
    caption = f"""🕰 <b>Vaqt oralig'i:</b> {time_range}
📦 <b>Jami mahsulotlar:</b> {total_products_sold} dona
💰 <b>Jami savdo:</b> {total_sales} so'm
🏦 <b>Jami yechib olingan:</b> {total_withdrawn} so'm"""

    # Rasm va caption yuborish
    send_photo_with_caption(img_path, caption)

# --- Asosiy ishga tushirish ---
if __name__ == "__main__":
    fetch_and_send_hour_info()
