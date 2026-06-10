from sqlalchemy import select, func
from bot.db.models import User
from bot.db.session import async_session
from datetime import datetime, timedelta


async def create_user(telegram_id: int, username: str | None, first_name: str | None) -> User:
    async with async_session() as session:
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def get_user(telegram_id: int) -> User | None:
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()


async def update_user(telegram_id: int, **kwargs) -> User | None:
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            return None
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        await session.commit()
        await session.refresh(user)
        return user


async def get_user_by_id(user_id: int) -> User | None:
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()


async def get_all_users() -> list[User]:
    async with async_session() as session:
        result = await session.execute(
            select(User).order_by(User.created_at.desc())
        )
        return list(result.scalars().all())


async def get_status_counts() -> dict[str, int]:
    async with async_session() as session:
        result = await session.execute(
            select(User.status, func.count(User.id))
            .group_by(User.status)
        )
        counts = {}
        for status, count in result:
            counts[status] = count
        total = await session.execute(select(func.count(User.id)))
        counts["total"] = total.scalar()
        return counts


async def add_credits(telegram_id: int, amount: int) -> User | None:
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            return None
        user.credits = (user.credits or 0) + amount
        await session.commit()
        await session.refresh(user)
        return user


# ──────────────────────────────────────────────
# StylistApplication queries
# ──────────────────────────────────────────────

from bot.db.models import StylistApplication


async def create_stylist_application(
    telegram_id: int,
    username: str | None,
    first_name: str | None,
    payment_date: datetime,
    last_photo_id: str | None = None,
    analysis_text: str | None = None,
    name: str | None = None,
    age: int | None = None,
    goals: list | None = None,
    photo_ids: list | None = None,
) -> StylistApplication:
    async with async_session() as session:
        app = StylistApplication(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            name=name,
            age=age,
            goals=goals or [],
            photo_ids=photo_ids or [],
            payment_date=payment_date,
            last_photo_id=last_photo_id,
            analysis_text=analysis_text,
            status="pending",
        )
        session.add(app)
        await session.commit()
        await session.refresh(app)
        return app


async def get_stylist_applications(status: str | None = None) -> list[StylistApplication]:
    async with async_session() as session:
        if status:
            result = await session.execute(
                select(StylistApplication)
                .where(StylistApplication.status == status)
                .order_by(StylistApplication.created_at.desc())
            )
        else:
            result = await session.execute(
                select(StylistApplication)
                .order_by(StylistApplication.created_at.desc())
            )
        return list(result.scalars().all())


async def get_stylist_application(app_id: int) -> StylistApplication | None:
    async with async_session() as session:
        result = await session.execute(
            select(StylistApplication).where(StylistApplication.id == app_id)
        )
        return result.scalar_one_or_none()


# ──────────────────────────────────────────────
# SavedAnalysis queries
# ──────────────────────────────────────────────

from bot.db.models import SavedAnalysis


async def save_analysis(telegram_id: int, report_type: str, report_text: str) -> SavedAnalysis:
    async with async_session() as session:
        record = SavedAnalysis(
            telegram_id=telegram_id,
            report_type=report_type,
            report_text=report_text,
        )
        session.add(record)
        await session.commit()
        await session.refresh(record)
        return record


async def get_user_analyses(telegram_id: int) -> list[SavedAnalysis]:
    async with async_session() as session:
        result = await session.execute(
            select(SavedAnalysis)
            .where(SavedAnalysis.telegram_id == telegram_id)
            .order_by(SavedAnalysis.created_at.desc())
        )
        return list(result.scalars().all())


async def get_saved_analysis(analysis_id: int) -> SavedAnalysis | None:
    async with async_session() as session:
        result = await session.execute(
            select(SavedAnalysis).where(SavedAnalysis.id == analysis_id)
        )
        return result.scalar_one_or_none()


async def migrate_existing_reports():
    """Переносит старые result_text из users в saved_analyses."""
    from bot.db.models import User
    async with async_session() as session:
        users = await session.execute(
            select(User).where(User.result_text.isnot(None), User.result_text != "")
        )
        for user in users.scalars().all():
            existing = await session.execute(
                select(SavedAnalysis).where(
                    SavedAnalysis.telegram_id == user.telegram_id,
                    SavedAnalysis.report_text == user.result_text,
                )
            )
            if not existing.scalar_one_or_none():
                session.add(SavedAnalysis(
                    telegram_id=user.telegram_id,
                    report_type="full",
                    report_text=user.result_text,
                ))
        await session.commit()


