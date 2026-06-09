import os


class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    ADMIN_CHAT_ID: int = int(os.getenv("ADMIN_CHAT_ID", "0"))
    DATA_DIR: str = os.getenv("DATA_DIR", "data")
    YUKASSA_PROVIDER_TOKEN: str = os.getenv("YUKASSA_PROVIDER_TOKEN", "")
    YUKASSA_SHOP_ID: str = os.getenv("YUKASSA_SHOP_ID", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    SUPPORT_USERNAME: str = os.getenv("SUPPORT_USERNAME", "@support")
    BOT_LINK: str = os.getenv("BOT_LINK", "https://t.me/bot")

    CREDIT_PACKAGES = [
        {"label": "1 анализ — 99 ₽", "stars": 25, "rub": 99, "credits": 1},
        {"label": "5 анализов — 390 ₽", "stars": 100, "rub": 390, "credits": 5},
        {"label": "15 анализов — 990 ₽", "stars": 250, "rub": 990, "credits": 15},
    ]

    @property
    def database_url(self) -> str:
        db_path = os.path.join(self.DATA_DIR, "bot.db")
        return f"sqlite+aiosqlite:///{db_path}"


config = Config()
