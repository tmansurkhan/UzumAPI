import os
import json
import logging
import gspread
import pandas as pd
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from google.oauth2.service_account import Credentials

# --- Logger ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- Google Sheets'ga ulanish ---
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
service_account_info = json.loads(os.environ["GOOGLE_APPLICATION_CREDENTIALS"])
creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPE)
client = gspread.authorize(creds)
spreadsheet = client.open("Uzum API")  # Google Sheet nomi
ORDERS_SHEET_NAME = "Orders"

# --- Telegram token ---
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

# --- Vaqt formati ---
DATE_FORMAT = "%Y-%m-%d"

# --- Reply Keyboard (bosh menyu) ---
main_keyboard = ReplyKeyboardMarkup([["Hisobot olish"]], resize_keyboard=True)

# --- Inline Keyboard ---
def get_time_range_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Bugungi", callback_data="today"),
         InlineKeyboardButton("Kechagi", callback_data="yesterday")],
        [InlineKeyboardButton("1 hafta", callback_data="1week"),
         InlineKeyboardButton("2 hafta", callback_data="2weeks")],
        [InlineKeyboardButton("1 oy", callback_data="1month"),
         InlineKeyboardButton("Ixtiyoriy", callback_data="custom")]
    ])

# --- Hisobotni olib kelish ---
def fetch_report(start_date, end_date):
    orders_sheet = spreadsheet.worksheet(ORDERS_SHEET_NAME)
    data = orders_sheet.get_all_records()
    if not data:
        return None, None

    df = pd.DataFrame(data)
    df['Order Time'] = pd.to_datetime(df['M'], errors='coerce')
    df = df.dropna(subset=['Order Time'])
    mask = (df['Order Time'] >= start_date) & (df['Order Time'] <= end_date)
    filtered = df.loc[mask]
    if filtered.empty:
        return None, None

    # Raqamlar
    filtered['E'] = pd.to_numeric(filtered['E'], errors='coerce').fillna(0)
    filtered['F'] = pd.to_numeric(filtered['F'], errors='coerce').fillna(0)
    filtered['G'] = pd.to_numeric(filtered['G'], errors='coerce').fillna(0)
    filtered['H'] = pd.to_numeric(filtered['H'], errors='coerce').fillna(0)

    total_sales = (filtered['E'] * filtered['H']).sum()
    total_commission = (filtered['F'] * filtered['H']).sum()
    total_logistics = (filtered['G'] * filtered['H']).sum()
    total_orders = filtered['H'].sum()

    filtered['total_sold_price'] = filtered['E'] * filtered['H']
    top_skus = (filtered.groupby('D')['total_sold_price']
                .sum().sort_values(ascending=False).head(3))

    return (total_sales, total_commission, total_logistics, total_orders), top_skus

# --- Hisobotni formatlash ---
def format_report(start_date, end_date, report_data, top_skus):
    total_sales, total_commission, total_logistics, total_orders = report_data
    text = f"""📊 <b>Hisobot:</b>
🗓 <b>Oraliq:</b> {start_date.strftime(DATE_FORMAT)} - {end_date.strftime(DATE_FORMAT)}
📦 <b>Mahsulotlar soni:</b> {int(total_orders)}
💰 <b>Umumiy savdo:</b> {int(total_sales):,} so'm
🏦 <b>Komissiya:</b> {int(total_commission):,} so'm
🚚 <b>Logistika:</b> {int(total_logistics):,} so'm
"""
    if not top_skus.empty:
        text += "\n<b>Top 3 SKU:</b>\n"
        for sku, amount in top_skus.items():
            text += f"🔹 {sku}: {int(amount):,} so'm\n"
    return text

# --- /start komandasi ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Salom! Hisobot olish uchun quyidagi tugmadan foydalaning.",
        reply_markup=main_keyboard
    )

# --- "Hisobot olish" tugmasi ---
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "Hisobot olish":
        await update.message.reply_text(
            "Vaqt oralig'ini tanlang:",
            reply_markup=get_time_range_keyboard()
        )
    else:
        # custom oralig'i bo‘lsa
        if context.user_data.get("awaiting_custom_range"):
            try:
                start_str, end_str = update.message.text.split(" - ")
                start_date = datetime.strptime(start_str.strip(), DATE_FORMAT)
                end_date = datetime.strptime(end_str.strip(), DATE_FORMAT)

                report_data, top_skus = fetch_report(start_date, end_date)
                if report_data:
                    text = format_report(start_date, end_date, report_data, top_skus)
                    await update.message.reply_text(text, parse_mode="HTML")
                else:
                    await update.message.reply_text("Hisobot uchun ma'lumot topilmadi.")
            except Exception as e:
                logging.error(e)
                await update.message.reply_text("❌ Format xato. To‘g‘ri format: YYYY-MM-DD - YYYY-MM-DD")
            finally:
                context.user_data["awaiting_custom_range"] = False
        else:
            await update.message.reply_text("Hisobot olish uchun 'Hisobot olish' tugmasini bosing.")

# --- Inline tugma ishlovchi ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    today = datetime.now()
    if query.data == "today":
        start_date = today.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = today
    elif query.data == "yesterday":
        start_date = (today - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
    elif query.data == "1week":
        start_date = today - timedelta(days=7)
        end_date = today
    elif query.data == "2weeks":
        start_date = today - timedelta(days=14)
        end_date = today
    elif query.data == "1month":
        start_date = today - timedelta(days=30)
        end_date = today
    elif query.data == "custom":
        context.user_data["awaiting_custom_range"] = True
        await query.message.reply_text("Ixtiyoriy vaqt oralig'ini kiriting.\nMasalan: 2025-04-01 - 2025-04-27")
        return
    else:
        await query.message.reply_text("Noto‘g‘ri tanlov.")
        return

    report_data, top_skus = fetch_report(start_date, end_date)
    if report_data:
        text = format_report(start_date, end_date, report_data, top_skus)
        await query.message.reply_text(text, parse_mode="HTML")
    else:
        await query.message.reply_text("Hisobot uchun ma'lumot topilmadi.")

# --- Asosiy ishga tushirish ---
def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
