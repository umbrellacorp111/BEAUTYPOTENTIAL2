# Потенциал внешности — Telegram Bot

Бот для продажи персонального разбора внешности.
Стек: Python 3.11, Aiogram 3, PostgreSQL, SQLAlchemy async.

## Быстрый запуск

```bash
cp .env.example .env
# заполнить .env
python -m bot.main
```

## Деплой на bothost.ru

1. Создай репозиторий на GitHub и залей туда этот код
2. Зарегистрируйся на [bothost.ru](https://bothost.ru)
3. Создай проект → выбери GitHub → подключи репозиторий
4. В настройках проекта добавь переменные окружения (см. `.env.example`):
   - `BOT_TOKEN` — токен бота от @BotFather
   - `ADMIN_CHAT_ID` — твой Telegram ID
   - `DB_HOST` / `DB_PORT` / `DB_NAME` / `DB_USER` / `DB_PASS` — данные PostgreSQL
   - `YUKASSA_PROVIDER_TOKEN` — токен ЮKassa (если используешь)
5. Нажми "Развернуть" — бот запустится автоматически
6. При каждом пуше в `main` бот будет обновляться автоматически

> **База данных:** bothost не предоставляет PostgreSQL на бесплатном тарифе. 
> Используй внешний провайдер (Supabase, Railway, ElephantSQL) или подключи тариф с managed DB.

## Команды

- `/start` — начать работу с ботом
- `/admin` — открыть админ-панель (только для админа)
