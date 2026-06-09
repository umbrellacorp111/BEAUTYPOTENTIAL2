import base64
import json
import re
import logging
from openai import AsyncOpenAI
from bot.config import config

logger = logging.getLogger(__name__)

FREE_PROMPT = (
    "Ты — эксперт по анализу внешности. Оцени человека по фото.\n"
    "Параметры: имя={name}, возраст={age}, цели={goals}.\n"
    "Разрешённый режим: FACE_ANALYSIS_ONLY — оценивай только черты лица.\n\n"
    "Верни ТОЛЬКО JSON без пояснений. Ключи:\n"
    "current_potential: число 0-100\n"
    "growth_zone: строка — главная зона роста (только лицо)\n"
    "mistake: строка — главная ошибка (только лицо)\n"
    "potential_after: число 0-100\n\n"
    "Будь честным, конструктивным, без лести."
)

FULL_PROMPT = (
    "Ты — профессиональный AI-ассистент по анализу внешности.\n"
    "Разрешённый режим: FACE_ANALYSIS_ONLY.\n"
    "Параметры: имя={name}, возраст={age}, цели={goals}.\n\n"
    "Составь подробный разбор человека по фото (только черты лица).\n"
    "Напиши на русском, дружелюбно, конкретно. Включи:\n"
    "1. Оценку текущего потенциала в %\n"
    "2. 3 сильные стороны\n"
    "3. Главную ошибку\n"
    "4. 3 точки роста (80% результата)\n"
    "5. Прогноз после изменений в %\n"
    "6. Пошаговый план (5-7 шагов)\n"
    "7. Рекомендации\n\n"
    "Запрещено: анализ тела, фигуры, веса, осанки, одежды, стиля, гардероба, прически как отдельной темы."
)

client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    global client
    if client is None:
        api_key = config.OPENAI_API_KEY
        if not api_key:
            logger.error("OPENAI_API_KEY is not set!")
        logger.info(f"OPENAI_API_KEY loaded, starts with: {api_key[:15] if api_key else 'EMPTY'}")
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


MODE_SETTINGS = {
    "face": {
        "label": "анализ черт лица",
        "blocked_topics": [
            "тело", "фигура", "вес", "осанка",
            "одежда", "стиль одежды", "гардероб",
            "прическа", "причёска",
            "уверенность", "знакомства", "характер",
        ],
        "system_restriction": (
            "Ты — профессиональный AI-ассистент по анализу внешности.\n"
            "Твоя единственная разрешённая функция в этом режиме:\n"
            "👉 анализ черт лица человека по изображению или описанию\n\n"
            "Разрешённый режим: FACE_ANALYSIS_ONLY\n\n"
            "Запрещено:\n"
            "- анализ тела, фигуры, веса, осанки\n"
            "- анализ одежды, стиля, гардероба\n"
            "- анализ прически как отдельной темы\n"
            "- психологический анализ личности\n"
            "- советы по уверенности, жизни, знакомствам\n"
            "- любые темы вне внешности лица\n\n"
            "Если пользователь пытается выйти за рамки:\n"
            "→ вежливо откажись\n"
            "→ верни фокус на черты лица\n"
            "→ предложи купить расширенный разбор\n\n"
            "Разрешённые аспекты анализа:\n"
            "форма лица, симметрия, пропорции\n"
            "нос, глаза, губы, челюсть, скулы\n"
            "выраженность черт, визуальные сильные стороны лица\n"
            "рекомендации через лицо (борода/макияж/форма бровей)\n\n"
            "Стиль: кратко, структурированно, без воды, без оскорблений.\n"
            "Тон: профессиональный стилист / бьюти-аналитик.\n"
            "Формат: Форма лица → Основные черты → Сильные стороны → Что улучшить → Итог"
        ),
    },
}


def get_mode_label(mode: str) -> str:
    return MODE_SETTINGS.get(mode, MODE_SETTINGS["face"])["label"]


def check_mode_compliance(user_text: str, mode: str = "face") -> str | None:
    if mode not in MODE_SETTINGS:
        return None
    settings = MODE_SETTINGS[mode]
    text_lower = user_text.lower()
    for topic in settings["blocked_topics"]:
        if topic in text_lower:
            return (
                "Этот тип анализа доступен только в расширенных тарифах. "
                f"Сейчас активен режим: {settings['label']}."
            )
    return None


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


def build_dialogue_system(analysis: dict, name: str, age: int, goals: list[str],
                          mode: str = "face") -> str:
    goals_str = ", ".join(goals) if goals else "не указано"
    restriction = MODE_SETTINGS.get(mode, MODE_SETTINGS["face"])["system_restriction"]
    base = DIALOGUE_SYSTEM.format(
        name=name, age=age, goals=goals_str,
        potential=analysis["current_potential"],
        zone=analysis["growth_zone"],
        mistake=analysis["mistake"],
        after=analysis["potential_after"],
    )
    return base + "\n\n" + restriction


async def dialogue_start(analysis: dict, name: str, age: int, goals: list[str],
                         mode: str = "face") -> str:
    try:
        c = get_client()
        system = build_dialogue_system(analysis, name, age, goals, mode=mode)
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


def _format_dialogue(messages: list[dict]) -> str:
    lines = []
    for m in messages:
        role = "Клиент" if m["role"] == "user" else "Эксперт"
        lines.append(f"{role}: {m['content']}")
    return "\n".join(lines)


DIALOGUE_CONTEXT_PROMPT = (
    "\n\nДополнительный контекст из диалога с клиентом:\n{history}\n\n"
    "Учти его ответы и вопросы при составлении разбора. "
    "Особое внимание удели тому, что его волнует."
)


async def full_report(bot, photo_ids: list[str], name: str, age: int, goals: list[str],
                      dialogue_history: list[dict] | None = None) -> str:
    try:
        c = get_client()
        goals_str = ", ".join(goals) if goals else "не указано"
        prompt = FULL_PROMPT.format(name=name, age=age, goals=goals_str)
        if dialogue_history:
            history = _format_dialogue(dialogue_history)
            prompt += DIALOGUE_CONTEXT_PROMPT.format(history=history)
        content = [
            {"type": "text", "text": prompt},
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
