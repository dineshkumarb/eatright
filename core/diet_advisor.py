import json
import logging

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = "You are a friendly nutritionist who specializes in Mediterranean diet and Spanish supermarket products. Give practical, Mercadona-specific advice."

ADVICE_PROMPT_TEMPLATE = """Based on this grocery basket analysis, generate personalized diet improvement advice.

Basket data: {score_report_json}

Provide:
1. TOP 3 SWAPS: Specific Mercadona products to replace with healthier alternatives (keep it realistic and affordable)
2. MISSING NUTRIENTS: What nutrients are likely missing based on the basket (e.g., omega-3, fiber, vitamin D)
3. ORGANIC UPGRADE: Which 2–3 items are most worth buying organic at Mercadona (ECO range)
4. WEEKLY MEAL IDEA: One simple meal idea using the healthy items already in the basket
5. TREND INSIGHT: If historical data exists, comment on improvement/decline vs previous shop

{history_context}

Format your response in clear sections with emojis. Keep it friendly, practical, and specific to what Mercadona actually sells.
Language: English"""

MODEL = "gemini-2.5-flash"


class DietAdvisor:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)

    async def get_recommendations(
        self,
        score_report: dict,
        previous_reports: list[dict] | None = None,
    ) -> str:
        history_context = ""
        if previous_reports:
            history_lines = []
            for r in previous_reports[:5]:
                history_lines.append(
                    f"- {r.get('date', '?')}: Grade {r.get('grade', '?')} "
                    f"(Score {r.get('score', '?')})"
                )
            history_context = (
                "Historical data (most recent first):\n" + "\n".join(history_lines)
            )

        prompt = ADVICE_PROMPT_TEMPLATE.format(
            score_report_json=json.dumps(score_report, indent=2),
            history_context=history_context,
        )

        try:
            response = self.client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    max_output_tokens=2048,
                    temperature=0.7,
                ),
            )
            return response.text.strip()
        except Exception as e:
            logger.error("Gemini API error in diet advisor: %s", e)
            return _fallback_advice(score_report)


def _fallback_advice(score_report: dict) -> str:
    grade = score_report.get("overall_grade", "C")
    improvements = score_report.get("improvement_potential", [])

    lines = ["🍏 *Quick Tips to Improve Your Score*\n"]

    if grade in ("D", "E"):
        lines.append("Your basket has room for improvement! Try these changes:\n")
    elif grade == "C":
        lines.append("Decent basket! A few tweaks can push you to a B:\n")
    else:
        lines.append("Great basket! Keep it up. Minor suggestions:\n")

    for i, tip in enumerate(improvements[:3], 1):
        lines.append(f"{i}. {tip}")

    if not improvements:
        lines.append("• Try adding more fresh vegetables and fruits")
        lines.append("• Consider Mercadona's ECO range for staples like eggs and milk")
        lines.append("• Swap sugary drinks for water or herbal tea")

    lines.append("\n💡 *Goal*: Aim for 35%+ of your spend on fresh produce!")
    return "\n".join(lines)
