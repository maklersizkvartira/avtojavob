import logging
from collections import defaultdict
from typing import Dict, List
import openai
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self, api_key: str, model: str = "openai/gpt-oss-120b", base_url: str = None, system_prompt: str = ""):
        if base_url:
            self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        else:
            self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.system_prompt = system_prompt or (
            "Siz do'stona, xushmuomala shaxsiy yordamchisiz. "
            "Telegram hisob egasi nomidan xushmuomalalik bilan qisqa va lo'nda javob bering."
        )
        # Suhbat tarixini saqlash: key -> chat_id yoki (connection_id, chat_id)
        self.histories: Dict[str, List[dict]] = defaultdict(list)
        self.max_history = 10

    def _get_history(self, chat_key: str) -> List[dict]:
        return self.histories[chat_key]

    def _add_to_history(self, chat_key: str, role: str, content: str):
        history = self.histories[chat_key]
        history.append({"role": role, "content": content})
        if len(history) > self.max_history * 2:
            self.histories[chat_key] = history[-(self.max_history * 2):]

    async def get_reply(self, chat_key: str, user_message: str, sender_name: str = "") -> str:
        """
        OpenAI orqali matnga aqlli javob oladi.
        """
        self._add_to_history(chat_key, "user", user_message)

        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(self._get_history(chat_key))

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=600,
            )
            reply = response.choices[0].message.content.strip()
            self._add_to_history(chat_key, "assistant", reply)
            return reply

        except openai.RateLimitError as e:
            logger.error(f"OpenAI RateLimit / Balans xatosi: {e}")
            if "credit_balance_exhausted" in str(e) or "insufficient_quota" in str(e):
                return (
                    "⚠️ [Avtojavob Tizimi]: Kechirasiz, hisobimdagi OpenAI balansi tugaganligi sababli "
                    "avtomatik javob bera olmadim. Tez orada egam o'zi sizga yozadi!"
                )
            return "Kechirasiz, sun'iy intellekt xizmati band. Birozdan so'ng qayta yozing."

        except openai.AuthenticationError as e:
            logger.error(f"OpenAI API kaliti xato: {e}")
            return "Kechirasiz, AI tizimi sozlamalarida xatolik bor (API kalit noto'g'ri)."

        except Exception as e:
            logger.error(f"AI javob olishda kutilmagan xatolik: {e}")
            return "Assalomu alaykum! Xabaringiz qabul qilindi, tez orada javob qaytaraman."
