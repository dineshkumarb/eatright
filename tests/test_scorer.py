import pytest

from core.nutritional_scorer import (
    calculate_basket_score,
    estimate_item_grade,
    score_to_grade,
)


class TestScoreToGrade:
    def test_excellent(self):
        assert score_to_grade(4.5) == "A"
        assert score_to_grade(5.0) == "A"

    def test_good(self):
        assert score_to_grade(3.5) == "B"
        assert score_to_grade(4.4) == "B"

    def test_average(self):
        assert score_to_grade(2.5) == "C"
        assert score_to_grade(3.4) == "C"

    def test_poor(self):
        assert score_to_grade(1.5) == "D"
        assert score_to_grade(2.4) == "D"

    def test_bad(self):
        assert score_to_grade(1.0) == "E"
        assert score_to_grade(0.5) == "E"


class TestEstimateItemGrade:
    def test_explicit_nutriscore(self):
        item = {"nutriscore_estimate": "B", "category": "dairy"}
        assert estimate_item_grade(item) == "B"

    def test_fresh_produce(self):
        item = {"category": "fresh_produce"}
        assert estimate_item_grade(item) == "A"

    def test_snacks(self):
        item = {"category": "snacks_sweets"}
        assert estimate_item_grade(item) == "E"

    def test_organic_boost(self):
        item = {"category": "dairy", "is_organic": True}
        assert estimate_item_grade(item) == "A"

    def test_cleaning_no_grade(self):
        item = {"category": "cleaning"}
        assert estimate_item_grade(item) is None

    def test_unknown_category(self):
        item = {"category": "other"}
        assert estimate_item_grade(item) is None


class TestCalculateBasketScore:
    def test_all_healthy_basket(self):
        items = [
            {"english_name": "Tomatoes", "category": "fresh_produce",
             "total_price": 2.0, "nutriscore_estimate": "A", "is_organic": False},
            {"english_name": "Spinach", "category": "fresh_produce",
             "total_price": 2.5, "nutriscore_estimate": "A", "is_organic": True},
            {"english_name": "Salmon", "category": "meat_fish",
             "total_price": 5.0, "nutriscore_estimate": "B", "is_organic": False},
        ]
        result = calculate_basket_score(items)
        assert result["overall_grade"] in ("A", "B")
        assert result["overall_score"] >= 4.0
        assert result["fresh_percentage"] > 0
        assert result["ultra_processed_percentage"] == 0

    def test_all_unhealthy_basket(self):
        items = [
            {"english_name": "Chips", "category": "snacks_sweets",
             "total_price": 2.0, "nutriscore_estimate": "E", "is_organic": False},
            {"english_name": "Cola", "category": "beverages",
             "total_price": 1.5, "nutriscore_estimate": "E", "is_organic": False},
            {"english_name": "Cookies", "category": "snacks_sweets",
             "total_price": 2.0, "nutriscore_estimate": "E", "is_organic": False},
        ]
        result = calculate_basket_score(items)
        assert result["overall_grade"] == "E"
        assert result["overall_score"] <= 1.5
        assert result["ultra_processed_percentage"] == 100.0

    def test_mixed_basket(self):
        items = [
            {"english_name": "Tomatoes", "category": "fresh_produce",
             "total_price": 2.0, "nutriscore_estimate": "A", "is_organic": False},
            {"english_name": "Bread", "category": "bread_bakery",
             "total_price": 1.5, "nutriscore_estimate": "C", "is_organic": False},
            {"english_name": "Chips", "category": "snacks_sweets",
             "total_price": 1.5, "nutriscore_estimate": "E", "is_organic": False},
        ]
        result = calculate_basket_score(items)
        assert result["overall_grade"] == "C"

    def test_empty_basket(self):
        result = calculate_basket_score([])
        assert result["overall_grade"] == "C"
        assert result["overall_score"] == 3.0

    def test_non_food_items_excluded(self):
        items = [
            {"english_name": "Detergent", "category": "cleaning",
             "total_price": 4.0, "is_organic": False},
            {"english_name": "Tomatoes", "category": "fresh_produce",
             "total_price": 2.0, "nutriscore_estimate": "A", "is_organic": False},
        ]
        result = calculate_basket_score(items)
        assert result["overall_grade"] == "A"
        assert result["total_food_spend"] == 2.0

    def test_improvements_generated(self):
        items = [
            {"english_name": "Chips", "category": "snacks_sweets",
             "total_price": 1.5, "nutriscore_estimate": "E", "is_organic": False},
            {"english_name": "Cola", "category": "beverages",
             "total_price": 1.0, "nutriscore_estimate": "E", "is_organic": False},
        ]
        result = calculate_basket_score(items)
        assert len(result["improvement_potential"]) > 0

    def test_organic_percentage(self):
        items = [
            {"english_name": "Eco Eggs", "category": "dairy",
             "total_price": 3.0, "nutriscore_estimate": "B", "is_organic": True},
            {"english_name": "Milk", "category": "dairy",
             "total_price": 1.0, "nutriscore_estimate": "B", "is_organic": False},
        ]
        result = calculate_basket_score(items)
        assert result["organic_percentage"] == 75.0

    def test_category_breakdown(self):
        items = [
            {"english_name": "Tomatoes", "category": "fresh_produce",
             "total_price": 2.0, "nutriscore_estimate": "A", "is_organic": False},
            {"english_name": "Milk", "category": "dairy",
             "total_price": 1.0, "nutriscore_estimate": "B", "is_organic": False},
        ]
        result = calculate_basket_score(items)
        assert "fresh_produce" in result["category_breakdown"]
        assert "dairy" in result["category_breakdown"]
