import requests
import gspread
from google.oauth2.service_account import Credentials
from collections import defaultdict
from datetime import datetime
import time

# Google Sheets'ga ulanish
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_file("service_account.json", scopes=SCOPE)
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
orders_sheet.append_row([
    "Order ID", "Status", "shopId", "ProductTitle", "SellPrice", "Commission", "logisticDeliveryFee",
    "amount", "SellerProfit", "withdrawnProfit", "purchasePrice", "Image URL", "date"
])

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
        rows.append([
            order_id, status, shopId, title, sell_price, commission, logistic_fee, amount,
            seller_profit, withdrawn_profit, purchase_price, image_url, date
        ])

    orders_sheet.append_rows(rows, value_input_option="RAW")
    total_orders += len(rows)
    print(f"{len(rows)} ta buyurtma qo‘shildi. Jami: {total_orders} ta.")
    time.sleep(2)

    if len(orderItems) < params["size"]:
        break
    params["page"] += 1

# --- 3. Aggregatsiya: date_info_total ---
date_info_sheet = get_or_create_sheet("date_info_total", 100, 10)
date_info_sheet.clear()
date_info_sheet.append_row([
    "Date", "SKU", "Shop ID", "Quantity Sold", "Total Sales", "Purchase Total",
    "Seller Profit Total", "Commission Total", "Delivery Fee Total", "Image URL"
])

data = orders_sheet.get_all_values()
sales_data = {}

for row in data[1:]:
    try:
        full_date = row[12]
        date = full_date.split(" ")[0]  # ✅ faqat sana (YYYY-MM-DD)
        sku = row[3]
        price = float(row[4])
        commission = float(row[5])
        delivery_fee = float(row[6])
        quantity = int(row[7])
        seller_profit = float(row[8])
        purchase_price = float(row[10])
        image_url = row[11]
        shop_id = row[2]

        if image_url.startswith('=IMAGE("'):
            image_url = image_url.replace('=IMAGE("', '').rstrip('")')

        key = f"{date}-{sku}-{shop_id}"

        if key not in sales_data:
            sales_data[key] = {
                "date": date, "sku": sku, "shopId": shop_id, "quantity": 0, "totalSales": 0,
                "purchaseTotal": 0, "sellerProfitTotal": 0, "commissionTotal": 0,
                "deliveryFeeTotal": 0, "image": image_url
            }

        sales_data[key]["quantity"] += quantity
        sales_data[key]["totalSales"] += price * quantity
        sales_data[key]["purchaseTotal"] += purchase_price * quantity
        sales_data[key]["sellerProfitTotal"] += seller_profit * quantity
        sales_data[key]["commissionTotal"] += commission * quantity
        sales_data[key]["deliveryFeeTotal"] += delivery_fee * quantity

    except (IndexError, ValueError) as e:
        print(f"⚠️ Ma’lumotni o‘qishda xatolik: {e}")
        continue

batch_rows = []
for item in sales_data.values():
    batch_rows.append([
        item["date"], item["sku"], item["shopId"], item["quantity"], item["totalSales"],
        item["purchaseTotal"], item["sellerProfitTotal"], item["commissionTotal"], item["deliveryFeeTotal"],
        item["image"]
    ])

date_info_sheet.append_rows(batch_rows, value_input_option="RAW")
print("✅ Aggregatsiya natijalari date_info_total varag‘iga yozildi.")

# --- 4. Kunlik umumiy: daily_info_total ---
daily_sheet = get_or_create_sheet("daily_info_total", 100, 11)
daily_sheet.clear()
daily_sheet.append_row([
    "Date", "SKU Prefix", "Shop Name(s)", "Quantity", "Total Sales", "Total Purchase Price",
    "Total Seller Profit", "Total Commission", "Total Logistic Fee", "Image"
])

data = date_info_sheet.get_all_values()
aggregated = defaultdict(lambda: {
    "quantity": 0, "sales": 0, "purchase": 0, "profit": 0,
    "commission": 0, "logistics": 0, "image": "", "shopIds": set()
})

for row in data[1:]:
    date, sku_full = row[0], row[1]
    sku_prefix = "-".join(sku_full.split("-")[:2]) if "-" in sku_full else sku_full
    key = f"{date}_{sku_prefix}"

    aggregated[key]["quantity"] += int(row[3])
    aggregated[key]["sales"] += float(row[4])
    aggregated[key]["purchase"] += float(row[5])
    aggregated[key]["profit"] += float(row[6])
    aggregated[key]["commission"] += float(row[7])
    aggregated[key]["logistics"] += float(row[8])
    aggregated[key]["shopIds"].add(row[2])
    if not aggregated[key]["image"]:
        aggregated[key]["image"] = row[9]

batch_rows = []
for key, values in aggregated.items():
    date, sku_prefix = key.split("_", 1)
    shop_names = [shop_id_name_map.get(shop_id, f"ID:{shop_id}") for shop_id in values["shopIds"]]
    batch_rows.append([
        date, sku_prefix, ", ".join(sorted(shop_names)), values["quantity"], values["sales"], values["purchase"],
        values["profit"], values["commission"], values["logistics"],
        f'=IMAGE("{values["image"]}")'
    ])

daily_sheet.append_rows(batch_rows, value_input_option="USER_ENTERED")
print("✅ Kunlik umumiy ma’lumotlar daily_info_total varag‘iga yozildi.")
