import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from bot.config import config
from bot.db.session import engine
from bot.db.models import Base
from bot.handlers import start, registration, photos, payment, result, feedback, admin

logging.basicConfig(level=logging.INFO)


async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


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
    )

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
