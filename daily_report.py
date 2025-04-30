import os
import json
import gspread
import requests
import pandas as pd
from datetime import datetime, timedelta
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

def send_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        print("✅ Xabar yuborildi!")
    else:
        print(f"⚠️ Xatolik: {response.text}")

def fetch_and_send_daily_report():
    sheet = spreadsheet.worksheet("Orders")
    data = sheet.get_all_values()

    if not data or len(data) < 2:
        print("⚠️ Jadvalda ma'lumot yo'q.")
        return

    df = pd.DataFrame(data[1:], columns=data[0])

    # Sana formatini tuzatish va faqat kechagi sanani tanlash
    df['Sana'] = pd.to_datetime(df['L'], errors='coerce').dt.date
    yesterday = datetime.now().date() - timedelta(days=1)
    df_yesterday = df[df['Sana'] == yesterday]

    if df_yesterday.empty:
        print("⚠️ Kechagi ma'lumot topilmadi.")
        return

    # Zarur ustunlarni floatga aylantirish
    df_yesterday['Sotilgan'] = pd.to_numeric(df_yesterday['I'], errors='coerce')
    df_yesterday['Tannarx'] = pd.to_numeric(df_yesterday['K'], errors='coerce')
    df_yesterday['Soni'] = pd.to_numeric(df_yesterday['H'], errors='coerce')  # Miqdor ustuni

    df_yesterday = df_yesterday.dropna(subset=['Sotilgan', 'Tannarx', 'Soni'])

    # Hisoblash
    total_quantity = int(df_yesterday['Soni'].sum())
    total_sales = int((df_yesterday['Sotilgan'] * df_yesterday['Soni']).sum())
    total_cost = int((df_yesterday['Tannarx'] * df_yesterday['Soni']).sum())
    total_profit = total_sales - total_cost

    text = f"""📊 <b>Kechagi hisobot ({yesterday}):</b>
📦 <b>Jami mahsulotlar:</b> {total_quantity} dona
💰 <b>Jami savdo:</b> {total_sales:,} so'm
🏷 <b>Jami tannarx:</b> {total_cost:,} so'm
📈 <b>Sof foyda:</b> <u>{total_profit:,} so'm</u>"""

    send_message(text)

# --- Asosiy ---
if __name__ == "__main__":
    fetch_and_send_daily_report()
