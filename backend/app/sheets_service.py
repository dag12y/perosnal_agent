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


def add_expense(category: str, amount: float, description: str = ""):
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet.append_row([date, category, amount, description])


def _is_income(category: str) -> bool:
    return str(category).strip().lower() == "income"


def get_monthly_summary():
    records = sheet.get_all_records()
    expenses_by_category = {}
    total_income = 0.0
    total_expense = 0.0

    current_month = datetime.now().strftime("%Y-%m")

    for row in records:
        if row["Date"].startswith(current_month):
            category = row["Category"]
            amount = float(row["Amount"])
            if _is_income(category):
                total_income += amount
            else:
                total_expense += amount
                expenses_by_category[category] = expenses_by_category.get(category, 0) + amount

    return {
        "expenses_by_category": expenses_by_category,
        "total_income": total_income,
        "total_expense": total_expense,
        "net_balance": total_income - total_expense,
    }


def get_balance_summary():
    records = sheet.get_all_records()

    total_income = 0.0
    total_expense = 0.0

    for row in records:
        category = row.get("Category", "")
        amount = float(row.get("Amount", 0) or 0)
        if _is_income(category):
            total_income += amount
        else:
            total_expense += amount

    return {
        "total_income": total_income,
        "total_expense": total_expense,
        "net_balance": total_income - total_expense,
    }
