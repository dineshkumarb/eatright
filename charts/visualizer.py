import io
import logging

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.offsetbox import AnnotationBbox, TextArea
from PIL import Image

logger = logging.getLogger(__name__)

GRADE_COLORS = {
    "A": "#2ECC71",
    "B": "#82E0AA",
    "C": "#F4D03F",
    "D": "#E67E22",
    "E": "#E74C3C",
}

GRADE_LABELS = {
    "A": "Excellent",
    "B": "Good",
    "C": "Average",
    "D": "Poor",
    "E": "Bad",
}

BG_COLOR = "#1a1a2e"
TEXT_COLOR = "#e8e8e8"
SUBTLE_TEXT = "#8a8a9a"


def generate_score_card(score_report: dict) -> bytes:
    grade = score_report.get("overall_grade", "C")
    score = score_report.get("overall_score", 3.0)
    fresh_pct = score_report.get("fresh_percentage", 0)
    organic_pct = score_report.get("organic_percentage", 0)
    processed_pct = score_report.get("ultra_processed_percentage", 0)
    category_breakdown = score_report.get("category_breakdown", {})

    fig = plt.figure(figsize=(8, 6), facecolor=BG_COLOR)
    gs = fig.add_gridspec(3, 2, height_ratios=[2, 0.8, 2], hspace=0.4, wspace=0.3)

    # --- Grade display (top left) ---
    ax_grade = fig.add_subplot(gs[0, 0])
    ax_grade.set_facecolor(BG_COLOR)
    ax_grade.set_xlim(0, 10)
    ax_grade.set_ylim(0, 10)
    ax_grade.axis("off")

    color = GRADE_COLORS.get(grade, "#F4D03F")
    circle = plt.Circle((5, 5.5), 3.2, color=color, alpha=0.15)
    ax_grade.add_patch(circle)
    ax_grade.text(5, 5.5, grade, fontsize=72, fontweight="bold", color=color,
                  ha="center", va="center", fontfamily="monospace")
    ax_grade.text(5, 1.8, GRADE_LABELS.get(grade, ""), fontsize=14,
                  color=SUBTLE_TEXT, ha="center", va="center")

    # --- Score bar (top right) ---
    ax_bar = fig.add_subplot(gs[0, 1])
    ax_bar.set_facecolor(BG_COLOR)
    ax_bar.set_xlim(0, 5)
    ax_bar.set_ylim(0, 3)
    ax_bar.axis("off")

    ax_bar.text(2.5, 2.6, f"Score: {score:.1f} / 5.0", fontsize=16,
                color=TEXT_COLOR, ha="center", va="center", fontweight="bold")

    bar_y = 1.6
    bar_height = 0.5
    for i, (g, c) in enumerate([("E", GRADE_COLORS["E"]), ("D", GRADE_COLORS["D"]),
                                  ("C", GRADE_COLORS["C"]), ("B", GRADE_COLORS["B"]),
                                  ("A", GRADE_COLORS["A"])]):
        rect = mpatches.FancyBboxPatch((i, bar_y), 1, bar_height,
                                        boxstyle="round,pad=0.02", facecolor=c, alpha=0.3)
        ax_bar.add_patch(rect)
        ax_bar.text(i + 0.5, bar_y - 0.3, g, fontsize=10, color=SUBTLE_TEXT, ha="center")

    marker_x = max(0.1, min(4.9, score))
    ax_bar.plot(marker_x, bar_y + bar_height / 2, "v", color="white", markersize=14)

    # --- Stats bar (middle row, full width) ---
    ax_stats = fig.add_subplot(gs[1, :])
    ax_stats.set_facecolor(BG_COLOR)
    ax_stats.set_xlim(0, 12)
    ax_stats.set_ylim(0, 2)
    ax_stats.axis("off")

    stats = [
        ("🥦 Fresh", f"{fresh_pct:.0f}%", "#2ECC71" if fresh_pct >= 30 else "#E67E22"),
        ("♻️ Organic", f"{organic_pct:.0f}%", "#2ECC71" if organic_pct >= 15 else "#F4D03F"),
        ("⚠️ Processed", f"{processed_pct:.0f}%", "#2ECC71" if processed_pct < 20 else "#E74C3C"),
    ]

    for i, (label, value, stat_color) in enumerate(stats):
        x = 2 + i * 3
        ax_stats.text(x, 1.2, label, fontsize=11, color=SUBTLE_TEXT, ha="center")
        ax_stats.text(x, 0.4, value, fontsize=18, color=stat_color, ha="center", fontweight="bold")

    # --- Category pie chart (bottom row) ---
    food_categories = {k: v for k, v in category_breakdown.items()
                       if k not in ("cleaning", "personal_care")}

    if food_categories:
        ax_pie = fig.add_subplot(gs[2, :])
        ax_pie.set_facecolor(BG_COLOR)

        labels = []
        sizes = []
        colors = []
        for cat, data in sorted(food_categories.items(), key=lambda x: -x[1]["spend"]):
            nice_name = cat.replace("_", " ").title()
            labels.append(f"{nice_name}\n€{data['spend']:.2f}")
            sizes.append(data["spend"])
            colors.append(GRADE_COLORS.get(data.get("grade", "C"), "#F4D03F"))

        if sizes:
            wedges, texts = ax_pie.pie(
                sizes, labels=labels, colors=colors,
                startangle=90, pctdistance=0.75,
                textprops={"fontsize": 8, "color": TEXT_COLOR},
                wedgeprops={"alpha": 0.85, "edgecolor": BG_COLOR, "linewidth": 2},
            )
            ax_pie.set_title("Spending by Category", fontsize=12, color=TEXT_COLOR, pad=10)

    fig.suptitle("BASKET HEALTH SCORE", fontsize=18, color=TEXT_COLOR,
                 fontweight="bold", y=0.97)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                facecolor=BG_COLOR, edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def generate_trend_chart(score_trend: list[dict]) -> bytes:
    if not score_trend:
        return _placeholder_image("No data yet")

    dates = [entry.get("date", "?") for entry in score_trend]
    scores = [entry.get("score", 3.0) for entry in score_trend]
    grades = [entry.get("grade", "C") for entry in score_trend]
    colors = [GRADE_COLORS.get(g, "#F4D03F") for g in grades]

    fig, ax = plt.subplots(figsize=(8, 4), facecolor=BG_COLOR)
    ax.set_facecolor(BG_COLOR)

    ax.fill_between(range(len(scores)), scores, alpha=0.15, color="#3498DB")
    ax.plot(range(len(scores)), scores, "-o", color="#3498DB", linewidth=2.5,
            markersize=8, markerfacecolor="white", markeredgecolor="#3498DB", markeredgewidth=2)

    for i, (s, g, c) in enumerate(zip(scores, grades, colors)):
        ax.annotate(g, (i, s), textcoords="offset points", xytext=(0, 14),
                    ha="center", fontsize=12, fontweight="bold", color=c)

    short_dates = []
    for d in dates:
        try:
            parts = d.split("-")
            short_dates.append(f"{parts[2]}/{parts[1]}" if len(parts) == 3 else d[:5])
        except (IndexError, AttributeError):
            short_dates.append(str(d)[:5])

    ax.set_xticks(range(len(short_dates)))
    ax.set_xticklabels(short_dates, fontsize=9, color=SUBTLE_TEXT, rotation=30)
    ax.set_ylim(0.5, 5.5)
    ax.set_ylabel("Score", color=TEXT_COLOR, fontsize=11)
    ax.tick_params(axis="y", colors=SUBTLE_TEXT)

    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.grid(axis="y", alpha=0.1, color="white")

    ax.set_title("Your Score Trend", fontsize=16, color=TEXT_COLOR, fontweight="bold", pad=15)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                facecolor=BG_COLOR, edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def _placeholder_image(text: str) -> bytes:
    fig, ax = plt.subplots(figsize=(6, 3), facecolor=BG_COLOR)
    ax.set_facecolor(BG_COLOR)
    ax.text(0.5, 0.5, text, fontsize=18, color=SUBTLE_TEXT,
            ha="center", va="center", transform=ax.transAxes)
    ax.axis("off")
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100, bbox_inches="tight",
                facecolor=BG_COLOR, edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()
