from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from app.sheets_service import (
    add_expense,
    get_balance_summary,
    get_current_month_category_expense,
    get_monthly_summary,
    get_weekly_report,
)

# Temporary storage for user inputs
user_data = {}
user_budgets = {}
budget_alert_state = {}

CATEGORIES = ["Food", "Transport", "Coffee", "Shopping", "Other", "Income"]
NON_INCOME_CATEGORIES = [category for category in CATEGORIES if category != "Income"]


def _get_chat_id(update: Update):
    chat = update.effective_chat
    return chat.id if chat else None


def _get_message(update: Update):
    return update.effective_message


def _normalize_category(value: str) -> str:
    return str(value).strip().lower()


def _display_category(value: str) -> str:
    normalized = _normalize_category(value)
    for category in CATEGORIES:
        if _normalize_category(category) == normalized:
            return category
    return str(value).strip().title()


def _parse_positive_amount(value: str):
    try:
        amount = float(value)
    except ValueError:
        return None

    if amount <= 0:
        return None

    return amount


async def _send_budget_alert_if_needed(chat_id: int, category: str, message):
    normalized_category = _normalize_category(category)
    if normalized_category == "income":
        return

    budgets = user_budgets.get(chat_id, {})
    budget = budgets.get(normalized_category)
    if not budget:
        return

    spent = get_current_month_category_expense(category)
    ratio = spent / budget if budget > 0 else 0
    month_key = message.date.strftime("%Y-%m")

    key_80 = (chat_id, month_key, normalized_category, "80")
    key_100 = (chat_id, month_key, normalized_category, "100")

    if ratio >= 1.0 and not budget_alert_state.get(key_100):
        budget_alert_state[key_80] = True
        budget_alert_state[key_100] = True
        await message.reply_text(
            f"🚨 Budget reached for {_display_category(category)}: "
            f"{spent:.2f}/{budget:.2f} ETB ({ratio * 100:.1f}%)"
        )
    elif ratio >= 0.8 and not budget_alert_state.get(key_80):
        budget_alert_state[key_80] = True
        await message.reply_text(
            f"⚠️ You used 80%+ of your {_display_category(category)} budget: "
            f"{spent:.2f}/{budget:.2f} ETB ({ratio * 100:.1f}%)"
        )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = _get_message(update)
    chat_id = _get_chat_id(update)
    if message is None or chat_id is None:
        return

    user_data[chat_id] = {"category": None, "amount": None, "description": None}

    keyboard = [[InlineKeyboardButton(category, callback_data=category)] for category in CATEGORIES]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await message.reply_text(
        "Choose a category:\n"
        "Quick add:\n"
        "/e <category> <amount> [description]\n"
        "/i <amount> [description]",
        reply_markup=reply_markup,
    )


async def category_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query is None or query.message is None:
        return

    await query.answer()
    category = query.data
    chat_id = query.message.chat_id

    if chat_id not in user_data:
        user_data[chat_id] = {"category": None, "amount": None, "description": None}

    user_data[chat_id]["category"] = category
    await query.message.reply_text(f"Category '{category}' selected. Enter the amount:")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = _get_message(update)
    chat_id = _get_chat_id(update)
    if message is None or chat_id is None or not message.text:
        return

    text = message.text.strip()

    if chat_id not in user_data:
        await message.reply_text("Send /start or use quick add: /e or /i.")
        return

    data = user_data[chat_id]

    if data["category"] is None:
        await message.reply_text("Choose a category first from /start.")
        return

    if data["amount"] is None:
        amount = _parse_positive_amount(text)
        if amount is None:
            await message.reply_text("Please enter a valid positive number for amount.")
            return

        data["amount"] = amount
        await message.reply_text("Enter description (optional, or type '-' to skip):")
        return

    if data["description"] is None:
        description = "" if text == "-" else text
        data["description"] = description

        add_expense(data["category"], data["amount"], data["description"])

        await message.reply_text(
            f"Saved ✅ {data['category']} - {data['amount']:.2f} ETB"
            + (f" | {data['description']}" if data["description"] else "")
        )
        await _send_budget_alert_if_needed(chat_id, data["category"], message)

        user_data.pop(chat_id)


async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = _get_message(update)
    if message is None:
        return

    summary_data = get_monthly_summary()
    expenses_by_category = summary_data["expenses_by_category"]
    total_income = summary_data["total_income"]
    total_expense = summary_data["total_expense"]
    net_balance = summary_data["net_balance"]

    response = "📊 Monthly Summary:\n"
    if expenses_by_category:
        response += "\nExpenses by category:\n"
        for category, total in expenses_by_category.items():
            response += f"- {category}: {total:.2f} ETB\n"
    else:
        response += "\nNo expenses recorded this month.\n"

    response += f"\nTotal Income: {total_income:.2f} ETB\n"
    response += f"Total Expense: {total_expense:.2f} ETB\n"
    response += f"Net Balance: {net_balance:.2f} ETB"

    await message.reply_text(response)


