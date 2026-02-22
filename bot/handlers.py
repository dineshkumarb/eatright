import io
import logging
import time
from functools import wraps

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatAction, ParseMode

from bot.messages import (
    WELCOME_MESSAGE,
    HELP_MESSAGE,
    ANALYZING_MESSAGE,
    ERROR_RECEIPT_MESSAGE,
    RATE_LIMIT_MESSAGE,
    NO_HISTORY_MESSAGE,
    format_item_list,
    format_score_card,
    format_history,
    format_streak,
)
from bot.keyboards import main_menu_keyboard, after_analysis_keyboard
from core.receipt_parser import ReceiptParser
from core.nutritional_scorer import calculate_basket_score
from core.diet_advisor import DietAdvisor
from core.predictive_engine import PredictiveEngine
from charts.visualizer import generate_score_card, generate_trend_chart
from database.repository import Repository

logger = logging.getLogger(__name__)

_user_last_analysis: dict[int, float] = {}
RATE_LIMIT_SECONDS = 60


def _rate_limited(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        now = time.time()
        last = _user_last_analysis.get(user_id, 0)
        if now - last < RATE_LIMIT_SECONDS:
            await update.message.reply_text(RATE_LIMIT_MESSAGE)
            return
        _user_last_analysis[user_id] = now
        try:
            return await func(update, context)
        except Exception:
            _user_last_analysis[user_id] = 0
            raise
    return wrapper


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    repo: Repository = context.bot_data["repo"]
    user = update.effective_user
    repo.get_or_create_user(user.id, user.username, user.first_name)
    await update.message.reply_text(WELCOME_MESSAGE, parse_mode=ParseMode.MARKDOWN)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_MESSAGE, parse_mode=ParseMode.MARKDOWN)


async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    repo: Repository = context.bot_data["repo"]
    receipts = repo.get_user_receipts(update.effective_user.id, limit=5)
    text = format_history(receipts)
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    repo: Repository = context.bot_data["repo"]
    engine = PredictiveEngine(repo)
    trends = engine.get_user_trends(update.effective_user.id)

    if not trends["score_trend"]:
        await update.message.reply_text(NO_HISTORY_MESSAGE)
        return

    await context.bot.send_chat_action(update.effective_chat.id, ChatAction.UPLOAD_PHOTO)
    chart_bytes = generate_trend_chart(trends["score_trend"])
    await update.message.reply_photo(
        photo=io.BytesIO(chart_bytes),
        caption="📊 Your score trend over time",
    )


async def tips_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    repo: Repository = context.bot_data["repo"]
    advisor: DietAdvisor = context.bot_data["advisor"]
    engine = PredictiveEngine(repo)

    receipts = repo.get_user_receipts(update.effective_user.id, limit=5)
    if not receipts:
        await update.message.reply_text(NO_HISTORY_MESSAGE)
        return

    await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)

    import json
    latest = receipts[0]
    raw = json.loads(latest.raw_json) if latest.raw_json else {}
    score_report = raw.get("score", {})

    history = [
        {"date": r.receipt_date.isoformat() if r.receipt_date else "?",
         "grade": r.overall_grade, "score": r.overall_score}
        for r in receipts
    ]

    advice = await advisor.get_recommendations(score_report, history)
    await update.message.reply_text(advice, parse_mode=ParseMode.MARKDOWN)


async def streak_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    repo: Repository = context.bot_data["repo"]
    engine = PredictiveEngine(repo)
    trends = engine.get_user_trends(update.effective_user.id)
    text = format_streak(trends["streak"], trends["total_receipts"])
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def compare_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    repo: Repository = context.bot_data["repo"]
    engine = PredictiveEngine(repo)
    comparison = engine.get_comparison(update.effective_user.id)

    if not comparison:
        await update.message.reply_text(
            "📭 I need at least two receipts to compare. Send me more receipt photos!"
        )
        return

    await update.message.reply_text(f"```\n{comparison}\n```", parse_mode=ParseMode.MARKDOWN)


