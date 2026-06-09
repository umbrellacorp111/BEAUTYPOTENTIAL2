import base64
import json
import re
import logging
from openai import AsyncOpenAI
from bot.config import config

logger = logging.getLogger(__name__)

FREE_PROMPT = (
    "Ты — эксперт по анализу внешности. Оцени человека по фото.\n"
    "Параметры: имя={name}, возраст={age}, цели={goals}.\n\n"
    "Верни ТОЛЬКО JSON без пояснений. Ключи:\n"
    "current_potential: число 0-100\n"
    "growth_zone: строка — главная зона роста\n"
    "mistake: строка — главная ошибка\n"
    "potential_after: число 0-100\n\n"
    "Будь честным, конструктивным, без лести."
)

FULL_PROMPT = (
    "Ты — эксперт по анализу внешности. Составь подробный разбор человека по фото.\n"
    "Параметры: имя={name}, возраст={age}, цели={goals}.\n\n"
    "Напиши на русском, дружелюбно, конкретно. Включи:\n"
    "1. Оценку текущего потенциала в %\n"
    "2. 3 сильные стороны\n"
    "3. Главную ошибку\n"
    "4. 3 точки роста (80% результата)\n"
    "5. Прогноз после изменений в %\n"
    "6. Пошаговый план (5-7 шагов)\n"
    "7. Рекомендации"
)

client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    global client
    if client is None:
        api_key = config.OPENAI_API_KEY
        if not api_key:
            logger.error("OPENAI_API_KEY is not set!")
        client = AsyncOpenAI(api_key=api_key)
    return client


async def _photo_to_base64(bot, file_id: str) -> str:
    file = await bot.get_file(file_id)
    tg_path = file.file_path
    if not tg_path:
        raise ValueError(f"No file_path for file_id {file_id}")
    file_bytes = await bot.download_file(tg_path)
    data = file_bytes.read()
    return base64.b64encode(data).decode("utf-8")


def _extract_json(text: str) -> dict | None:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        text = text.rsplit("```", 1)[0]
        text = text.strip()
        if text.startswith("json"):
            text = text[4:].strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


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
        logger.info("Free analysis: sending to GPT-4o-mini...")
        resp = await c.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": content}],
            max_tokens=500,
        )
        text = resp.choices[0].message.content.strip()
        logger.info(f"Free analysis raw response: {text[:300]}")
        data = _extract_json(text)
        if not data:
            raise ValueError(f"No valid JSON in response")
        return {
            "current_potential": data.get("current_potential", 50),
            "growth_zone": data.get("growth_zone", "не определено"),
            "mistake": data.get("mistake", "не определено"),
            "potential_after": data.get("potential_after", 75),
        }
    except Exception as e:
        logger.error(f"AI free analysis error: {e}", exc_info=True)
        return {
            "current_potential": 50,
            "growth_zone": "требуется повторный анализ",
            "mistake": "ошибка анализа, попробуйте снова",
            "potential_after": 75,
        }


DIALOGUE_SYSTEM = (
    "Ты — эксперт-консультант по внешности. Ты уже проанализировал фото человека.\n"
    "У тебя есть его данные: имя={name}, возраст={age}, цели={goals}.\n"
    "Результаты анализа: потенциал {potential}%, зона роста: {zone}, ошибка: {mistake}, прогноз: {after}%.\n\n"
    "Сейчас ты ведёшь короткий диалог 3-5 сообщений.\n"
    "Правила:\n"
    "- Не раскрывай полный анализ сразу\n"
    "- Задавай уточняющие вопросы по внешности\n"
    "- Отвечай на ответы, выстраивай беседу\n"
    "- После 3-5 сообщений плавно подведи к тому, что полный отчёт готов\n"
    "- Финальное сообщение должно предлагать открыть полный разбор\n"
    "- Пиши на русском, дружелюбно, от первого лица"
)


def build_dialogue_system(analysis: dict, name: str, age: int, goals: list[str]) -> str:
    goals_str = ", ".join(goals) if goals else "не указано"
    return DIALOGUE_SYSTEM.format(
        name=name, age=age, goals=goals_str,
        potential=analysis["current_potential"],
        zone=analysis["growth_zone"],
        mistake=analysis["mistake"],
        after=analysis["potential_after"],
    )


async def dialogue_start(analysis: dict, name: str, age: int, goals: list[str]) -> str:
    try:
        c = get_client()
        system = build_dialogue_system(analysis, name, age, goals)
        resp = await c.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": "Я готов ответить на вопросы. Спроси меня что-нибудь о моей внешности."},
            ],
            max_tokens=300,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"dialogue_start error: {e}", exc_info=True)
        return "Расскажи, что тебя больше всего не устраивает в своей внешности?"


async def dialogue_continue(history: list[dict], system: str) -> str:
    try:
        c = get_client()
        messages = [{"role": "system", "content": system}] + history
        resp = await c.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=300,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"dialogue_continue error: {e}", exc_info=True)
        return "Понял. Хочешь увидеть полный разбор?"


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
        logger.info("Full report: sending to GPT-4o-mini...")
        resp = await c.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": content}],
            max_tokens=2000,
        )
        result = resp.choices[0].message.content.strip()
        logger.info(f"Full report received, length={len(result)}")
        return result
    except Exception as e:
        logger.error(f"AI full report error: {e}", exc_info=True)
        return "❌ Ошибка при генерации разбора. Проверь, что OpenAI API ключ работает и на балансе есть средства."
