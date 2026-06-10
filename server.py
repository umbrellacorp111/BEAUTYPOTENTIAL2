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


async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        res = await conn.execute(text("PRAGMA table_info(users)"))
        cols = {row[1] for row in res.all()}
        if "credits" not in cols:
            await conn.execute(text("ALTER TABLE users ADD COLUMN credits INTEGER DEFAULT 0"))
        if "free_used" not in cols:
            await conn.execute(text("ALTER TABLE users ADD COLUMN free_used INTEGER DEFAULT 0"))
        if "stylist_access_until" not in cols:
            await conn.execute(text("ALTER TABLE users ADD COLUMN stylist_access_until DATETIME DEFAULT NULL"))
        res2 = await conn.execute(text("PRAGMA table_info(stylist_applications)"))
        app_cols = {row[1] for row in res2.all()}
        if "name" not in app_cols:
            await conn.execute(text("ALTER TABLE stylist_applications ADD COLUMN name VARCHAR(255) DEFAULT NULL"))
        if "age" not in app_cols:
            await conn.execute(text("ALTER TABLE stylist_applications ADD COLUMN age INTEGER DEFAULT NULL"))
        if "goals" not in app_cols:
            await conn.execute(text("ALTER TABLE stylist_applications ADD COLUMN goals JSON DEFAULT '[]'"))
        if "photo_ids" not in app_cols:
            await conn.execute(text("ALTER TABLE stylist_applications ADD COLUMN photo_ids JSON DEFAULT '[]'"))
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
