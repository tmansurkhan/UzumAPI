import os
import json
import requests
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

# --- Muhit o'zgaruvchilarini yuklash (.env fayldan) ---
load_dotenv()

# --- Google Sheets credential sozlamalari ---
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

with open("service_account.json") as f:
    service_account_info = json.load(f)

creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPE)
client = gspread.authorize(creds)

# --- "Uzum API" faylidan "nakladnoy" varog'ini ochish ---
try:
    spreadsheet = client.open("Uzum API")
    worksheet = spreadsheet.worksheet("nakladnoy")
except gspread.SpreadsheetNotFound:
    print("❌ 'Uzum API' nomli fayl topilmadi.")
    exit()
except gspread.WorksheetNotFound:
    print("❌ 'nakladnoy' nomli varaq topilmadi.")
    exit()

# --- API so'rovi uchun URL qismlari ---
BASE_URL = "https://api-seller.uzum.uz/api/seller-openapi/v1/invoice"
PAGE = 0
SIZE = 5000
URL = f"{BASE_URL}?size={SIZE}&page={PAGE}"

headers = {
    "accept": "*/*",
    "Authorization": "OsfBx+VPNzoViSLx20H8RcTEKqJtoMOEzDokHG3sqN8="
}

# --- API chaqiruvi ---
response = requests.get(URL, headers=headers)

if response.status_code != 200:
    print(f"❌ API xatosi: {response.status_code} - {response.text}")
    exit()

# --- JSON javobni tahlil qilish ---
invoices = response.json()

if not isinstance(invoices, list):
    print("❌ Noto'g'ri javob formati: list kutilgan edi.")
    exit()

if not invoices:
    print("📭 Fakturalar topilmadi.")
    exit()

# --- Jadval sarlavhalari ---
headers_row = [
    "InvoiceID", "InvoiceNumber", "DateCreated", "Status",
    "ShopTitle", "StockTitle", "TotalAccepted", "ProductTitle",
    "SkuTitle", "QuantityAccepted", "PurchasePrice"
]

rows = []

# --- Ma'lumotlarni yig'ish ---
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
worksheet.append_row(headers_row)
worksheet.append_rows(rows)

print("✅ Faktura ma'lumotlari 'nakladnoy' varog'iga muvaffaqiyatli yozildi.")
