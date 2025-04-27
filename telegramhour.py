# --- Telegram va Google Sheets kutubxonalarini chaqiramiz ---
import os
import json
import gspread
import requests
from google.oauth2.service_account import Credentials

# --- Google Sheets'ga ulanish ---
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

service_account_info = json.loads(os.environ["GOOGLE_APPLICATION_CREDENTIALS"])
creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPE)
client = gspread.authorize(creds)
spreadsheet = client.open("Uzum API")  # Google Sheets fayl nomi

# --- Telegram bot uchun sozlamalar ---
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]   # .env fayldan oladi yoki to'g'ridan-to'g'ri yozishingiz mumkin
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]       # Foydalanuvchi chat ID si

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        print("✅ Xabar yuborildi!")
    else:
        print(f"⚠️ Xabar yuborishda xatolik: {response.text}")

def fetch_and_send_hour_info():
    hour_info_sheet = spreadsheet.worksheet("hour_info")
    values = hour_info_sheet.get_all_values()

    if len(values) < 2:
        print("⚠️ Ma'lumot topilmadi.")
        return

    # A2, B2, C2 ma'lumotlarini o'qib olamiz
    time_range = values[1][0] if len(values[1]) > 0 else "Noma'lum"
    total_products_sold = values[1][1] if len(values[1]) > 1 else "0"
    total_sales = values[1][2] if len(values[1]) > 2 else "0"

    # Telegramga yuboriladigan xabar matni
    message = f"""🕰 <b>Vaqt oralig'i:</b> {time_range}
📦 <b>Umumiy sotilgan mahsulotlar:</b> {total_products_sold} dona
💰 <b>Umumiy sotuv summasi:</b> {total_sales} so'm"""

    send_telegram_message(message)

# --- Asosiy ishga tushirish ---
if __name__ == "__main__":
    fetch_and_send_hour_info()
