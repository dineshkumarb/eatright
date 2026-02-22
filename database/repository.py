import json
from datetime import date, datetime
from typing import Optional

from sqlalchemy.orm import Session

from database.models import User, Receipt, PurchasedItem


class Repository:
    def __init__(self, session_factory):
        self._session_factory = session_factory

    def _session(self) -> Session:
        return self._session_factory()

    def get_or_create_user(self, telegram_id: int, username: str = None, first_name: str = None) -> User:
        with self._session() as session:
            user = session.query(User).filter_by(id=telegram_id).first()
            if not user:
                user = User(id=telegram_id, username=username, first_name=first_name)
                session.add(user)
                session.commit()
            elif username and user.username != username:
                user.username = username
                session.commit()
            return user

    def save_receipt(
        self,
        user_id: int,
        parsed_data: dict,
        score_report: dict,
    ) -> Receipt:
        with self._session() as session:
            receipt_date_str = parsed_data.get("receipt_date")
            receipt_date = None
            if receipt_date_str:
                try:
                    receipt_date = datetime.strptime(receipt_date_str, "%d/%m/%Y").date()
                except ValueError:
                    receipt_date = date.today()

            receipt = Receipt(
                user_id=user_id,
                receipt_date=receipt_date or date.today(),
                store_location=parsed_data.get("store_location"),
                total_amount=parsed_data.get("total_amount", 0),
                overall_grade=score_report.get("overall_grade", "C"),
                overall_score=score_report.get("overall_score", 3.0),
                organic_percentage=score_report.get("organic_percentage", 0),
                fresh_percentage=score_report.get("fresh_percentage", 0),
                ultra_processed_percentage=score_report.get("ultra_processed_percentage", 0),
                raw_json=json.dumps({"parsed": parsed_data, "score": score_report}),
            )
            session.add(receipt)
            session.flush()

            for item in parsed_data.get("items", []):
                item_score = _find_item_score(score_report, item.get("english_name", ""))
                purchased = PurchasedItem(
                    receipt_id=receipt.id,
                    original_name=item.get("original_name", ""),
                    english_name=item.get("english_name", ""),
                    category=item.get("category", "other"),
                    quantity=item.get("quantity", 1),
                    unit_price=item.get("unit_price", 0),
                    total_price=item.get("total_price", 0),
                    grade=item_score or item.get("nutriscore_estimate", "C"),
                    is_organic=item.get("is_organic", False),
                )
                session.add(purchased)

            session.commit()
            receipt_id = receipt.id

        with self._session() as session:
            return session.query(Receipt).filter_by(id=receipt_id).first()

    def get_user_receipts(self, user_id: int, limit: int = 10) -> list[Receipt]:
        with self._session() as session:
            return (
                session.query(Receipt)
                .filter_by(user_id=user_id)
                .order_by(Receipt.receipt_date.desc())
                .limit(limit)
                .all()
            )

    def get_receipt_with_items(self, receipt_id: int) -> Optional[Receipt]:
        with self._session() as session:
            receipt = session.query(Receipt).filter_by(id=receipt_id).first()
            if receipt:
                _ = receipt.items  # eager load
            return receipt

    def get_all_items_for_user(self, user_id: int) -> list[PurchasedItem]:
        with self._session() as session:
            return (
                session.query(PurchasedItem)
                .join(Receipt)
                .filter(Receipt.user_id == user_id)
                .order_by(Receipt.receipt_date.desc())
                .all()
            )

    def get_user_receipt_count(self, user_id: int) -> int:
        with self._session() as session:
            return session.query(Receipt).filter_by(user_id=user_id).count()


def _find_item_score(score_report: dict, english_name: str) -> Optional[str]:
    for scored in score_report.get("item_scores", []):
        if scored.get("english_name", "").lower() == english_name.lower():
            return scored.get("grade")
    return None
