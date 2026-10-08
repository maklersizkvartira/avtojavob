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
        self.model = model or "openai/gpt-oss-120b"
        self.system_prompt = system_prompt or (
            "Siz Telegram akkaunti egasining professional shaxsiy yordamchisisiz.\n"
            "ASOSIY VAZIFANGIZ:\n"
            "1. Siz hisob egasi nomidan xushmuomala, muloyim va samimiy javob berasiz.\n"
            "2. Salomlashishsa, iliq alik oling. Akkaunt egasi hozir bandligini, lekin xabarni darhol ularga yetkazganingizni bildiring.\n"
            "3. Mijozdan kerakli ma'lumotlarni (masalan: qaysi kvartira, qaysi hudud, narxi yoki qanday savoli borligini) qisqa so'rab oling.\n"
            "4. Qisqa, lo'nda va tabiiy (1-3 ta gap) o'zbek tilida yozing. Hech qachon bir xil qolip so'zlarni takrorlamang.\n"
            "5. Hisob egasi tez orada o'zi shaxsan to'liq javob qaytarishini ayting."
        )
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
        OpenAI/Groq orqali matnga aqlli javob oladi.
        """
        self._add_to_history(chat_key, "user", user_message)

        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(self._get_history(chat_key))

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                frequency_penalty=0.4,
                presence_penalty=0.4,
                max_tokens=600,
            )
            reply = response.choices[0].message.content.strip()
            self._add_to_history(chat_key, "assistant", reply)
            return reply

        except openai.RateLimitError as e:
            logger.error(f"OpenAI RateLimit / Balans xatosi: {e}")
            return "Assalomu alaykum! Xabaringiz hisob egasiga yetkazildi, tez orada javob yozadi."

        except openai.AuthenticationError as e:
            logger.error(f"API kaliti xato: {e}")
            return "Assalomu alaykum! Xabaringiz qabul qilindi, tez orada bog'lanamiz."

        except Exception as e:
            logger.error(f"AI javob olishda xatolik: {e}")
            return "Assalomu alaykum! Xabaringiz yetkazildi, tez orada o'zim sizga yozaman."
