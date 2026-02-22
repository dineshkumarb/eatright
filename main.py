import logging
import os

from dotenv import load_dotenv
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.handlers import (
    start_command,
    help_command,
    history_command,
    stats_command,
    tips_command,
    streak_command,
    compare_command,
    handle_photo,
    handle_callback,
)
from core.receipt_parser import ReceiptParser
from core.diet_advisor import DietAdvisor
from core.predictive_engine import PredictiveEngine
from database.models import init_db
from database.repository import Repository

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def send_weekly_reports(app):
    repo: Repository = app.bot_data["repo"]
    engine = PredictiveEngine(repo)

    from database.models import User
    with repo._session_factory() as session:
        users = session.query(User).all()
        user_ids = [u.id for u in users]

    for user_id in user_ids:
        try:
            report = engine.generate_weekly_report(user_id)
            if report:
                await app.bot.send_message(
                    chat_id=user_id,
                    text=report,
                    parse_mode="Markdown",
                )
        except Exception as e:
            logger.warning("Failed to send weekly report to %s: %s", user_id, e)


def main():
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    gemini_key = os.getenv("GEMINI_API_KEY")
    database_url = os.getenv("DATABASE_URL", "sqlite:///./groceries.db")

    if not telegram_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set in .env")
    if not gemini_key:
        raise RuntimeError("GEMINI_API_KEY is not set in .env")

    engine, Session = init_db(database_url)
    repo = Repository(Session)
    parser = ReceiptParser(gemini_key)
    advisor = DietAdvisor(gemini_key)

    app = ApplicationBuilder().token(telegram_token).build()

    app.bot_data["repo"] = repo
    app.bot_data["parser"] = parser
    app.bot_data["advisor"] = advisor

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("history", history_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("tips", tips_command))
    app.add_handler(CommandHandler("streak", streak_command))
    app.add_handler(CommandHandler("compare", compare_command))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(handle_callback))

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        send_weekly_reports,
        "cron",
        day_of_week="sun",
        hour=10,
        minute=0,
        args=[app],
    )
    scheduler.start()

    logger.info("Bot started! Polling for messages...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