@_rate_limited
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    repo: Repository = context.bot_data["repo"]
    parser: ReceiptParser = context.bot_data["parser"]
    advisor: DietAdvisor = context.bot_data["advisor"]
    user = update.effective_user
    chat_id = update.effective_chat.id

    repo.get_or_create_user(user.id, user.username, user.first_name)

    status_msg = await update.message.reply_text(ANALYZING_MESSAGE)
    await context.bot.send_chat_action(chat_id, ChatAction.TYPING)

    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        image_data = await file.download_as_bytearray()

        parsed_data = await parser.parse_receipt_image(bytes(image_data))
    except (ValueError, RuntimeError) as e:
        logger.warning("Receipt parsing failed for user %s: %s", user.id, e)
        await status_msg.edit_text(ERROR_RECEIPT_MESSAGE, parse_mode=ParseMode.MARKDOWN)
        return
    except Exception as e:
        logger.error("Unexpected error parsing receipt: %s", e, exc_info=True)
        await status_msg.edit_text(ERROR_RECEIPT_MESSAGE, parse_mode=ParseMode.MARKDOWN)
        return

    score_report = calculate_basket_score(parsed_data.get("items", []))

    previous_receipts = repo.get_user_receipts(user.id, limit=1)
    previous_grade = previous_receipts[0].overall_grade if previous_receipts else None

    receipt = repo.save_receipt(user.id, parsed_data, score_report)

    await status_msg.delete()

    # Message 1: Item list
    item_list_text = format_item_list(parsed_data, score_report)
    await update.message.reply_text(item_list_text, parse_mode=ParseMode.MARKDOWN)

    # Message 2: Score card image
    await context.bot.send_chat_action(chat_id, ChatAction.UPLOAD_PHOTO)
    score_card_bytes = generate_score_card(score_report)
    score_text = format_score_card(score_report, previous_grade)
    await update.message.reply_photo(
        photo=io.BytesIO(score_card_bytes),
        caption=score_text,
        parse_mode=ParseMode.MARKDOWN,
    )

    # Message 3: Recommendations
    await context.bot.send_chat_action(chat_id, ChatAction.TYPING)
    history = [
        {"date": r.receipt_date.isoformat() if r.receipt_date else "?",
         "grade": r.overall_grade, "score": r.overall_score}
        for r in previous_receipts
    ]
    advice = await advisor.get_recommendations(score_report, history)
    await update.message.reply_text(advice, parse_mode=ParseMode.MARKDOWN)

    # Message 4: Predictive insight (if history exists)
    engine = PredictiveEngine(repo)
    trends = engine.get_user_trends(user.id)
    if trends["total_receipts"] > 1:
        weekly = engine.generate_weekly_report(user.id)
        if weekly:
            await update.message.reply_text(
                weekly, parse_mode=ParseMode.MARKDOWN,
                reply_markup=after_analysis_keyboard(),
            )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    handlers = {
        "history": _cb_history,
        "stats": _cb_stats,
        "tips": _cb_tips,
        "streak": _cb_streak,
        "compare": _cb_compare,
    }

    handler = handlers.get(query.data)
    if handler:
        await handler(query, context)


async def _cb_history(query, context):
    repo: Repository = context.bot_data["repo"]
    receipts = repo.get_user_receipts(query.from_user.id, limit=5)
    text = format_history(receipts)
    await query.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def _cb_stats(query, context):
    repo: Repository = context.bot_data["repo"]
    engine = PredictiveEngine(repo)
    trends = engine.get_user_trends(query.from_user.id)
    if not trends["score_trend"]:
        await query.message.reply_text(NO_HISTORY_MESSAGE)
        return
    chart_bytes = generate_trend_chart(trends["score_trend"])
    await query.message.reply_photo(photo=io.BytesIO(chart_bytes))


async def _cb_tips(query, context):
    repo: Repository = context.bot_data["repo"]
    advisor: DietAdvisor = context.bot_data["advisor"]
    import json
    receipts = repo.get_user_receipts(query.from_user.id, limit=5)
    if not receipts:
        await query.message.reply_text(NO_HISTORY_MESSAGE)
        return
    latest = receipts[0]
    raw = json.loads(latest.raw_json) if latest.raw_json else {}
    score_report = raw.get("score", {})
    history = [
        {"date": r.receipt_date.isoformat() if r.receipt_date else "?",
         "grade": r.overall_grade, "score": r.overall_score}
        for r in receipts
    ]
    advice = await advisor.get_recommendations(score_report, history)
    await query.message.reply_text(advice, parse_mode=ParseMode.MARKDOWN)


async def _cb_streak(query, context):
    repo: Repository = context.bot_data["repo"]
    engine = PredictiveEngine(repo)
    trends = engine.get_user_trends(query.from_user.id)
    text = format_streak(trends["streak"], trends["total_receipts"])
    await query.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def _cb_compare(query, context):
    repo: Repository = context.bot_data["repo"]
    engine = PredictiveEngine(repo)
    comparison = engine.get_comparison(query.from_user.id)
    if not comparison:
        await query.message.reply_text("📭 Need at least two receipts to compare.")
        return
    await query.message.reply_text(f"```\n{comparison}\n```", parse_mode=ParseMode.MARKDOWN)
