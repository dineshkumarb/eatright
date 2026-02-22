from datetime import datetime, date

from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    Float,
    Boolean,
    Date,
    DateTime,
    Text,
    ForeignKey,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True)  # Telegram user ID
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    receipts = relationship("Receipt", back_populates="user", order_by="desc(Receipt.receipt_date)")


class Receipt(Base):
    __tablename__ = "receipts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    receipt_date = Column(Date, nullable=True)
    store_location = Column(String(500), nullable=True)
    total_amount = Column(Float, nullable=True)
    overall_grade = Column(String(1), nullable=True)
    overall_score = Column(Float, nullable=True)
    organic_percentage = Column(Float, default=0.0)
    fresh_percentage = Column(Float, default=0.0)
    ultra_processed_percentage = Column(Float, default=0.0)
    raw_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="receipts")
    items = relationship("PurchasedItem", back_populates="receipt", cascade="all, delete-orphan")


class PurchasedItem(Base):
    __tablename__ = "purchased_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    receipt_id = Column(Integer, ForeignKey("receipts.id"), nullable=False)
    original_name = Column(String(500), nullable=False)
    english_name = Column(String(500), nullable=False)
    category = Column(String(100), nullable=False)
    quantity = Column(Float, default=1.0)
    unit_price = Column(Float, default=0.0)
    total_price = Column(Float, default=0.0)
    grade = Column(String(1), nullable=True)
    is_organic = Column(Boolean, default=False)

    receipt = relationship("Receipt", back_populates="items")


def init_db(database_url: str):
    engine = create_engine(database_url, echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return engine, Session
