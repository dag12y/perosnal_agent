from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from app.sheets_service import add_expense, get_monthly_summary


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().lower()

    if text == "summary":
        summary = get_monthly_summary()
        if not summary:
            await update.message.reply_text("No expenses this month.")
            return

        response = "📊 Monthly Summary:\n"
        for category, total in summary.items():
            response += f"{category}: {total} ETB\n"

        await update.message.reply_text(response)
        return

    parts = text.split()

    if len(parts) != 2:
        await update.message.reply_text(
            "Usage:\nfood 120\ntransport 50\n\nOr type: summary"
        )
        return

    category, amount = parts

    try:
        amount = float(amount)
    except ValueError:
        await update.message.reply_text("Amount must be a number.")
        return

    add_expense(category, amount)

    await update.message.reply_text(
        f"Saved ✅ {category} - {amount} ETB"
    )