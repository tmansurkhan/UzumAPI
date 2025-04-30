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
spreadsheet = client.open("Uzum API")  # Google Sheets fayli nomi

# --- Telegram ma'lumotlari ---
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
    sheet = spreadsheet.worksheet("Orders")
    data = sheet.get_all_values()

    if len(data) < 2:
        print("⚠️ Ma'lumot yetarli emas.")
        return

    headers = data[0]
    df = pd.DataFrame(data[1:], columns=headers)

    try:
        df['Sana'] = pd.to_datetime(df.iloc[:, 11], errors='coerce').dt.date  # 'L' ustun: 11-index
        df['Tannarx'] = pd.to_numeric(df.iloc[:, 10], errors='coerce')  # 'K' ustun: 10-index
        df['Sotilgan narx'] = pd.to_numeric(df.iloc[:, 8], errors='coerce')  # 'I' ustun: 8-index
        df['Soni'] = pd.to_numeric(df.iloc[:, 7], errors='coerce')  # 'H' ustun: 7-index
    except Exception as e:
        print(f"❌ Ustunlarni o'qishda xatolik: {e}")
        return

    bugun = pd.Timestamp.now().date()
    df_today = df[df['Sana'] == bugun]

    if df_today.empty:
        print("📭 Bugungi sotuvlar topilmadi.")
        return

    jami_soni = int(df_today['Soni'].sum())
    jami_savdo = int((df_today['Soni'] * df_today['Sotilgan narx']).sum())
    jami_tannarx = int((df_today['Soni'] * df_today['Tannarx']).sum())
    foyda = jami_savdo - jami_tannarx

    # Eng ko‘p sotilgan SKUlar (E ustun: 4-index)
    df_today['SKU'] = df_today.iloc[:, 4]
    top_sku = df_today.groupby('SKU')['Soni'].sum().sort_values(ascending=False).head(10).reset_index()

    # Jadvalni rasmga aylantirish
    plt.figure(figsize=(8, 4))
    plt.axis('off')
    table = plt.table(cellText=top_sku.values, colLabels=top_sku.columns, loc='center', cellLoc='center')
    table.scale(1, 1.5)
    plt.tight_layout()
    image_path = "daily_summary.png"
    plt.savefig(image_path, dpi=200)
    plt.close()

    # Yuboriladigan xabar matni
    caption = f"""📅 <b>Bugungi hisobot: {bugun}</b>
📦 <b>Jami mahsulotlar:</b> {jami_soni} dona
💰 <b>Jami savdo:</b> {jami_savdo:,} so'm
💸 <b>Jami tannarx:</b> {jami_tannarx:,} so'm
📈 <b>Foyda:</b> {foyda:,} so'm"""

    send_photo_with_caption(image_path, caption)

# --- Asosiy ---
if __name__ == "__main__":
    fetch_and_send_daily_report()
