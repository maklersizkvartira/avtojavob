import logging
from collections import defaultdict
from typing import Dict, List
import openai
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

class AIService:
    def __init__(
        self,
        api_key: str,
        model: str = "openai/gpt-oss-120b",
        base_url: str = None,
        owner_name: str = "Akkaunt egasi",
        system_prompt: str = ""
    ):
        if base_url:
            self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        else:
            self.client = AsyncOpenAI(api_key=api_key)
        self.model = model or "openai/gpt-oss-120b"
        self.owner_name = owner_name or "Akkaunt egasi"
        self.custom_prompt = system_prompt
        self.histories: Dict[str, List[dict]] = defaultdict(list)
        self.max_history = 10

    def set_owner_name(self, name: str):
        """Ega ismini yangilash."""
        if name and name.strip():
            self.owner_name = name.strip()

    def build_system_prompt(self) -> str:
        """Ega ismiga moslangan tizim ko'rsatmasini shakllantirish."""
        if self.custom_prompt:
            return self.custom_prompt

        name = self.owner_name
        return (
            f"Siz {name}ning professional, sodiq va samimiy shaxsiy yordamchisisiz.\n"
            f"QAT'IY VA MUHIM QOIDALAR:\n"
            f"1. Sizni {name} yaratgan va siz faqat {name}ning shaxsiy yordamchisisiz. "
            f"Agar sizdan 'Egang kim?', 'Seni kim yaratgan?', 'Kimning botisan?' yoki shunga o'xshash savol so'rashsa, "
            f"har doim hurmat bilan: 'Meni {name} yaratgan, men {name}ning shaxsiy yordamchisiman!' deb javob bering.\n"
            f"2. HECH QACHON 'Men OpenAI man', 'Men ChatGPT man', 'Men til modeliman', 'Men botman/sun'iy intellektman' deb aytmang! "
            f"Bu qat'iyan taqiqlanadi. Har doim {name}ning shaxsiy yordamchisi sifatida gapiring.\n"
            f"3. Doimo {name} nomidan xushmuomala, muloyim va samimiy muloqot qiling.\n"
            f"4. Salomlashishsa, iliq alik oling. {name} hozir biroz bandligini, lekin xabarni darhol ularga yetkazganingizni bildiring.\n"
            f"5. Mijozdan kerakli ma'lumotlarni qisqa so'rab oling va {name} tez orada o'zi to'liq bog'lanishini ayting.\n"
            f"6. Javoblaringiz qisqa (1-3 ta gap), tabiiy va adabiy o'zbek tilida bo'lsin. Bir xil qolipli so'zlarni takrorlamang."
        )

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

        system_instruction = self.build_system_prompt()
        messages = [{"role": "system", "content": system_instruction}]
        messages.extend(self._get_history(chat_key))

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.6,
                frequency_penalty=0.4,
                presence_penalty=0.4,
                max_tokens=500,
            )
            reply = response.choices[0].message.content.strip()
            self._add_to_history(chat_key, "assistant", reply)
            return reply

        except openai.RateLimitError as e:
            logger.error(f"OpenAI RateLimit xatosi: {e}")
            return f"Assalomu alaykum! Xabaringiz {self.owner_name}ga yetkazildi, tez orada o'zlari javob yozadilar."

        except openai.AuthenticationError as e:
            logger.error(f"API kaliti xato: {e}")
            return f"Assalomu alaykum! Xabaringiz {self.owner_name}ga qabul qilindi, tez orada bog'lanamiz."

        except Exception as e:
            logger.error(f"AI javob olishda xatolik: {e}")
            return f"Assalomu alaykum! Xabaringiz {self.owner_name}ga yetkazildi, tez orada javob qaytaramiz."
