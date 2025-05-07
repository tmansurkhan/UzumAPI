import os
import json
import requests
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
from datetime import datetime

# --- Muhit o'zgaruvchilarini yuklash ---
load_dotenv()

# --- Google Sheets credential ---
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

with open("service_account.json") as f:
    service_account_info = json.load(f)

creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPE)
client = gspread.authorize(creds)

# --- "nakladnoy" faylini ochish ---
spreadsheet = client.open("nakladnoy")
worksheet = spreadsheet.sheet1

# --- Uzum API so'rovi ---
headers = {
    "accept": "*/*",
    "Authorization": "OsfBx+VPNzoViSLx20H8RcTEKqJtoMOEzDokHG3sqN8="
}
response = requests.get("https://api-seller.uzum.uz/api/seller-openapi/v1/invoice?size=50&page=0", headers=headers)

if response.status_code != 200:
    print(f"❌ API xatosi: {response.status_code} - {response.text}")
    exit()

invoices = response.json().get("content", [])
if not invoices:
    print("📭 Hech qanday faktura topilmadi.")
    exit()

# --- Sarlavhalarni tayyorlash ---
headers = [
    "InvoiceID", "InvoiceNumber", "DateCreated", "Status",
    "ShopTitle", "StockTitle", "TotalAccepted", "ProductTitle",
    "SkuTitle", "QuantityAccepted", "PurchasePrice"
]

rows = []

# --- Fakturalarni ajratib olish ---
for invoice in invoices:
    invoice_id = invoice.get("id")
    invoice_number = invoice.get("invoiceNumber")
    date_created = invoice.get("dateCreated")
    status = invoice.get("invoiceStatus", {}).get("text")
    shop_title = invoice.get("shopTitle")
    stock_title = invoice.get("stock", {}).get("title")
    total_accepted = invoice.get("totalAccepted")

    for product in invoice.get("productForInvoiceDto", []):
        product_title = product.get("productTitle")
        for sku in product.get("skuForInvoiceDtoList", []):
            sku_title = sku.get("skuTitle")
            quantity = sku.get("quantityAccepted")
            price = sku.get("purchasePrice")

            rows.append([
                invoice_id, invoice_number, date_created, status,
                shop_title, stock_title, total_accepted,
                product_title, sku_title, quantity, price
            ])

# --- Google Sheets'ga yozish ---
worksheet.clear()
worksheet.append_row(headers)
worksheet.append_rows(rows)

print("✅ Faktura ma'lumotlari 'nakladnoy' fayliga muvaffaqiyatli yozildi.")
