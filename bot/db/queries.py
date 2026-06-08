from sqlalchemy import select, func
from bot.db.models import User
from bot.db.session import async_session


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


async def get_users_by_status(status: str) -> list[User]:
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.status == status).order_by(User.created_at.desc())
        )
        return list(result.scalars().all())


async def get_all_users() -> list[User]:
    async with async_session() as session:
        result = await session.execute(
            select(User).order_by(User.created_at.desc())
        )
        return list(result.scalars().all())


async def get_user_by_id(user_id: int) -> User | None:
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()


async def get_status_counts() -> dict[str, int]:
    async with async_session() as session:
        result = await session.execute(
            select(User.status, func.count(User.id))
            .group_by(User.status)
        )
        counts = {"new": 0, "awaiting_payment": 0, "paid": 0, "in_progress": 0, "completed": 0, "cancelled": 0}
        for status, count in result:
            counts[status] = count
        total = await session.execute(select(func.count(User.id)))
        counts["total"] = total.scalar()
        return counts
