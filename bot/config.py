import os


class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    ADMIN_CHAT_ID: int = int(os.getenv("ADMIN_CHAT_ID", "0"))
    DATA_DIR: str = os.getenv("DATA_DIR", "data")
    YUKASSA_SHOP_ID: str = os.getenv("YUKASSA_SHOP_ID", "")
    YUKASSA_SECRET_KEY: str = os.getenv("YUKASSA_SECRET_KEY", "")
    YUKASSA_RETURN_URL: str = os.getenv("YUKASSA_RETURN_URL", "https://t.me/")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    SUPPORT_USERNAME: str = os.getenv("SUPPORT_USERNAME", "@support")
    BOT_LINK: str = os.getenv("BOT_LINK", "https://t.me/bot")

    CREDIT_PACKAGES = [
        {"label": "1 разбор — 99₽", "stars": 25, "rub": 99, "credits": 1},
        {"label": "5 разборов — 290₽", "stars": 75, "rub": 290, "credits": 5},
        {"label": "100 разборов — 999₽", "stars": 250, "rub": 999, "credits": 100},
    ]

    STYLIST_PACKAGE = {
        "label": "Персональный анализ от стилиста",
        "stars": 300,
        "rub": 1199,
        "credits": 0,
        "is_stylist": True,
    }

    @property
    def database_url(self) -> str:
        db_path = os.path.join(self.DATA_DIR, "bot.db")
        return f"sqlite+aiosqlite:///{db_path}"


config = Config()
