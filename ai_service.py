import json
import logging
import re
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
        owner_name: str = "Zayniddin",
        system_prompt: str = ""
    ):
        if base_url:
            self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        else:
            self.client = AsyncOpenAI(api_key=api_key)
        self.model = model or "openai/gpt-oss-120b"
        self.owner_name = owner_name or "Zayniddin"
        self.custom_prompt = system_prompt
        self.histories: Dict[str, List[dict]] = defaultdict(list)
        self.max_history = 10

    def set_owner_name(self, name: str):
        """Ega ismini yangilash."""
        if name and name.strip():
            self.owner_name = name.strip()

    def is_creator_question(self, text: str) -> bool:
        """Egang kim, seni kim yaratgan kabi savollarni 100% aniqlash."""
        t = text.lower().strip()
        patterns = [
            r'kim yaratgan',
            r'egang kim',
            r'egeng kim',
            r'egasi kim',
            r'kimning boti',
            r'kimning yordamchisi',
            r'kim tuzgan',
            r'kim qildi',
            r'kim yozdi',
            r'kim ishlab chiq',
            r'open\s*ai',
            r'chat\s*gpt',
            r'kimning odamisan',
            r'sen kimsan',
            r'kim bu'
        ]
        for p in patterns:
            if re.search(p, t):
                return True
        return False

    def build_system_prompt(self) -> str:
        """Ega ismiga moslangan qat'iy tizim ko'rsatmasi."""
        name = self.owner_name or "Zayniddin"
        return (
            f"SIZNING IDENTIKLIGINGIZ (ENG MUHIM QAT'IY QOIDA):\n"
            f"Sizni faqat va faqat {name} yaratgan! Siz {name}ning sodiq shaxsiy yordamchisisiz!\n"
            f"Agar kimdir 'Seni kim yaratgan?', 'Egang kim?', 'Kimning botisan?' deb so'rasa, "
            f"har doim: 'Meni {name} yaratgan, men {name}ning shaxsiy yordamchisiman!' deb javob bering.\n"
            f"QAT'IYAN TAQIQLANADI: Hech qachon 'OpenAI', 'ChatGPT', 'til modeliman', 'sun'iy intellektman' deb aytmang! "
            f"Siz faqat {name}ning shaxsiy yordamchisisiz.\n\n"
            f"VAZIFANGIZ:\n"
            f"1. {name} nomidan xushmuomala, muloyim va tabiiy o'zbek tilida gaplashing.\n"
            f"2. Salomlashishsa, iliq alik oling. {name} hozir biroz bandligini, lekin xabarni darhol ularga yetkazganingizni bildiring.\n"
            f"3. Mijozdan kerakli ma'lumotlarni qisqa so'rab oling va {name} tez orada o'zi bog'lanishini ayting.\n"
            f"4. Javoblaringiz qisqa (1-3 ta gap) va lo'nda bo'lsin."
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

        # 1. Egang kim / Seni kim yaratgan savollari bo'lsa darhol 100% aniq javob berish
        if self.is_creator_question(user_message):
            reply = f"Meni {self.owner_name} yaratgan, men {self.owner_name}ning shaxsiy yordamchisiman!"
            self._add_to_history(chat_key, "assistant", reply)
            return reply

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

            # 2. Xavfsizlik filtri: Agar javobda tasodifan OpenAI yoki ChatGPT chiqsa, tozalaymiz
            if "openai" in reply.lower() or "chatgpt" in reply.lower():
                reply = f"Meni {self.owner_name} yaratgan, men {self.owner_name}ning shaxsiy yordamchisiman!"

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


