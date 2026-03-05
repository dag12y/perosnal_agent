import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
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
BUDGET_SHEET_TITLE = "Budgets"
BUDGET_HEADERS = ["ChatId", "Category", "Amount", "UpdatedAt"]


def _normalize_category(value: str) -> str:
    return str(value).strip().lower()


def _get_or_create_budget_sheet():
    workbook = client.open(SHEET_NAME)
    try:
        ws = workbook.worksheet(BUDGET_SHEET_TITLE)
    except gspread.WorksheetNotFound:
        ws = workbook.add_worksheet(title=BUDGET_SHEET_TITLE, rows=1000, cols=4)

    first_row = ws.row_values(1)
    if first_row != BUDGET_HEADERS:
        ws.update("A1:D1", [BUDGET_HEADERS])
    return ws


budget_sheet = _get_or_create_budget_sheet()


def add_expense(category: str, amount: float, description: str = ""):
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet.append_row([date, category, amount, description])


def _is_income(category: str) -> bool:
    return str(category).strip().lower() == "income"


def _to_float(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _parse_date(value: str):
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError):
        return None


def get_monthly_summary():
    records = sheet.get_all_records()
    expenses_by_category = {}
    total_income = 0.0
    total_expense = 0.0

    current_month = datetime.now().strftime("%Y-%m")

    for row in records:
        if row["Date"].startswith(current_month):
            category = row["Category"]
            amount = _to_float(row["Amount"])
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
        amount = _to_float(row.get("Amount", 0))
        if _is_income(category):
            total_income += amount
        else:
            total_expense += amount

    return {
        "total_income": total_income,
        "total_expense": total_expense,
        "net_balance": total_income - total_expense,
    }


def get_current_month_category_expense(category: str) -> float:
    records = sheet.get_all_records()
    current_month = datetime.now().strftime("%Y-%m")
    target = str(category).strip().lower()
    total = 0.0

    for row in records:
        row_category = str(row.get("Category", "")).strip().lower()
        if row.get("Date", "").startswith(current_month) and row_category == target and not _is_income(row_category):
            total += _to_float(row.get("Amount", 0))

    return total


def get_weekly_report():
    records = sheet.get_all_records()
    now = datetime.now()

    current_start = (now - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
    current_end = now
    previous_start = (now - timedelta(days=13)).replace(hour=0, minute=0, second=0, microsecond=0)
    previous_end = (now - timedelta(days=7)).replace(hour=23, minute=59, second=59, microsecond=999999)

    current_total = 0.0
    previous_total = 0.0
    current_by_category = {}

    for row in records:
        category = row.get("Category", "")
        if _is_income(category):
            continue

        row_date = _parse_date(row.get("Date", ""))
        if row_date is None:
            continue

        amount = _to_float(row.get("Amount", 0))
        if current_start <= row_date <= current_end:
            current_total += amount
            current_by_category[category] = current_by_category.get(category, 0) + amount
        elif previous_start <= row_date <= previous_end:
            previous_total += amount

    top_category = None
    if current_by_category:
        top_category = max(current_by_category.items(), key=lambda item: item[1])

    return {
        "current_total": current_total,
        "previous_total": previous_total,
        "difference": previous_total - current_total,
        "current_start": current_start.strftime("%Y-%m-%d"),
        "current_end": current_end.strftime("%Y-%m-%d"),
        "top_category": top_category,
    }


def set_user_budget(chat_id: int, category: str, amount: float):
    records = budget_sheet.get_all_records()
    target_chat = str(chat_id)
    target_category = _normalize_category(category)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    found_row = None
    for idx, row in enumerate(records, start=2):
        row_chat = str(row.get("ChatId", "")).strip()
        row_category = _normalize_category(row.get("Category", ""))
        if row_chat == target_chat and row_category == target_category:
            found_row = idx
            break

    if found_row is None:
        budget_sheet.append_row([target_chat, category, amount, now])
    else:
        budget_sheet.update(
            f"A{found_row}:D{found_row}",
            [[target_chat, category, amount, now]],
        )


def get_user_budgets(chat_id: int):
    records = budget_sheet.get_all_records()
    target_chat = str(chat_id)
    budgets = {}

    for row in records:
        row_chat = str(row.get("ChatId", "")).strip()
        if row_chat != target_chat:
            continue

        category = str(row.get("Category", "")).strip()
        if not category:
            continue

        normalized = _normalize_category(category)
        budgets[normalized] = {
            "category": category,
            "amount": _to_float(row.get("Amount", 0)),
        }

    return budgets


def get_user_budget(chat_id: int, category: str):
    budgets = get_user_budgets(chat_id)
    data = budgets.get(_normalize_category(category))
    if not data:
        return None
    return data["amount"]
