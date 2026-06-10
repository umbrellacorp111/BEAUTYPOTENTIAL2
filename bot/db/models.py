from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Column, BigInteger, String, Integer, Text, DateTime, Float, JSON, Boolean, func
from datetime import datetime


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    goals = Column(JSON, nullable=True, default=list)
    photo_ids = Column(JSON, nullable=True, default=list)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="new")
    credits: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    free_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    godmode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    stylist_free_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stylist_access_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    payment_method: Mapped[str | None] = mapped_column(String(32), nullable=True)
    payment_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payment_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    result_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_file_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at = mapped_column(DateTime, server_default=func.now())
    updated_at = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class StylistApplication(Base):
    __tablename__ = "stylist_applications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    goals = Column(JSON, nullable=True, default=list)
    photo_ids = Column(JSON, nullable=True, default=list)
    payment_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    last_photo_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    analysis_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    created_at = mapped_column(DateTime, server_default=func.now())


class SavedAnalysis(Base):
    __tablename__ = "saved_analyses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    report_type: Mapped[str] = mapped_column(String(32), nullable=False, default="full")
    report_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at = mapped_column(DateTime, server_default=func.now())


class PendingPayment(Base):
    """Персистентное хранилище ожидающих платежей.
    Заменяет словарь pending_payments в памяти процесса.
    Выживает после рестарта контейнера.
    """
    __tablename__ = "pending_payments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    payment_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    package_index: Mapped[int] = mapped_column(Integer, nullable=False)
    is_stylist: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Сериализованный state_data (name, age, goals, photo_ids, dialogue_messages и т.д.)
    state_data = Column(JSON, nullable=False, default=dict)
    # Статус: pending → succeeded / failed
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    created_at = mapped_column(DateTime, server_default=func.now())
    completed_at = mapped_column(DateTime, nullable=True)
