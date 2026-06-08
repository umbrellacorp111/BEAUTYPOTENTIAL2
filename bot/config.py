import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    ADMIN_CHAT_ID: int = int(os.getenv("ADMIN_CHAT_ID", "0"))

    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_NAME: str = os.getenv("DB_NAME", "appearance_bot")
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASS: str = os.getenv("DB_PASS", "password")

    YUKASSA_PROVIDER_TOKEN: str = os.getenv("YUKASSA_PROVIDER_TOKEN", "")
    YUKASSA_SHOP_ID: str = os.getenv("YUKASSA_SHOP_ID", "")

    SUPPORT_USERNAME: str = os.getenv("SUPPORT_USERNAME", "@support")
    BOT_LINK: str = os.getenv("BOT_LINK", "https://t.me/bot")

    STARS_PRICE: int = 299
    RUB_PRICE: int = 1199

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )


config = Config()
