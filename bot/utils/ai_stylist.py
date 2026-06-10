import base64
import logging
from openai import AsyncOpenAI
from bot.config import config

logger = logging.getLogger(__name__)

STYLIST_SYSTEM_PROMPT = (
    "Ты — профессиональный AI-стилист. Твоя задача — давать советы по стилю одежды, "
    "причёскам, анализу образа, цветотипу, сочетанию вещей в гардеробе.\n\n"
    "Ты можешь:\n"
    "- анализировать образ по фото\n"
    "- рекомендовать фасоны одежды под тип фигуры\n"
    "- советовать причёски\n"
    "- подбирать цветовые сочетания\n"
    "- обсуждать стиль и внешность\n\n"
    "Ты НЕ даёшь советы по:\n"
    "- медицинским вопросам\n"
    "- психологии / психотерапии\n"
    "- отношениям и знакомствам\n\n"
    "Отвечай дружелюбно, профессионально, на русском языке.\n"
    "Если пользователь отправляет фото — анализируй образ, стиль, сочетания.\n"
    "Будь конкретным и полезным."
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
        else:
            for msg in history:
                messages.append(msg)

        resp = await c.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=800,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Stylist chat error: {e}", exc_info=True)
        return "❌ Ошибка при обращении к AI-стилисту. Попробуй ещё раз."
