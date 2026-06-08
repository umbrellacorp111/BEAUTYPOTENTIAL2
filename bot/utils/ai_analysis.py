import base64
import json
import logging
from openai import AsyncOpenAI
from bot.config import config

logger = logging.getLogger(__name__)

FREE_PROMPT = (
    "Ты — эксперт по анализу внешности. Оцени человека по фото.\n"
    "Верни ТОЛЬКО JSON без пояснений в формате:\n"
    "{\n"
    '  "current_potential": число от 0 до 100,\n'
    '  "growth_zone": "одна фраза — главная зона роста",\n'
    '  "mistake": "одна фраза — главная ошибка в образе",\n'
    '  "potential_after": число от 0 до 100\n'
    "}\n"
    "Параметры: имя={name}, возраст={age}, цели={goals}.\n"
    "Будь честным, конструктивным, без лести."
)

FULL_PROMPT = (
    "Ты — эксперт по анализу внешности. Составь подробный персональный разбор человека по фото.\n"
    "Параметры: имя={name}, возраст={age}, цели={goals}.\n\n"
    "Напиши разбор в свободной форме, включив:\n"
    "1. Оценку текущего потенциала в %\n"
    "2. 3 сильные стороны внешности\n"
    "3. Главную ошибку в образе\n"
    "4. 3 точки роста, которые дадут 80% результата\n"
    "5. Прогноз результата после изменений в %\n"
    "6. Пошаговый план действий (5-7 шагов)\n"
    "7. Персональные рекомендации\n\n"
    "Пиши на русском, дружелюбно, конкретно, без воды."
)

client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    global client
    if client is None:
        client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
    return client


async def _photo_to_base64(bot, file_id: str) -> str:
    file = await bot.get_file(file_id)
    file_bytes = await bot.download_file(file.file_path)
    data = file_bytes.read()
    return base64.b64encode(data).decode("utf-8")


async def free_analysis(bot, photo_ids: list[str], name: str, age: int, goals: list[str]) -> dict:
    try:
        c = get_client()
        goals_str = ", ".join(goals) if goals else "не указано"
        content = [
            {"type": "text", "text": FREE_PROMPT.format(name=name, age=age, goals=goals_str)},
        ]
        for fid in photo_ids[:2]:
            b64 = await _photo_to_base64(bot, fid)
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
            })
        resp = await c.chat.completions.create(
            model="gpt-5.4-mini",
            messages=[{"role": "user", "content": content}],
            max_tokens=500,
        )
        text = resp.choices[0].message.content.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        data = json.loads(text.strip())
        return {
            "current_potential": data.get("current_potential", 50),
            "growth_zone": data.get("growth_zone", "не определено"),
            "mistake": data.get("mistake", "не определено"),
            "potential_after": data.get("potential_after", 75),
        }
    except Exception as e:
        logger.error(f"AI free analysis error: {e}")
        return {
            "current_potential": 50,
            "growth_zone": "требуется повторный анализ",
            "mistake": "ошибка анализа, попробуйте снова",
            "potential_after": 75,
        }


async def full_report(bot, photo_ids: list[str], name: str, age: int, goals: list[str]) -> str:
    try:
        c = get_client()
        goals_str = ", ".join(goals) if goals else "не указано"
        content = [
            {"type": "text", "text": FULL_PROMPT.format(name=name, age=age, goals=goals_str)},
        ]
        for fid in photo_ids[:3]:
            b64 = await _photo_to_base64(bot, fid)
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
            })
        resp = await c.chat.completions.create(
            model="gpt-5.4-mini",
            messages=[{"role": "user", "content": content}],
            max_tokens=2000,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"AI full report error: {e}")
        return "Извините, произошла ошибка при генерации разбора. Попробуйте позже."
