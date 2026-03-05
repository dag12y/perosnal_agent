from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from app.sheets_service import add_expense, get_balance_summary, get_monthly_summary

# Temporary storage for user inputs
user_data = {}

# Step 1: Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_data[chat_id] = {"category": None, "amount": None, "description": None}

    # Category buttons
    categories = ["Food", "Transport", "Coffee", "Shopping", "Other", "Income"]
    keyboard = [[InlineKeyboardButton(cat, callback_data=cat)] for cat in categories]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("Choose a category:", reply_markup=reply_markup)

# Step 2: Handle category button click
async def category_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    category = query.data
    chat_id = query.message.chat_id

    # Save category
    user_data[chat_id]["category"] = category

    # Ask for amount
    await query.message.reply_text(f"Category '{category}' selected. Enter the amount:")

# Step 3: Handle text messages (amount or description)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    text = update.message.text.strip()

    if chat_id not in user_data:
        await update.message.reply_text("Send /start to log an expense.")
        return

    data = user_data[chat_id]

    if data["category"] is None:
        await update.message.reply_text("Choose a category first from /start.")
        return

    # Step 3a: Enter amount
    if data["amount"] is None:
        try:
            amount = float(text)
            if amount <= 0:
                await update.message.reply_text("Amount must be greater than 0.")
                return
            data["amount"] = amount
            await update.message.reply_text("Enter description (optional, or type '-' to skip):")
        except ValueError:
            await update.message.reply_text("Please enter a valid number for amount.")
        return

    # Step 3b: Enter description
    if data["description"] is None:
        description = "" if text == "-" else text
        data["description"] = description

        # Save to Google Sheet
        add_expense(data["category"], data["amount"], data["description"])

        await update.message.reply_text(
            f"Saved ✅ {data['category']} - {data['amount']} ETB"
            + (f" | {data['description']}" if data['description'] else "")
        )

        # Clear user data
        user_data.pop(chat_id)
        return

# Step 4: Monthly summary
async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    await update.message.reply_text(response)


async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    balance_data = get_balance_summary()
    response = (
        "💰 Balance Overview:\n"
        f"Total Income: {balance_data['total_income']:.2f} ETB\n"
        f"Total Expense: {balance_data['total_expense']:.2f} ETB\n"
        f"Net Balance: {balance_data['net_balance']:.2f} ETB"
    )
    await update.message.reply_text(response)
