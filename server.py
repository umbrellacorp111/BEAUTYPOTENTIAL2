import asyncio
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from sqlalchemy import text
from bot.config import config
from bot.db.session import engine
from bot.db.models import Base
from bot.db.queries import migrate_existing_reports
from bot.handlers import start, registration, photos, payment, result, feedback, admin, stylist
from bot.handlers.payment import yukassa_webhook_handler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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

    # Migrations in a separate connection to avoid DDL transaction issues
    async with engine.begin() as conn:
        for table, column, definition in MIGRATIONS:
            try:
                await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {definition}"))
                logger.info(f"Added column {table}.{column}")
            except Exception as e:
                msg = str(e).lower()
                if "duplicate" in msg or "already exists" in msg:
                    logger.info(f"Column {table}.{column} already exists")
                else:
                    logger.error(f"Migration error for {table}.{column}: {e}")

    await migrate_existing_reports()


async def health_handler(request: web.Request) -> web.Response:
    return web.Response(text="OK")


async def main():
    bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties())
    dp = Dispatcher()

    dp.startup.register(on_startup)

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

    # aiohttp веб-сервер для healthcheck + webhook
    app = web.Application()
    app["bot"] = bot
    app.router.add_get("/", health_handler)
    app.router.add_post("/webhook/yukassa", yukassa_webhook_handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 3000)
    await site.start()
    logger.info("HTTP server started on port 3000 (healthcheck + yukassa webhook)")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
