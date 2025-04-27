# --- Kutubxonalarni chaqirish ---
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
spreadsheet = client.open("Uzum API")  # Sheets fayl nomi

# --- Telegram token va chat ID ---
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

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
    total_withdrawn = values[1][3] if len(values[1]) > 3 else "0"

    # SKU sotuv ma'lumotlarini pandas orqali o'qib olamiz
    sku_data = values[2:]  # 3-qator va pastdagi qatorlar
    sku_df = pd.DataFrame(sku_data, columns=["", "", "", "", "SKU", "Withdrawn", "Sold"])

    if sku_df.empty:
        print("⚠️ SKU ma'lumotlari topilmadi.")
        return

    # Faqat kerakli ustunlarni olish
    plot_df = sku_df[["SKU", "Withdrawn", "Sold"]].dropna()

    # Rasm faylini yaratamiz
    plt.figure(figsize=(8, 4))
    plt.axis('tight')
    plt.axis('off')
    table = plt.table(cellText=plot_df.values, colLabels=plot_df.columns, loc='center', cellLoc='center')
    table.scale(1, 1.5)
    plt.tight_layout()

    img_path = "sku_table.png"
    plt.savefig(img_path, dpi=200)
    plt.close()

    # Telegramga yuboriladigan matn
    caption = f"""🕰 <b>Vaqt oralig'i:</b> {time_range}
📦 <b>Jami mahsulotlar:</b> {total_products_sold} dona
💰 <b>Jami savdo:</b> {total_sales} so'm
🏦 <b>Jami yechib olingan:</b> {total_withdrawn} so'm"""

    # Rasm + Text birga yuborish
    send_photo_with_caption(img_path, caption)

# --- Asosiy ---
if __name__ == "__main__":
    fetch_and_send_hour_info()
