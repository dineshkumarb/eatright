from typing import Optional

GRADE_MAP = {"A": 5, "B": 4, "C": 3, "D": 2, "E": 1}
SCORE_TO_GRADE = [(4.5, "A"), (3.5, "B"), (2.5, "C"), (1.5, "D"), (0, "E")]

CATEGORY_GRADES = {
    "fresh_produce": "A",
    "organic": "A",
    "dairy": "B",
    "meat_fish": "B",
    "bread_bakery": "C",
    "frozen": "C",
    "condiments_sauces": "C",
    "processed_food": "D",
    "beverages": "C",
    "snacks_sweets": "E",
    "cleaning": None,
    "personal_care": None,
    "other": None,
}

HEALTHY_SWAP_SUGGESTIONS = {
    "snacks_sweets": {
        "default": "raw nuts or dried fruit from the healthy aisle",
        "examples": {
            "chips": "baked vegetable crisps or raw almonds",
            "cookies": "rice cakes with dark chocolate",
            "chocolate": "85%+ dark chocolate (smaller portion, more antioxidants)",
            "candy": "fresh seasonal fruit",
            "pastry": "whole grain toast with natural jam",
        },
    },
    "beverages": {
        "default": "sparkling water or herbal infusion",
        "examples": {
            "cola": "sparkling water with lemon",
            "soda": "Mercadona's kombucha or sparkling water",
            "juice": "whole fruit instead (more fiber, less sugar)",
            "energy": "green tea or black coffee",
        },
    },
    "processed_food": {
        "default": "a fresh-cooked alternative",
        "examples": {
            "nuggets": "fresh chicken breast, cut and bake at home",
            "pizza": "Mercadona's fresh pizza dough + fresh toppings",
            "ready meal": "batch-cooked stew (freeze portions)",
        },
    },
}


def score_to_grade(score: float) -> str:
    for threshold, grade in SCORE_TO_GRADE:
        if score >= threshold:
            return grade
    return "E"


def estimate_item_grade(item: dict) -> Optional[str]:
    if item.get("nutriscore_estimate") in GRADE_MAP:
        return item["nutriscore_estimate"]

    category = item.get("category", "other")
    base_grade = CATEGORY_GRADES.get(category)
    if base_grade is None:
        return None

    if item.get("is_organic") and base_grade in ("B", "C"):
        idx = list(GRADE_MAP.keys()).index(base_grade)
        return list(GRADE_MAP.keys())[max(0, idx - 1)]

    return base_grade


def calculate_basket_score(items: list[dict]) -> dict:
    scored_items = []
    food_items = []
    total_spend = 0.0
    organic_spend = 0.0
    fresh_spend = 0.0
    ultra_processed_spend = 0.0
    category_spend: dict[str, dict] = {}

    for item in items:
        grade = estimate_item_grade(item)
        price = item.get("total_price", 0)
        category = item.get("category", "other")

        scored_items.append({
            "english_name": item.get("english_name", item.get("original_name", "")),
            "original_name": item.get("original_name", ""),
            "category": category,
            "total_price": price,
            "grade": grade,
            "is_organic": item.get("is_organic", False),
        })

        if category in ("cleaning", "personal_care"):
            continue

        food_items.append((grade, price))
        total_spend += price

        if item.get("is_organic"):
            organic_spend += price
        if category == "fresh_produce":
            fresh_spend += price
        if grade in ("D", "E"):
            ultra_processed_spend += price

        if category not in category_spend:
            category_spend[category] = {"spend": 0.0, "grades": []}
        category_spend[category]["spend"] += price
        if grade:
            category_spend[category]["grades"].append(grade)

    if not food_items or total_spend == 0:
        return _empty_report(scored_items)

    weighted_sum = sum(GRADE_MAP.get(g, 3) * p for g, p in food_items if g)
    weight_total = sum(p for g, p in food_items if g)
    overall_score = weighted_sum / weight_total if weight_total > 0 else 3.0
    overall_grade = score_to_grade(overall_score)

    category_breakdown = {}
    for cat, data in category_spend.items():
        grades = data["grades"]
        if grades:
            avg = sum(GRADE_MAP.get(g, 3) for g in grades) / len(grades)
            category_breakdown[cat] = {"spend": round(data["spend"], 2), "grade": score_to_grade(avg)}

    improvement_potential = _generate_improvements(scored_items)

    return {
        "overall_grade": overall_grade,
        "overall_score": round(overall_score, 2),
        "organic_percentage": round(organic_spend / total_spend * 100, 1) if total_spend else 0,
        "fresh_percentage": round(fresh_spend / total_spend * 100, 1) if total_spend else 0,
        "ultra_processed_percentage": round(ultra_processed_spend / total_spend * 100, 1) if total_spend else 0,
        "category_breakdown": category_breakdown,
        "item_scores": scored_items,
        "improvement_potential": improvement_potential,
        "total_food_spend": round(total_spend, 2),
    }


def _generate_improvements(scored_items: list[dict]) -> list[str]:
    improvements = []
    for item in scored_items:
        if item["grade"] not in ("D", "E"):
            continue
        name = item["english_name"]
        category = item["category"]
        swap = _get_swap(name, category)
        if swap:
            improvements.append(f"Replace {name} with {swap}")
    return improvements[:5]


def _get_swap(name: str, category: str) -> Optional[str]:
    suggestions = HEALTHY_SWAP_SUGGESTIONS.get(category)
    if not suggestions:
        return "a fresher, less processed option"

    name_lower = name.lower()
    for keyword, swap in suggestions.get("examples", {}).items():
        if keyword in name_lower:
            return swap
    return suggestions["default"]


def _empty_report(scored_items: list[dict]) -> dict:
    return {
        "overall_grade": "C",
        "overall_score": 3.0,
        "organic_percentage": 0,
        "fresh_percentage": 0,
        "ultra_processed_percentage": 0,
        "category_breakdown": {},
        "item_scores": scored_items,
        "improvement_potential": [],
        "total_food_spend": 0,
    }
