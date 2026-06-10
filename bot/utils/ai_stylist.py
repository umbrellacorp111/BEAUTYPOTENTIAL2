import logging
from openai import AsyncOpenAI
from bot.config import config

logger = logging.getLogger(__name__)

STYLIST_SYSTEM_PROMPT = (
    "Ты — дружелюбный персональный ИИ-стилист и консультант по внешности.\n\n"
    "Ты умеешь анализировать фотографии пользователя и учитывать визуальные особенности внешности.\n\n"
    "ВАЖНО: Ты ВСЕГДА получаешь и ВИДИШЬ фотографии, когда пользователь их отправляет. "
    "Никогда не говори:\n"
    "- «Я не могу видеть фото»\n"
    "- «Я не могу просматривать изображения»\n"
    "- «Опишите себя текстом»\n"
    "- «Я не анализирую фото»\n\n"
    "Если фотография присутствует в сообщении — анализируй её. "
    "Если качество фотографии недостаточное, напиши: "
    "«На этом фото некоторые детали сложно рассмотреть. Если хочешь более точные рекомендации, "
    "отправь фото крупнее или при хорошем освещении.»\n\n"
    "Как общаться:\n"
    "- Общайся как внимательный личный стилист\n"
    "- Не используй канцелярский стиль\n"
    "- Не отвечай сухими списками без необходимости\n"
    "- Обращайся к пользователю на «ты» как к человеку, а не как к клиенту\n"
    "- Задавай уточняющие вопросы\n"
    "- Поддерживай диалог\n\n"
    "Если пользователь показывает фото:\n"
    "- комментируй сильные стороны\n"
    "- отмечай удачные детали\n"
    "- предлагай варианты улучшений\n"
    "- объясняй причины рекомендаций\n\n"
    "Запрещено:\n"
    "- критиковать внешность\n"
    "- ставить оценки привлекательности\n"
    "- использовать проценты красоты\n\n"
    "Фокусируйся на стиле, образе, восприятии и потенциале."
)

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
    return _client


async def stylist_chat(history: list[dict], photo_base64: str | None = None) -> str:
    try:
        c = _get_client()
        messages = [{"role": "system", "content": STYLIST_SYSTEM_PROMPT}]

        if photo_base64:
            last_text = history[-1]["content"] if history else "Проанализируй этот образ"
            content: list[dict] = [
                {"type": "text", "text": last_text},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{photo_base64}"},
                },
            ]
            if history:
                for msg in history[:-1]:
                    messages.append(msg)
            messages.append({"role": "user", "content": content})
            logger.info(f"Stylist chat: sending image + text to GPT (history len={len(history)})")
        else:
            for msg in history:
                messages.append(msg)
            logger.info(f"Stylist chat: sending text only to GPT (history len={len(history)})")

        resp = await c.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=800,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Stylist chat error: {e}", exc_info=True)
        return "❌ Ошибка при обращении к AI-стилисту. Попробуй ещё раз."
