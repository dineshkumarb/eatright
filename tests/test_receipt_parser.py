import json
import pytest
from unittest.mock import MagicMock, patch

from core.receipt_parser import ReceiptParser


SAMPLE_RESPONSE = {
    "receipt_date": "15/02/2025",
    "total_amount": 32.14,
    "store_location": "Mercadona Barcelona Diagonal",
    "items": [
        {
            "original_name": "TOMÀQUET PERA KG",
            "english_name": "Pear Tomatoes (per kg)",
            "quantity": 1,
            "unit_price": 1.99,
            "total_price": 1.99,
            "category": "fresh_produce",
            "is_organic": False,
            "nutriscore_estimate": "A",
        },
        {
            "original_name": "ESPINACS BABY 200G",
            "english_name": "Baby Spinach 200g",
            "quantity": 1,
            "unit_price": 2.15,
            "total_price": 2.15,
            "category": "fresh_produce",
            "is_organic": False,
            "nutriscore_estimate": "A",
        },
        {
            "original_name": "LLET SEMI 1L",
            "english_name": "Semi-skimmed Milk 1L",
            "quantity": 1,
            "unit_price": 0.89,
            "total_price": 0.89,
            "category": "dairy",
            "is_organic": False,
            "nutriscore_estimate": "B",
        },
        {
            "original_name": "PATATES FREGIDES",
            "english_name": "Fried Potato Chips",
            "quantity": 1,
            "unit_price": 1.69,
            "total_price": 1.69,
            "category": "snacks_sweets",
            "is_organic": False,
            "nutriscore_estimate": "E",
        },
        {
            "original_name": "PLATANO ECO KG",
            "english_name": "Organic Bananas (per kg)",
            "quantity": 1,
            "unit_price": 1.80,
            "total_price": 1.80,
            "category": "fresh_produce",
            "is_organic": True,
            "nutriscore_estimate": "A",
        },
    ],
}


class TestReceiptParser:
    @pytest.fixture
    def parser(self):
        with patch("core.receipt_parser.genai.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            p = ReceiptParser(api_key="test-key")
            p._mock_client = mock_client
            yield p

    @pytest.mark.asyncio
    async def test_parse_receipt_image_success(self, parser):
        mock_response = MagicMock()
        mock_response.text = json.dumps(SAMPLE_RESPONSE)
        parser._mock_client.models.generate_content.return_value = mock_response

        result = await parser.parse_receipt_image(b"fake-image-data")

        assert result["receipt_date"] == "15/02/2025"
        assert result["total_amount"] == 32.14
        assert len(result["items"]) == 5
        assert result["items"][0]["english_name"] == "Pear Tomatoes (per kg)"

    @pytest.mark.asyncio
    async def test_parse_handles_markdown_wrapped_json(self, parser):
        wrapped = f"```json\n{json.dumps(SAMPLE_RESPONSE)}\n```"
        mock_response = MagicMock()
        mock_response.text = wrapped
        parser._mock_client.models.generate_content.return_value = mock_response

        result = await parser.parse_receipt_image(b"fake-image-data")

        assert result["total_amount"] == 32.14

    @pytest.mark.asyncio
    async def test_parse_invalid_json_raises(self, parser):
        mock_response = MagicMock()
        mock_response.text = "not valid json at all"
        parser._mock_client.models.generate_content.return_value = mock_response

        with pytest.raises(ValueError, match="Could not parse"):
            await parser.parse_receipt_image(b"fake-image-data")

    def test_sample_response_structure(self):
        assert "receipt_date" in SAMPLE_RESPONSE
        assert "total_amount" in SAMPLE_RESPONSE
        assert "items" in SAMPLE_RESPONSE
        for item in SAMPLE_RESPONSE["items"]:
            assert "original_name" in item
            assert "english_name" in item
            assert "category" in item
            assert "nutriscore_estimate" in item

    def test_organic_items_detected(self):
        organic = [i for i in SAMPLE_RESPONSE["items"] if i["is_organic"]]
        assert len(organic) == 1
        assert "ECO" in organic[0]["original_name"]
