import os
import requests
import gspread
from google.oauth2.service_account import Credentials
from collections import defaultdict
from datetime import datetime
import time
from google.auth.transport.requests import Request

# Google Sheets'ga ulanish
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# GitHub Secrets'dan `service_account.json` ma'lumotlarini o'qish
google_credentials = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')

if not google_credentials:
    print("❌ GOOGLE_APPLICATION_CREDENTIALS muhit o'zgaruvchisi o'rnatilmagan.")
    exit(1)

# JSON faylini sozlash
creds = Credentials.from_service_account_info(
    google_credentials, scopes=SCOPE)
client = gspread.authorize(creds)

spreadsheet = client.open("Uzum API")

# Sheetni olish yoki yaratish
def get_or_create_sheet(title, rows=100, cols=10):
    try:
        return spreadsheet.worksheet(title)
    except gspread.exceptions.WorksheetNotFound:
        return spreadsheet.add_worksheet(title=title, rows=rows, cols=cols)

# --- 1. Shop ma'lumotlari --- 
shop_sheet = get_or_create_sheet("ShopID", 100, 2)
shop_sheet.clear()

url = "https://api-seller.uzum.uz/api/seller-openapi/v1/shops"
headers = {
    "Authorization": "OsfBx+VPNzoViSLx20H8RcTEKqJtoMOEzDokHG3sqN8=",
    "Accept": "*/*"
}

response = requests.get(url, headers=headers)
shop_id_name_map = {}

if response.status_code == 200:
    shops = response.json()
    rows = [["id", "name"]]
    for shop in shops:
        shop_id = str(shop.get("id"))
        shop_name = shop.get("name")
        shop_id_name_map[shop_id] = shop_name
        rows.append([shop_id, shop_name])
    shop_sheet.append_rows(rows, value_input_option="RAW")
    print("✅ Shop ma’lumotlari ShopID varag‘iga yozildi.")
else:
    print(f"❌ API xatolik: {response.status_code}")

# --- 2. Orders ma'lumotlari ---
orders_sheet = get_or_create_sheet("Orders", 100, 13)
orders_sheet.clear()
orders_sheet.append_row([ ... ])  # Bu yerda faqat mavjud qismni davom ettiraman

url = "https://api-seller.uzum.uz/api/seller-openapi/v1/finance/orders"
params = {"page": 0, "size": 10000, "group": "false", "shopIds": [12488, 20002, 23251, 33077, 33863, 42620]}

total_orders = 0
while True:
    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        print(f"❌ Xatolik yuz berdi: {response.status_code}")
        break

    data = response.json()
    orderItems = data.get("orderItems", [])
    if not orderItems:
        print("✅ Barcha ma’lumotlar yuklandi.")
        break

    rows = []
    for item in orderItems:
        order_id = item.get("id")
        status = item.get("status")
        shopId = str(item.get("shopId"))
        title = item.get("skuTitle")
        sell_price = item.get("sellPrice")
        commission = item.get("commission")
        logistic_fee = item.get("logisticDeliveryFee")
        amount = item.get("amount")
        seller_profit = item.get("sellerProfit")
        withdrawn_profit = item.get("withdrawnProfit")
        purchase_price = item.get("purchasePrice")
        image_url = item.get("productImage", {}).get("photo", {}).get("800", {}).get("high", "N/A")
        date = datetime.fromtimestamp(item.get("date", 0) / 1000).strftime('%Y-%m-%d %H:%M')  # ✅ to‘liq sana + vaqt
        rows.append([ ... ])  # Davom eting

    orders_sheet.append_rows(rows, value_input_option="RAW")
    total_orders += len(rows)
    print(f"{len(rows)} ta buyurtma qo‘shildi. Jami: {total_orders} ta.")
    time.sleep(2)

    if len(orderItems) < params["size"]:
        break
    params["page"] += 1

# --- 3. Aggregatsiya --- qismni davom ettiring
