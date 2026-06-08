import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    ADMIN_CHAT_ID: int = int(os.getenv("ADMIN_CHAT_ID", "0"))

    DATA_DIR: str = os.getenv("DATA_DIR", "data")

    YUKASSA_PROVIDER_TOKEN: str = os.getenv("YUKASSA_PROVIDER_TOKEN", "")
    YUKASSA_SHOP_ID: str = os.getenv("YUKASSA_SHOP_ID", "")

    SUPPORT_USERNAME: str = os.getenv("SUPPORT_USERNAME", "@support")
    BOT_LINK: str = os.getenv("BOT_LINK", "https://t.me/bot")

    STARS_PRICE: int = 299
    RUB_PRICE: int = 1199

    @property
    def database_url(self) -> str:
        db_path = os.path.join(self.DATA_DIR, "bot.db")
        return f"sqlite+aiosqlite:///{db_path}"


config = Config()
