# --- Kutubxonalarni chaqirish ---
import os
import json
import gspread
import requests
import pandas as pd
from datetime import datetime
from google.oauth2.service_account import Credentials

# --- Google Sheets'ga ulanish ---
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

service_account_info = json.loads(os.environ["GOOGLE_APPLICATION_CREDENTIALS"])
creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPE)
client = gspread.authorize(creds)
spreadsheet = client.open("Uzum API")  # Sheets nomi

# --- Telegram token va chat ID ---
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

# --- Start va End date ni olish ---
START_DATE = os.getenv('START_DATE')
END_DATE = os.getenv('END_DATE')

if not START_DATE or not END_DATE:
    raise ValueError("Start va End date kiritilmagan!")

start_date = datetime.strptime(START_DATE, "%Y-%m-%d")
end_date = datetime.strptime(END_DATE, "%Y-%m-%d")

# --- Telegramga xabar yuborish funksiyasi ---
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

# --- Hisobot tayyorlash funksiyasi ---
def generate_report():
    orders_sheet = spreadsheet.worksheet("Orders")
    rows = orders_sheet.get_all_values()

    if len(rows) < 2:
        print("⚠️ 'Orders' jadvalida ma'lumot topilmadi.")
        return

    # DataFrame yaratamiz (ustun sarlavhasiz)
    df = pd.DataFrame(rows[1:], columns=None)

    # Indekslar bo'yicha ustunlar
    # D => 3 (index 3) - SKU
    # E => 4 (index 4) - Sotuv narxi
    # F => 5 (index 5) - Komissiya
    # G => 6 (index 6) - Logistika
    # H => 7 (index 7) - Buyurtma soni
    # M => 12 (index 12) - Buyurtma vaqti

    # Vaqt ustunini datetime formatga o'tkazish
    df[12] = pd.to_datetime(df[12], format="%d.%m.%Y %H:%M", errors='coerce')

    # Sana oralig'iga qarab filterlash
    filtered_df = df[(df[12] >= start_date) & (df[12] <= end_date)]

    if filtered_df.empty:
        send_message(f"⚠️ {START_DATE} dan {END_DATE} gacha hisobot uchun ma'lumot topilmadi.")
        return

    # Zarur ustunlarni numeric qilish
    filtered_df[4] = pd.to_numeric(filtered_df[4], errors='coerce').fillna(0)  # Sotuv narxi
    filtered_df[5] = pd.to_numeric(filtered_df[5], errors='coerce').fillna(0)  # Komissiya
    filtered_df[6] = pd.to_numeric(filtered_df[6], errors='coerce').fillna(0)  # Logistika
    filtered_df[7] = pd.to_numeric(filtered_df[7], errors='coerce').fillna(0)  # Buyurtma soni

    total_sales = (filtered_df[4] * filtered_df[7]).sum()
    total_commission = (filtered_df[5] * filtered_df[7]).sum()
    total_logistics = (filtered_df[6] * filtered_df[7]).sum()
    total_orders = filtered_df[7].sum()

    # Top 3 SKU hisoblash
    filtered_df['total_revenue'] = filtered_df[4] * filtered_df[7]
    top3_sku = (
        filtered_df.groupby(3)['total_revenue']  # SKU ustuni
        .sum()
        .sort_values(ascending=False)
        .head(3)
    )

    top3_text = "\n".join([f"🏅 <b>{sku}</b>: {int(amount):,} so'm" for sku, amount in top3_sku.items()])

    # Yuboriladigan xabar
    message = f"""<b>📊 Hisobot: {START_DATE} dan {END_DATE} gacha</b>

📦 <b>Jami buyurtmalar:</b> {int(total_orders)} ta
💵 <b>Jami savdo:</b> {int(total_sales):,} so'm
🏦 <b>Jami komissiya:</b> {int(total_commission):,} so'm
🚚 <b>Jami logistika:</b> {int(total_logistics):,} so'm

<b>🏆 Top 3 SKU:</b>
{top3_text}
"""

    send_message(message)

# --- Asosiy ---
if __name__ == "__main__":
    generate_report()