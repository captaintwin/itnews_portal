 #подключение к OpenAI / OpenRouter;

import time
import random
from core.logger import log
from core.config import OPENAI_API_KEY, MODEL_NAME

try:
    from openai import OpenAI
except ImportError:
    raise ImportError("Please install openai: pip install openai")

# Инициализация клиента
client = OpenAI(api_key=OPENAI_API_KEY)

# --- Параметры ---
MAX_RETRIES = 3       # количество попыток при ошибках API
DELAY_BETWEEN_CALLS = (1.5, 3.0)  # диапазон задержки между запросами (секунды)
MAX_INPUT_CHARS = 2000  # ограничим длину текста для экономии токенов


def summarize_text(text: str) -> str:
    """
    Генерирует короткое саммари для новости (1–2 предложения).
    Возвращает пустую строку при ошибке.
    """
    if not text or not text.strip():
        return ""

    # усечённый текст
    content = text.strip()[:MAX_INPUT_CHARS]
    prompt = (
        "Summarize the following news article in 2 short sentences, "
        "keeping it factual and neutral:\n\n" + content
    )

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            # делаем случайную задержку (чтобы не ловить rate limit)
            time.sleep(random.uniform(*DELAY_BETWEEN_CALLS))

            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=80,
                temperature=0.6,
            )

            summary = response.choices[0].message.content.strip()
            if summary:
                log.info(f"[LLM] Summary generated ({len(summary)} chars)")
                return summary

        except Exception as e:
            log.warning(f"[LLM] Attempt {attempt} failed: {e}")
            time.sleep(attempt * 2)  # экспоненциальная задержка

    log.error("[LLM] Failed to generate summary after retries.")
    return ""
