import json
import logging
from pathlib import Path

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert at reading Mercadona supermarket receipts written in Catalan or Spanish.
Extract every purchased item from the receipt image and return a structured JSON.

For each item, provide:
- original_name: exact text from receipt (Catalan/Spanish)
- english_name: accurate English translation
- quantity: number of units purchased
- unit_price: price per unit in EUR
- total_price: total line price in EUR
- category: one of [fresh_produce, dairy, meat_fish, bread_bakery, frozen, beverages, snacks_sweets, condiments_sauces, cleaning, personal_care, processed_food, organic, other]
- is_organic: true/false (look for "ECO" or "BIO" labels)
- nutriscore_estimate: your estimate of A/B/C/D/E based on the product type

Also extract:
- receipt_date: date of purchase (DD/MM/YYYY)
- total_amount: total bill amount in EUR
- store_location: if visible

Return ONLY valid JSON, no markdown."""

MODEL = "gemini-2.5-flash"


class ReceiptParser:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)

    async def parse_receipt_image(self, image_data: bytes, media_type: str = "image/jpeg") -> dict:
        return await self._call_gemini(image_data, media_type)

    async def parse_receipt_file(self, file_path: str) -> dict:
        path = Path(file_path)
        suffix = path.suffix.lower()
        media_type = "image/png" if suffix == ".png" else "image/jpeg"
        image_data = path.read_bytes()
        return await self.parse_receipt_image(image_data, media_type)

    async def _call_gemini(self, image_data: bytes, media_type: str) -> dict:
        try:
            response = self.client.models.generate_content(
                model=MODEL,
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part(inline_data=types.Blob(
                                data=image_data,
                                mime_type=media_type,
                            )),
                            types.Part(text="Please extract all items and details from this Mercadona receipt."),
                        ],
                    ),
                ],
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    max_output_tokens=4096,
                    temperature=0.1,
                ),
            )

            response_text = response.text.strip()
            if response_text.startswith("```"):
                response_text = response_text.split("\n", 1)[1]
                if response_text.endswith("```"):
                    response_text = response_text[:-3]

            return json.loads(response_text)

        except json.JSONDecodeError as e:
            logger.error("Failed to parse Gemini response as JSON: %s", e)
            raise ValueError(
                "Could not parse the receipt. Please try again with a clearer photo."
            ) from e
        except Exception as e:
            logger.error("Gemini API error: %s", e)
            raise RuntimeError("AI service is temporarily unavailable. Please try again later.") from e