async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = _get_message(update)
    if message is None:
        return

    balance_data = get_balance_summary()
    response = (
        "💰 Balance Overview:\n"
        f"Total Income: {balance_data['total_income']:.2f} ETB\n"
        f"Total Expense: {balance_data['total_expense']:.2f} ETB\n"
        f"Net Balance: {balance_data['net_balance']:.2f} ETB"
    )
    await message.reply_text(response)


async def set_budget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = _get_message(update)
    chat_id = _get_chat_id(update)
    if message is None or chat_id is None:
        return

    args = context.args

    if len(args) < 2:
        await message.reply_text("Usage: /setbudget <category> <amount>")
        return

    category = _normalize_category(args[0])
    valid_categories = {_normalize_category(value) for value in NON_INCOME_CATEGORIES}
    if category not in valid_categories:
        await message.reply_text(
            "Invalid category. Use one of: Food, Transport, Coffee, Shopping, Other."
        )
        return

    amount = _parse_positive_amount(args[1])
    if amount is None:
        await message.reply_text("Amount must be a positive number.")
        return

    if chat_id not in user_budgets:
        user_budgets[chat_id] = {}
    user_budgets[chat_id][category] = amount

    await message.reply_text(
        f"Budget set ✅ {_display_category(category)}: {amount:.2f} ETB for this month."
    )


async def list_budgets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = _get_message(update)
    chat_id = _get_chat_id(update)
    if message is None or chat_id is None:
        return

    budgets = user_budgets.get(chat_id, {})

    if not budgets:
        await message.reply_text(
            "No budgets set.\nSet one with: /setbudget <category> <amount>"
        )
        return

    response = "🎯 Budget Status (current month):\n"
    for category_key, budget in budgets.items():
        category_name = _display_category(category_key)
        spent = get_current_month_category_expense(category_name)
        percent = (spent / budget) * 100 if budget > 0 else 0
        response += (
            f"- {category_name}: {spent:.2f}/{budget:.2f} ETB "
            f"({percent:.1f}%)\n"
        )

    await message.reply_text(response)


async def weekly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = _get_message(update)
    if message is None:
        return

    data = get_weekly_report()
    top = data["top_category"]

    response = (
        "📅 Weekly Report (last 7 days)\n"
        f"Range: {data['current_start']} to {data['current_end']}\n"
        f"Total Spent: {data['current_total']:.2f} ETB\n"
    )

    if top:
        response += f"Top Category: {top[0]} ({top[1]:.2f} ETB)\n"
    else:
        response += "Top Category: No expenses this week\n"

    if data["previous_total"] == 0 and data["current_total"] == 0:
        response += "Trend: No expenses in both weeks."
    elif data["difference"] > 0:
        response += f"Trend: Improved ✅ You spent {data['difference']:.2f} ETB less than last week."
    elif data["difference"] < 0:
        response += f"Trend: Higher spending ⚠️ You spent {abs(data['difference']):.2f} ETB more than last week."
    else:
        response += "Trend: Same spending as last week."

    await message.reply_text(response)


async def quick_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = _get_message(update)
    chat_id = _get_chat_id(update)
    if message is None or chat_id is None:
        return

    args = context.args
    if len(args) < 2:
        await message.reply_text("Usage: /e <category> <amount> [description]")
        return

    category = _display_category(args[0])
    if _normalize_category(category) == "income":
        await message.reply_text("Use /i for income entries.")
        return

    amount = _parse_positive_amount(args[1])
    if amount is None:
        await message.reply_text("Amount must be a positive number.")
        return

    description = " ".join(args[2:]).strip()
    add_expense(category, amount, description)

    await message.reply_text(
        f"Saved ✅ {category} - {amount:.2f} ETB"
        + (f" | {description}" if description else "")
    )
    await _send_budget_alert_if_needed(chat_id, category, message)


async def quick_income(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = _get_message(update)
    if message is None:
        return

    args = context.args
    if not args:
        await message.reply_text("Usage: /i <amount> [description]")
        return

    amount = _parse_positive_amount(args[0])
    if amount is None:
        await message.reply_text("Amount must be a positive number.")
        return

    description = " ".join(args[1:]).strip()
    add_expense("Income", amount, description)
    await message.reply_text(
        f"Saved ✅ Income - {amount:.2f} ETB"
        + (f" | {description}" if description else "")
    )
