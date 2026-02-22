from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("📋 History", callback_data="history"),
            InlineKeyboardButton("📊 Stats", callback_data="stats"),
        ],
        [
            InlineKeyboardButton("💡 Tips", callback_data="tips"),
            InlineKeyboardButton("🔥 Streak", callback_data="streak"),
        ],
        [
            InlineKeyboardButton("🔄 Compare", callback_data="compare"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def after_analysis_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("📋 Full History", callback_data="history"),
            InlineKeyboardButton("📊 Trends", callback_data="stats"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)
