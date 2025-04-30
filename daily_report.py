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

def fetch_and_send_daily_report():
    # Jadvalni olish
    worksheet = spreadsheet.worksheet("Orders")  # yoki siz foydalanayotgan jadval nomi
    values = worksheet.get_all_values()

    if len(values) < 2:
        print("⚠️ Ma'lumot topilmadi.")
        return

    data = values[1:]  # 1-qatordan pastdagi ma’lumotlar
    df = pd.DataFrame(data)

    # Indexlar bo‘yicha ustunlarni aniqlash
    try:
        df['SKU'] = df[3]
        df['Narx'] = pd.to_numeric(df[4], errors='coerce')        # Sotuv narxi
        df['Soni'] = pd.to_numeric(df[7], errors='coerce')        # Soni
        df['Sotilgan'] = pd.to_numeric(df[8], errors='coerce')    # Sotilgan narx
        df['Tannarx'] = pd.to_numeric(df[10], errors='coerce')    # Tannarx
        df['Sana'] = pd.to_datetime(df[11], errors='coerce').dt.date  # Sana
    except Exception as e:
        print(f"❌ Xatolik: {e}")
        return

    # NaN qiymatlarni tashlab yuboramiz
    df = df.dropna(subset=['Sana', 'Soni', 'Sotilgan', 'Tannarx'])

    # Foyda ustunini hisoblash
    df['Foyda'] = df['Sotilgan'] - df['Tannarx']

    # Sanalar bo‘yicha guruhlab olish
    grouped = df.groupby('Sana').agg({
        'Soni': 'sum',
        'Sotilgan': 'sum',
        'Tannarx': 'sum',
        'Foyda': 'sum'
    }).reset_index()

    if grouped.empty:
        print("⚠️ Hisobot uchun ma’lumot yo‘q.")
        return

    # Jadvalni rasmga aylantirish
    plt.figure(figsize=(10, 4))
    plt.axis('off')
    table = plt.table(
        cellText=grouped.values,
        colLabels=grouped.columns,
        loc='center',
        cellLoc='center'
    )
    table.scale(1.2, 1.5)
    plt.tight_layout()

    img_path = "daily_report.png"
    plt.savefig(img_path, dpi=200)
    plt.close()

    # Yuboriladigan matn
    caption = "📊 <b>Kunlik savdo hisobot</b> (sanalar bo‘yicha)"

    # Telegramga rasm + matn yuborish
    send_photo_with_caption(img_path, caption)

# --- Asosiy ishga tushirish ---
if __name__ == "__main__":
    fetch_and_send_daily_report()
