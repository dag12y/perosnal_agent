from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from app.sheets_service import add_expense, get_monthly_summary

# Temporary storage for user inputs
user_data = {}

# Step 1: Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_data[chat_id] = {"category": None, "amount": None, "description": None}

    # Category buttons
    categories = ["Food", "Transport", "Coffee", "Shopping", "Other"]
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

    # Step 3a: Enter amount
    if data["amount"] is None:
        try:
            amount = float(text)
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
    if not summary_data:
        await update.message.reply_text("No expenses this month.")
        return

    response = "📊 Monthly Summary:\n"
    for category, total in summary_data.items():
        response += f"{category}: {total} ETB\n"

    await update.message.reply_text(response)

# Setup application
def main():
    from app.config import TELEGRAM_TOKEN

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("summary", summary))
    app.add_handler(CallbackQueryHandler(category_chosen))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()

if __name__ == "__main__":
    main()