import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from app.config import SHEET_NAME

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
creds = Credentials.from_service_account_file(
    "credentials.json",
    scopes=SCOPES
)

client = gspread.authorize(creds)
sheet = client.open(SHEET_NAME).sheet1


def add_expense(category: str, amount: float):
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet.append_row([date, category, amount])


def get_monthly_summary():
    records = sheet.get_all_records()
    summary = {}

    current_month = datetime.now().strftime("%Y-%m")

    for row in records:
        if row["Date"].startswith(current_month):
            category = row["Category"]
            amount = float(row["Amount"])
            summary[category] = summary.get(category, 0) + amount

    return summary