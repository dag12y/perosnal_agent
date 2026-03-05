from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)
from app.bot import (
    balance,
    category_chosen,
    handle_message,
    list_budgets,
    quick_expense,
    quick_income,
    set_budget,
    start,
    summary,
    weekly,
)
from app.config import TELEGRAM_TOKEN


def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("summary", summary))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("setbudget", set_budget))
    app.add_handler(CommandHandler("budgets", list_budgets))
    app.add_handler(CommandHandler("weekly", weekly))
    app.add_handler(CommandHandler("e", quick_expense))
    app.add_handler(CommandHandler("i", quick_income))
    app.add_handler(CallbackQueryHandler(category_chosen))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()


if __name__ == "__main__":
    main()
