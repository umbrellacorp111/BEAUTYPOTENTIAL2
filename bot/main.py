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

MIGRATIONS = [
    ("users", "credits", "credits INTEGER DEFAULT 0"),
    ("users", "free_used", "free_used INTEGER DEFAULT 0"),
    ("users", "stylist_access_until", "stylist_access_until DATETIME DEFAULT NULL"),
    ("users", "godmode", "godmode INTEGER DEFAULT 0"),
    ("users", "stylist_free_used", "stylist_free_used INTEGER DEFAULT 0"),
    ("stylist_applications", "name", "name VARCHAR(255) DEFAULT NULL"),
    ("stylist_applications", "age", "age INTEGER DEFAULT NULL"),
    ("stylist_applications", "goals", "goals JSON DEFAULT '[]'"),
    ("stylist_applications", "photo_ids", "photo_ids JSON DEFAULT '[]'"),
]


async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with engine.begin() as conn:
        for table, column, definition in MIGRATIONS:
            try:
                await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {definition}"))
                logging.info(f"Added column {table}.{column}")
            except Exception as e:
                msg = str(e).lower()
                if "duplicate" in msg or "already exists" in msg:
                    logging.info(f"Column {table}.{column} already exists")
                else:
                    logging.error(f"Migration error for {table}.{column}: {e}")

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
