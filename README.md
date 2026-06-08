# Потенциал внешности — Telegram Bot

Бот для продажи персонального разбора внешности.
Стек: Python 3.11, Aiogram 3, SQLite (aiosqlite), SQLAlchemy async.

## Быстрый запуск

```bash
cp .env.example .env
# заполнить .env (BOT_TOKEN, ADMIN_CHAT_ID)
python -m bot.main
```

## Деплой на bothost.ru

1. Создай репозиторий на GitHub и залей туда этот код
2. Зарегистрируйся на [bothost.ru](https://bothost.ru)
3. Создай проект → GitHub → подключи репозиторий → ветка `main`
4. В настройках проекта → **Env vars** → вставь содержимое `.env` и замени значения:
   - `BOT_TOKEN` — токен от @BotFather
   - `ADMIN_CHAT_ID` — твой Telegram ID (узнать у @userinfobot)
   - `DATA_DIR=/app/data` — постоянное хранилище (работает на платных тарифах)
5. Нажми "Развернуть"

> На платных тарифах bothost данные сохраняются в `/app/data/bot.db` и не пропадают при перезапуске.

## Команды

- `/start` — начать работу с ботом
- `/admin` — открыть админ-панель (только для админа)
