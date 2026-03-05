from telegram.ext import ApplicationBuilder, MessageHandler, filters
from app.bot import handle_message
from app.config import TELEGRAM_TOKEN

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()