# --- Telegramga xabar yuborish va hisobot tuzish --- #
def send_telegram_message(text):
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Telegram token yoki chat ID topilmadi.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        print("✅ Telegramga xabar yuborildi.")
    else:
        print(f"❌ Telegram xatosi: {response.text}")


def generate_summary_report():
    START_DATE = os.getenv('START_DATE')
    END_DATE = os.getenv('END_DATE')

    if not START_DATE or not END_DATE:
        raise ValueError("START_DATE yoki END_DATE o‘rnatilmagan!")

    start_date = datetime.strptime(START_DATE, "%Y-%m-%d")
    end_date = datetime.strptime(END_DATE, "%Y-%m-%d")

    daily_total_sheet = spreadsheet.worksheet("daily_total")
    rows = daily_total_sheet.get_all_values()[1:]  # sarlavhalarni tashlab

    filtered_rows = []
    for row in rows:
        try:
            row_date = datetime.strptime(row[0], "%Y-%m-%d")
            if start_date <= row_date <= end_date:
                filtered_rows.append(row)
        except Exception as e:
            print(f"⚠️ Sana formatida xatolik: {e}")
            continue

    if not filtered_rows:
        send_telegram_message(f"⚠️ {START_DATE} dan {END_DATE} oralig‘ida ma‘lumot topilmadi.")
        return

    total_orders = sum(int(row[1]) for row in filtered_rows)
    total_sales = sum(float(row[2]) for row in filtered_rows)
    total_purchase = sum(float(row[3]) for row in filtered_rows)
    total_commission = sum(float(row[4]) for row in filtered_rows)
    total_logistics = sum(float(row[5]) for row in filtered_rows)

    message = f"""<b>📊 Hisobot: {START_DATE} dan {END_DATE} gacha</b>

📦 <b>Jami buyurtmalar:</b> {total_orders} ta
💵 <b>Jami savdo:</b> {int(total_sales):,} so'm
🛒 <b>Jami xarajat (purchase):</b> {int(total_purchase):,} so'm
🏦 <b>Jami komissiya:</b> {int(total_commission):,} so'm
🚚 <b>Jami logistika:</b> {int(total_logistics):,} so'm
"""

    send_telegram_message(message)


# --- Asosiy chaqiruv --- #
if __name__ == "__main__":
    generate_summary_report()
