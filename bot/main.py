import asyncio
import logging
from sqlalchemy import text
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from bot.config import config
from bot.db.session import engine
from bot.db.models import Base
from bot.db.queries import migrate_existing_reports
from bot.handlers import start, registration, photos, payment, result, feedback, admin, stylist

logging.basicConfig(level=logging.INFO)


async def on_startup():
    async with engine.begin() as conn:
        # Создаёт все таблицы включая новую pending_payments
        await conn.run_sync(Base.metadata.create_all)
        result = await conn.execute(text("PRAGMA table_info(users)"))
        rows = result.all()
        cols = {row[1] for row in rows}
        if "credits" not in cols:
            await conn.execute(text("ALTER TABLE users ADD COLUMN credits INTEGER DEFAULT 0"))
            logging.info("Added column 'credits' to users table")
        if "free_used" not in cols:
            await conn.execute(text("ALTER TABLE users ADD COLUMN free_used INTEGER DEFAULT 0"))
            logging.info("Added column 'free_used' to users table")
        if "stylist_access_until" not in cols:
            await conn.execute(text("ALTER TABLE users ADD COLUMN stylist_access_until DATETIME DEFAULT NULL"))
            logging.info("Added column 'stylist_access_until' to users table")

        # Миграция новых полей stylist_applications
        result2 = await conn.execute(text("PRAGMA table_info(stylist_applications)"))
        app_cols = {row[1] for row in result2.all()}
        if "name" not in app_cols:
            await conn.execute(text("ALTER TABLE stylist_applications ADD COLUMN name VARCHAR(255) DEFAULT NULL"))
            logging.info("Added column 'name' to stylist_applications")
        if "age" not in app_cols:
            await conn.execute(text("ALTER TABLE stylist_applications ADD COLUMN age INTEGER DEFAULT NULL"))
            logging.info("Added column 'age' to stylist_applications")
        if "goals" not in app_cols:
            await conn.execute(text("ALTER TABLE stylist_applications ADD COLUMN goals JSON DEFAULT '[]'"))
            logging.info("Added column 'goals' to stylist_applications")
        if "photo_ids" not in app_cols:
            await conn.execute(text("ALTER TABLE stylist_applications ADD COLUMN photo_ids JSON DEFAULT '[]'"))
            logging.info("Added column 'photo_ids' to stylist_applications")
    await migrate_existing_reports()
    logging.info("Database ready")


async def on_shutdown():
    await engine.dispose()


async def main():
    bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties())
    dp = Dispatcher()

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    dp.include_routers(
        start.router,
        registration.router,
        photos.router,
        payment.router,
        result.router,
        feedback.router,
        admin.router,
        stylist.router,
    )

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
