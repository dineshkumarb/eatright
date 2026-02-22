import logging
from datetime import date, timedelta

from database.models import Receipt, PurchasedItem

logger = logging.getLogger(__name__)

GRADE_VALUES = {"A": 5, "B": 4, "C": 3, "D": 2, "E": 1}
VALUE_GRADES = {5: "A", 4: "B", 3: "C", 2: "D", 1: "E"}


class PredictiveEngine:
    def __init__(self, repository):
        self.repo = repository

    def get_user_trends(self, user_id: int) -> dict:
        receipts = self.repo.get_user_receipts(user_id, limit=20)
        if not receipts:
            return self._empty_trends()

        score_trend = [
            {
                "date": r.receipt_date.isoformat() if r.receipt_date else "unknown",
                "grade": r.overall_grade or "C",
                "score": r.overall_score or 3.0,
            }
            for r in receipts
        ]

        all_items = self.repo.get_all_items_for_user(user_id)
        unhealthy_counts: dict[str, int] = {}
        healthy_counts: dict[str, int] = {}

        for item in all_items:
            name = item.english_name
            if item.grade in ("D", "E"):
                unhealthy_counts[name] = unhealthy_counts.get(name, 0) + 1
            elif item.grade in ("A", "B"):
                healthy_counts[name] = healthy_counts.get(name, 0) + 1

        most_unhealthy = sorted(unhealthy_counts.items(), key=lambda x: -x[1])[:5]
        most_healthy = sorted(healthy_counts.items(), key=lambda x: -x[1])[:5]

        predicted = self._predict_next_score(score_trend)
        streak = self._calculate_streak(score_trend)

        return {
            "score_trend": list(reversed(score_trend)),
            "most_bought_unhealthy": [{"name": n, "count": c} for n, c in most_unhealthy],
            "most_bought_healthy": [{"name": n, "count": c} for n, c in most_healthy],
            "predicted_next_score": predicted,
            "predicted_next_grade": self._score_to_grade(predicted) if predicted else None,
            "streak": streak,
            "total_receipts": len(receipts),
        }

    def generate_weekly_report(self, user_id: int) -> str | None:
        receipts = self.repo.get_user_receipts(user_id, limit=2)
        if not receipts:
            return None

        current = receipts[0]
        previous = receipts[1] if len(receipts) > 1 else None

        lines = ["📊 *Weekly Shopping Report*\n"]

        lines.append(f"🛒 Latest shop: {_format_date(current.receipt_date)}")
        lines.append(f"📝 Grade: *{current.overall_grade}* ({current.overall_score:.1f}/5.0)")

        if previous:
            diff = (current.overall_score or 3) - (previous.overall_score or 3)
            if diff > 0:
                lines.append(f"📈 Improved from {previous.overall_grade} → {current.overall_grade} (+{diff:.1f})")
            elif diff < 0:
                lines.append(f"📉 Declined from {previous.overall_grade} → {current.overall_grade} ({diff:.1f})")
            else:
                lines.append(f"➡️ Same as last time: {current.overall_grade}")

        items = self.repo.get_receipt_with_items(current.id)
        if items and items.items:
            sorted_items = sorted(items.items, key=lambda i: GRADE_VALUES.get(i.grade, 3), reverse=True)
            best = sorted_items[0]
            worst = sorted_items[-1]
            lines.append(f"\n✅ Best purchase: {best.english_name} (Grade {best.grade})")
            lines.append(f"⚠️ Worst purchase: {worst.english_name} (Grade {worst.grade})")

        trends = self.get_user_trends(user_id)
        streak = trends.get("streak", 0)
        if streak > 0:
            lines.append(f"\n🔥 Healthy streak: {streak} week{'s' if streak != 1 else ''} with B or better!")

        lines.append("\n💪 *Goal for next shop*: Try to add one more serving of fresh produce!")

        return "\n".join(lines)

    def get_comparison(self, user_id: int) -> str | None:
        receipts = self.repo.get_user_receipts(user_id, limit=2)
        if len(receipts) < 2:
            return None

        current, previous = receipts[0], receipts[1]
        lines = ["📊 *Receipt Comparison*\n"]
        lines.append(f"{'Metric':<25} {'Previous':>10} {'Current':>10}")
        lines.append("─" * 47)
        lines.append(f"{'Date':<25} {_format_date(previous.receipt_date):>10} {_format_date(current.receipt_date):>10}")
        lines.append(f"{'Total':<25} {'€' + f'{previous.total_amount:.2f}':>9} {'€' + f'{current.total_amount:.2f}':>9}")
        lines.append(f"{'Grade':<25} {previous.overall_grade or '-':>10} {current.overall_grade or '-':>10}")
        lines.append(f"{'Score':<25} {previous.overall_score or 0:.1f}{'/5':>6} {current.overall_score or 0:.1f}{'/5':>6}")
        lines.append(f"{'Fresh %':<25} {previous.fresh_percentage or 0:.0f}{'%':>7} {current.fresh_percentage or 0:.0f}{'%':>7}")
        lines.append(f"{'Organic %':<25} {previous.organic_percentage or 0:.0f}{'%':>7} {current.organic_percentage or 0:.0f}{'%':>7}")
        lines.append(f"{'Ultra-processed %':<25} {previous.ultra_processed_percentage or 0:.0f}{'%':>7} {current.ultra_processed_percentage or 0:.0f}{'%':>7}")

        return "\n".join(lines)

    def _predict_next_score(self, score_trend: list[dict]) -> float | None:
        scores = [t["score"] for t in score_trend if t["score"]]
        if len(scores) < 2:
            return None

        n = len(scores)
        x_mean = (n - 1) / 2
        y_mean = sum(scores) / n
        numerator = sum((i - x_mean) * (s - y_mean) for i, s in enumerate(scores))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return y_mean

        slope = numerator / denominator
        intercept = y_mean - slope * x_mean
        predicted = slope * n + intercept
        return max(1.0, min(5.0, round(predicted, 2)))

    def _calculate_streak(self, score_trend: list[dict]) -> int:
        streak = 0
        for entry in score_trend:
            if entry["grade"] in ("A", "B"):
                streak += 1
            else:
                break
        return streak

    def _score_to_grade(self, score: float) -> str:
        if score >= 4.5:
            return "A"
        elif score >= 3.5:
            return "B"
        elif score >= 2.5:
            return "C"
        elif score >= 1.5:
            return "D"
        return "E"

    def _empty_trends(self) -> dict:
        return {
            "score_trend": [],
            "most_bought_unhealthy": [],
            "most_bought_healthy": [],
            "predicted_next_score": None,
            "predicted_next_grade": None,
            "streak": 0,
            "total_receipts": 0,
        }


def _format_date(d) -> str:
    if isinstance(d, date):
        return d.strftime("%d/%m/%Y")
    return str(d) if d else "N/A"
