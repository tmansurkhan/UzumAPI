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
spreadsheet = client.open("Uzum API")  # Sizning Sheets faylingiz nomi

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
    data = orders_sheet.get_all_values()

    if len(data) < 2:
        print("⚠️ 'Orders' jadvalida ma'lumot topilmadi.")
        return

    header = data[0]
    rows = data[1:]

    df = pd.DataFrame(rows, columns=header)

    # Zarur ustunlarni olish
    needed_columns = ['D', 'E', 'F', 'G', 'H', 'M']
    if not all(col in df.columns for col in needed_columns):
        raise ValueError("Sheetsda kerakli ustunlar topilmadi!")

    # Vaqt ustunini datetime formatga o'tkazish
    df['M'] = pd.to_datetime(df['M'], format="%d.%m.%Y %H:%M")

    # Sana oralig'iga qarab filterlash
    filtered_df = df[(df['M'] >= start_date) & (df['M'] <= end_date)]

    if filtered_df.empty:
        send_message(f"⚠️ {START_DATE} dan {END_DATE} gacha hisobot uchun ma'lumot topilmadi.")
        return

    # Hisoblash
    filtered_df['E'] = pd.to_numeric(filtered_df['E'], errors='coerce').fillna(0)
    filtered_df['F'] = pd.to_numeric(filtered_df['F'], errors='coerce').fillna(0)
    filtered_df['G'] = pd.to_numeric(filtered_df['G'], errors='coerce').fillna(0)
    filtered_df['H'] = pd.to_numeric(filtered_df['H'], errors='coerce').fillna(0)

    total_sales = (filtered_df['E'] * filtered_df['H']).sum()
    total_commission = (filtered_df['F'] * filtered_df['H']).sum()
    total_logistics = (filtered_df['G'] * filtered_df['H']).sum()
    total_orders = filtered_df['H'].sum()

    # Top 3 SKU ni aniqlash
    filtered_df['total_revenue'] = filtered_df['E'] * filtered_df['H']
    top3_sku = (
        filtered_df.groupby('D')['total_revenue']
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