# ──────────────────────────────────────────────
# PendingPayment queries
# ──────────────────────────────────────────────

from bot.db.models import PendingPayment
from datetime import datetime


async def create_pending_payment(
    payment_id: str,
    telegram_id: int,
    package_index: int,
    is_stylist: bool,
    state_data: dict,
) -> PendingPayment:
    """Сохранить данные платежа в БД перед отправкой пользователя на оплату."""
    async with async_session() as session:
        record = PendingPayment(
            payment_id=payment_id,
            telegram_id=telegram_id,
            package_index=package_index,
            is_stylist=is_stylist,
            state_data=state_data,
            status="pending",
        )
        session.add(record)
        await session.commit()
        await session.refresh(record)
        return record


async def get_pending_payment(payment_id: str) -> PendingPayment | None:
    """Получить запись по payment_id."""
    async with async_session() as session:
        result = await session.execute(
            select(PendingPayment).where(PendingPayment.payment_id == payment_id)
        )
        return result.scalar_one_or_none()


async def get_pending_payment_by_user(telegram_id: int) -> PendingPayment | None:
    """Получить последний незавершённый платёж пользователя (для восстановления после рестарта)."""
    async with async_session() as session:
        result = await session.execute(
            select(PendingPayment)
            .where(
                PendingPayment.telegram_id == telegram_id,
                PendingPayment.status == "pending",
            )
            .order_by(PendingPayment.created_at.desc())
        )
        return result.scalar_one_or_none()


async def complete_pending_payment(payment_id: str) -> None:
    """Отметить платёж как выполненный и удалить временные данные."""
    async with async_session() as session:
        result = await session.execute(
            select(PendingPayment).where(PendingPayment.payment_id == payment_id)
        )
        record = result.scalar_one_or_none()
        if record:
            record.status = "succeeded"
            record.completed_at = datetime.utcnow()
            # Очищаем тяжёлые временные данные, оставляем только метаданные
            record.state_data = {}
            await session.commit()


async def has_stylist_access(telegram_id: int) -> bool:
    user = await get_user(telegram_id)
    if not user or not user.stylist_access_until:
        return False
    return user.stylist_access_until > datetime.utcnow()


async def set_stylist_access(telegram_id: int, days: int = 30) -> User | None:
    until = datetime.utcnow() + timedelta(days=days)
    return await update_user(telegram_id, stylist_access_until=until)


# ──────────────────────────────────────────────
# Admin statistics queries
# ──────────────────────────────────────────────


async def get_total_users() -> int:
    async with async_session() as session:
        result = await session.execute(select(func.count(User.id)))
        return result.scalar() or 0


async def get_total_payments() -> int:
    """Количество пользователей, совершивших хотя бы одну оплату."""
    async with async_session() as session:
        result = await session.execute(
            select(func.count(User.id)).where(User.payment_id.isnot(None))
        )
        return result.scalar() or 0


async def get_total_applications() -> int:
    async with async_session() as session:
        result = await session.execute(
            select(func.count(StylistApplication.id))
        )
        return result.scalar() or 0


async def get_applications_count_by_status(status: str) -> int:
    async with async_session() as session:
        result = await session.execute(
            select(func.count(StylistApplication.id))
            .where(StylistApplication.status == status)
        )
        return result.scalar() or 0


async def get_active_subscriptions_count() -> int:
    now = datetime.utcnow()
    async with async_session() as session:
        result = await session.execute(
            select(func.count(User.id))
            .where(
                User.stylist_access_until.isnot(None),
                User.stylist_access_until > now,
            )
        )
        return result.scalar() or 0


async def get_recent_users(limit: int = 5) -> list[User]:
    async with async_session() as session:
        result = await session.execute(
            select(User).order_by(User.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())


async def update_stylist_application_status(app_id: int, status: str) -> StylistApplication | None:
    async with async_session() as session:
        result = await session.execute(
            select(StylistApplication).where(StylistApplication.id == app_id)
        )
        app = result.scalar_one_or_none()
        if not app:
            return None
        app.status = status
        await session.commit()
        await session.refresh(app)
        return app


async def fail_pending_payment(payment_id: str) -> None:
    """Отметить платёж как неудачный."""
    async with async_session() as session:
        result = await session.execute(
            select(PendingPayment).where(PendingPayment.payment_id == payment_id)
        )
        record = result.scalar_one_or_none()
        if record:
            record.status = "failed"
            await session.commit()
