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
from dotenv import load_dotenv  # .env faylini yuklash uchun kutubxona

# --- .env faylni yuklash ---
load_dotenv()

# --- Logger ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- Google Sheets bilan ulanish ---
with open("service_account.json") as f:
    service_account_info = json.load(f)

uzum_api_token = os.getenv("UZUM_API_TOKEN")

SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPE)
client = gspread.authorize(creds)
spreadsheet = client.open("Uzum API")
ORDERS_SHEET_NAME = "Orders"

# --- Telegram token va chat ID --- 
# .env faylidan o‘zgaruvchilarni olish
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

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
    rows = orders_sheet.get_all_values()
    if not rows or len(rows) < 2:
        return None, None

    headers = rows[0]
    data = rows[1:]
    df = pd.DataFrame(data, columns=headers)

    # Vaqt ustuni (index orqali)
    order_time_index = headers.index("M")
    df['Order Time'] = pd.to_datetime([r[order_time_index] for r in data], errors='coerce')
    df = df.dropna(subset=['Order Time'])

    mask = (df['Order Time'] >= start_date) & (df['Order Time'] <= end_date)
    filtered = df.loc[mask]
    if filtered.empty:
        return None, None

    # Ustun indekslarini aniqlash
    price_i = headers.index("E")
    comm_i  = headers.index("F")
    log_i   = headers.index("G")
    qty_i   = headers.index("H")
    sku_i   = headers.index("D")

    # Sonli qiymatlar
    filtered['E'] = pd.to_numeric(filtered.iloc[:, price_i], errors='coerce').fillna(0)
    filtered['F'] = pd.to_numeric(filtered.iloc[:, comm_i ], errors='coerce').fillna(0)
    filtered['G'] = pd.to_numeric(filtered.iloc[:, log_i  ], errors='coerce').fillna(0)
    filtered['H'] = pd.to_numeric(filtered.iloc[:, qty_i  ], errors='coerce').fillna(0)

    total_sales      = (filtered['E'] * filtered['H']).sum()
    total_commission = (filtered['F'] * filtered['H']).sum()
    total_logistics  = (filtered['G'] * filtered['H']).sum()
    total_orders     = filtered['H'].sum()

    filtered['total_sold_price'] = filtered['E'] * filtered['H']
    top_skus = (
        filtered.groupby(filtered.columns[sku_i])['total_sold_price']
        .sum().sort_values(ascending=False).head(3)
    )

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
        for sku, amt in top_skus.items():
            text += f"🔹 {sku}: {int(amt):,} so'm\n"
    return text

# --- /start komandasi ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Salom! Hisobot olish uchun quyidagi tugmadan foydalaning.",
        reply_markup=main_keyboard
    )

# --- Message handler ---
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "Hisobot olish":
        await update.message.reply_text("Vaqt oralig'ini tanlang:", reply_markup=get_time_range_keyboard())
    else:
        if context.user_data.get("awaiting_custom_range"):
            try:
                s, e = update.message.text.split(" - ")
                sd = datetime.strptime(s.strip(), DATE_FORMAT)
                ed = datetime.strptime(e.strip(), DATE_FORMAT)
                report, top3 = fetch_report(sd, ed)
                if report:
                    await update.message.reply_text(format_report(sd, ed, report, top3), parse_mode="HTML")
                else:
                    await update.message.reply_text("Ma'lumot topilmadi.")
            except Exception as err:
                logging.error(err)
                await update.message.reply_text("❌ Format: YYYY-MM-DD - YYYY-MM-DD")
            finally:
                context.user_data["awaiting_custom_range"] = False
        else:
            await update.message.reply_text("Hisobot olish uchun tugmani bosing.")

# --- Inline tugmalarga handler ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    now = datetime.now()
    if query.data == "today":
        sd = now.replace(hour=0, minute=0, second=0, microsecond=0); ed = now
    elif query.data == "yesterday":
        sd = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0); ed = sd + timedelta(days=1)
    elif query.data == "1week":
        sd, ed = now - timedelta(days=7), now
    elif query.data == "2weeks":
        sd, ed = now - timedelta(days=14), now
    elif query.data == "1month":
        sd, ed = now - timedelta(days=30), now
    elif query.data == "custom":
        context.user_data["awaiting_custom_range"] = True
        await query.message.reply_text("Iltimos: YYYY-MM-DD - YYYY-MM-DD formatda kiriting.")
        return
    else:
        await query.message.reply_text("Noto‘g‘ri tanlov."); return

    rpt, t3 = fetch_report(sd, ed)
    if rpt:
        await query.message.reply_text(format_report(sd, ed, rpt, t3), parse_mode="HTML")
    else:
        await query.message.reply_text("Ma'lumot topilmadi.")

# --- App boshqaruvi ---
def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
