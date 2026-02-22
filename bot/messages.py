from datetime import date

GRADE_EMOJI = {"A": "🟢", "B": "🟢", "C": "🟡", "D": "🟠", "E": "🔴"}
CATEGORY_EMOJI = {
    "fresh_produce": "🥦",
    "dairy": "🧀",
    "meat_fish": "🥩",
    "bread_bakery": "🍞",
    "frozen": "🧊",
    "beverages": "🥤",
    "snacks_sweets": "🍪",
    "condiments_sauces": "🫙",
    "cleaning": "🧹",
    "personal_care": "🧴",
    "processed_food": "🏭",
    "organic": "🌿",
    "other": "📦",
}
CATEGORY_LABELS = {
    "fresh_produce": "FRESH PRODUCE",
    "dairy": "DAIRY",
    "meat_fish": "MEAT & FISH",
    "bread_bakery": "BREAD & BAKERY",
    "frozen": "FROZEN",
    "beverages": "BEVERAGES",
    "snacks_sweets": "SNACKS & SWEETS",
    "condiments_sauces": "CONDIMENTS & SAUCES",
    "cleaning": "CLEANING",
    "personal_care": "PERSONAL CARE",
    "processed_food": "PROCESSED FOOD",
    "organic": "ORGANIC",
    "other": "OTHER",
}


WELCOME_MESSAGE = """👋 *Welcome to the Mercadona Grocery Health Analyzer!*

I help you eat healthier by analyzing your Mercadona receipts.

📸 *How to use:*
1. Take a photo of your Mercadona receipt
2. Send it to me
3. I'll analyze every item, score your basket A–E, and give you personalized tips!

*Commands:*
/history — View your last 5 receipt scores
/stats — See your score trend over time
/tips — Get personalized diet tips
/streak — Check your healthy shopping streak
/compare — Compare your last two receipts
/help — Show this message again

Ready? Send me a receipt photo! 🛒"""

HELP_MESSAGE = WELCOME_MESSAGE

ANALYZING_MESSAGE = "🔍 Analyzing your Mercadona receipt... this takes ~15 seconds"

ERROR_RECEIPT_MESSAGE = (
    "❌ I couldn't read that receipt clearly.\n\n"
    "💡 *Tips for better results:*\n"
    "• Lay the receipt flat on a dark surface\n"
    "• Make sure all text is visible and in focus\n"
    "• Avoid shadows and glare\n"
    "• Include the full receipt from top to bottom"
)

NO_HISTORY_MESSAGE = "📭 You don't have any receipt history yet. Send me a receipt photo to get started!"

RATE_LIMIT_MESSAGE = "⏳ Please wait a moment before sending another receipt. One analysis per minute."


def format_item_list(parsed_data: dict, score_report: dict) -> str:
    receipt_date = parsed_data.get("receipt_date", date.today().strftime("%d/%m/%Y"))
    location = parsed_data.get("store_location", "Mercadona")
    total = parsed_data.get("total_amount", 0)

    lines = [
        f"🛒 *Your Mercadona Receipt — {receipt_date}*",
        f"📍 {location} | 💶 Total: €{total:.2f}",
        "",
        "━━━━━━━━━━━━━━━━━━━━━",
    ]

    items_by_category: dict[str, list] = {}
    item_scores = {s["english_name"].lower(): s["grade"]
                   for s in score_report.get("item_scores", []) if s.get("grade")}

    for item in parsed_data.get("items", []):
        cat = item.get("category", "other")
        items_by_category.setdefault(cat, []).append(item)

    category_order = [
        "fresh_produce", "organic", "dairy", "meat_fish", "bread_bakery",
        "frozen", "beverages", "condiments_sauces", "processed_food",
        "snacks_sweets", "cleaning", "personal_care", "other",
    ]

    total_items = 0
    organic_count = 0
    ultra_processed_count = 0

    for cat in category_order:
        cat_items = items_by_category.get(cat)
        if not cat_items:
            continue

        emoji = CATEGORY_EMOJI.get(cat, "📦")
        label = CATEGORY_LABELS.get(cat, cat.upper())
        lines.append(f"{emoji} *{label}*")

        for item in cat_items:
            name = item.get("english_name", item.get("original_name", "?"))
            price = item.get("total_price", 0)
            grade = item_scores.get(name.lower(), item.get("nutriscore_estimate", ""))
            grade_emoji = GRADE_EMOJI.get(grade, "⬜")

            organic_tag = " 🌿" if item.get("is_organic") else ""
            qty = item.get("quantity", 1)
            qty_str = f" x{qty}" if qty > 1 else ""

            lines.append(f"  {grade_emoji} {name}{organic_tag}{qty_str} — €{price:.2f}")

            total_items += 1
            if item.get("is_organic"):
                organic_count += 1
            if grade in ("D", "E"):
                ultra_processed_count += 1

        lines.append("")

    lines.append("━━━━━━━━━━━━━━━━━━━━━")
    lines.append(
        f"🏷️ *{total_items} items | {organic_count} organic | "
        f"{ultra_processed_count} ultra-processed*"
    )

    return "\n".join(lines)


