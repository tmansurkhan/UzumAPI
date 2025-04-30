import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import requests
import json
import matplotlib.pyplot as plt
from io import BytesIO
import os

# Google Sheets va Telegramga ulanish uchun o'zgaruvchilar
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
SERVICE_ACCOUNT_INFO = json.loads(os.environ["GOOGLE_APPLICATION_CREDENTIALS"])
creds = Credentials.from_service_account_info(SERVICE_ACCOUNT_INFO, scopes=SCOPE)
client = gspread.authorize(creds)
spreadsheet = client.open("Uzum API")  # Bu yerda Google Sheets nomini qo'ying

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

# Sanani olish uchun funksiya
def get_yesterday_date():
    yesterday = pd.to_datetime('today') - pd.DateOffset(1)
    return yesterday.date()

# Hisobotni olish va yuborish funksiyasi
def fetch_and_send_daily_report():
    # 'Orders' ishchi varaqasini o'qing
    orders_worksheet = spreadsheet.worksheet("Orders")  # Bu yerda o'zgartiring
    values = orders_worksheet.get_all_values()

    # Pandas DataFrame yaratish
    df = pd.DataFrame(values[1:], columns=values[0])

    # Sana ustunini to'g'ri formatlash
    df['Sana'] = pd.to_datetime(df['L'], format='%Y-%m-%d %H:%M', errors='coerce').dt.date

    # Kecha sanasini olish
    yesterday_date = get_yesterday_date()

    # Faqat kecha bo'lgan ma'lumotlarni tanlang
    df_yesterday = df[df['Sana'] == yesterday_date]

    # Agar kecha bo'yicha ma'lumotlar mavjud bo'lsa
    if not df_yesterday.empty:
        total_sales = df_yesterday['I'].sum()  # 'I' ustuni sotilgan narx
        total_cost = df_yesterday['K'].sum()   # 'K' ustuni xarajatlar
        profit = total_sales - total_cost

        # Grafik yaratish
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.bar(['Sotilgan Narx', 'Xarajatlar', 'Foyda'], [total_sales, total_cost, profit])
        ax.set_ylabel('So\'m')
        ax.set_title(f"Kecha ({yesterday_date}) hisobot")

        # Grafikni saqlash
        img_path = "/tmp/daily_report.png"
        plt.savefig(img_path)
        plt.close()

        # Telegramga rasm va matn yuborish
        caption = f"<b>Kecha ({yesterday_date}) bo'yicha hisobot:</b>\n\n" \
                  f"💰 Jami Sotilgan: {total_sales} so'm\n" \
                  f"💸 Jami Xarajatlar: {total_cost} so'm\n" \
                  f"💵 Foyda: {profit} so'm"
        send_photo_with_caption(img_path, caption)
    else:
        print(f"⚠️ Kecha ({yesterday_date}) bo'yicha ma'lumotlar topilmadi.")

# Telegramga rasm va matn yuborish uchun funksiya
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

# Asosiy funksiya
if __name__ == "__main__":
    fetch_and_send_daily_report()