def format_score_card(score_report: dict, previous_grade: str = None) -> str:
    grade = score_report.get("overall_grade", "C")
    score = score_report.get("overall_score", 3.0)
    grade_emoji = GRADE_EMOJI.get(grade, "⬜")
    fresh_pct = score_report.get("fresh_percentage", 0)
    organic_pct = score_report.get("organic_percentage", 0)
    processed_pct = score_report.get("ultra_processed_percentage", 0)

    lines = [
        "📊 *BASKET HEALTH SCORE*",
        "",
        f"Your grade this shop: *{grade}* {grade_emoji}",
        f"Score: {score:.1f} / 5.0",
    ]

    if previous_grade:
        grade_val = {"A": 5, "B": 4, "C": 3, "D": 2, "E": 1}
        diff = grade_val.get(grade, 3) - grade_val.get(previous_grade, 3)
        if diff > 0:
            lines.append(f"\n📈 vs last shop: ↑ improved from {previous_grade}")
        elif diff < 0:
            lines.append(f"\n📉 vs last shop: ↓ declined from {previous_grade}")
        else:
            lines.append(f"\n➡️ vs last shop: same grade ({grade})")

    lines.append("")

    fresh_status = "✅" if fresh_pct >= 30 else "🟡" if fresh_pct >= 20 else "🔴"
    organic_status = "✅" if organic_pct >= 15 else "🟡" if organic_pct >= 5 else "🔴"
    processed_status = "✅" if processed_pct < 15 else "🟡" if processed_pct < 25 else "🔴"

    lines.append(f"🥦 Fresh produce: {fresh_pct:.0f}% of spend {fresh_status}")
    lines.append(f"♻️ Organic items: {organic_pct:.0f}% of spend {organic_status}")
    lines.append(f"⚠️ Ultra-processed: {processed_pct:.0f}% of spend {processed_status}")

    if fresh_pct < 35:
        lines.append(f"\n*Goal: Get fresh produce above 35% next shop!*")
    elif processed_pct > 20:
        lines.append(f"\n*Goal: Reduce ultra-processed items below 20%!*")
    else:
        lines.append(f"\n*Great job! Keep up the healthy shopping! 🌟*")

    return "\n".join(lines)


def format_history(receipts: list) -> str:
    if not receipts:
        return NO_HISTORY_MESSAGE

    lines = ["📋 *Your Receipt History*\n"]

    for r in receipts[:5]:
        d = r.receipt_date.strftime("%d/%m/%Y") if r.receipt_date else "?"
        grade_emoji = GRADE_EMOJI.get(r.overall_grade, "⬜")
        lines.append(
            f"{grade_emoji} {d} — Grade *{r.overall_grade}* "
            f"({r.overall_score:.1f}/5.0) — €{r.total_amount:.2f}"
        )

    return "\n".join(lines)


def format_streak(streak: int, total_receipts: int) -> str:
    if total_receipts == 0:
        return NO_HISTORY_MESSAGE

    if streak == 0:
        return (
            "🛒 *Shopping Streak*\n\n"
            "You don't have a healthy streak yet.\n"
            "Aim for a B or better on your next shop to start one! 💪"
        )

    fire = "🔥" * min(streak, 5)
    return (
        f"🛒 *Shopping Streak*\n\n"
        f"{fire} *{streak} consecutive shop{'s' if streak != 1 else ''}* "
        f"with grade B or better!\n\n"
        f"Keep it going! 💪"
    )
