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
        """Global fallback ega ismini yangilash."""
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
            r'kimning odamisan'
        ]
        for p in patterns:
            if re.search(p, t):
                return True
        return False

    def build_system_prompt(self, owner_name: str = None) -> str:
        """Ega ismiga moslangan aqlli va tabiiy tizim ko'rsatmasi."""
        name = owner_name or self.owner_name or "Akkaunt egasi"
        custom_instructions = f"\nQo'shimcha biznes yo'riqnomasi:\n{self.custom_prompt}\n" if self.custom_prompt else ""

        return (
            f"Siz — {name}ning aqlli, xushmuomala va tajribali shaxsiy yordamchisisiz!\n\n"
            f"ASOSIY QOIDALAR VA VAZIFALARINGIZ:\n"
            f"1. SAVOLLARGA TO'G'RI VA ANIQ JAVOB BERING: Foydalanuvchi yoki mijoz har qanday savol bersa "
            f"(xizmatlar, ko'chmas mulk, ma'lumotlar, narxlar, maslahatlar yoki oddiy suhbat), "
            f"siz sun'iy intellekt sifatida o'sha savolga to'liq, aqlli, mantiqan to'g'ri va yordam beruvchi javob qaytaring.\n"
            f"2. QOLIPDAN MUTLAQO QOCHING: Hech qachon 'Falonchi hozir band, tez orada bog'lanadi' deb bir xil ma'nosiz gapni takrorlamang! "
            f"Mijozning aniq savoliga darhol mazmunli va foydali javob bering.\n"
            f"3. IDENTIKLIK: Agar 'Seni kim yaratgan?', 'Egang kim?', 'Kimning yordamchisisan?' deb so'rashsa: "
            f"'Meni {name} yaratgan, men {name}ning shaxsiy yordamchisiman!' deb javob bering. "
            f"Hech qachon 'OpenAI', 'ChatGPT' deb aytmang.\n"
            f"4. MUOMALA: O'zbek tilida tabiiy, samimiy, ravon va xushmuomala gaplashing. Javoblaringiz tushunarli bo'lsin."
            f"{custom_instructions}"
        )

    def _get_history(self, chat_key: str) -> List[dict]:
        return self.histories[chat_key]

    def _add_to_history(self, chat_key: str, role: str, content: str):
        history = self.histories[chat_key]
        history.append({"role": role, "content": content})
        if len(history) > self.max_history * 2:
            self.histories[chat_key] = history[-(self.max_history * 2):]

    async def get_reply(self, chat_key: str, user_message: str, sender_name: str = "", owner_name: str = None) -> str:
        """
        OpenAI/Groq orqali har bir akkaunt egasi nomidan to'g'ri va aqlli javob oladi.
        """
        active_owner = owner_name or self.owner_name or "Akkaunt egasi"
        self._add_to_history(chat_key, "user", user_message)

        # 1. Egang kim / Seni kim yaratgan savollari bo'lsa darhol tegishli ega nomi bilan javob berish
        if self.is_creator_question(user_message):
            reply = f"Meni {active_owner} yaratgan, men {active_owner}ning shaxsiy yordamchisiman!"
            self._add_to_history(chat_key, "assistant", reply)
            return reply

        system_instruction = self.build_system_prompt(active_owner)
        messages = [{"role": "system", "content": system_instruction}]
        messages.extend(self._get_history(chat_key))

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.6,
                frequency_penalty=0.3,
                presence_penalty=0.3,
                max_tokens=600,
            )
            reply = response.choices[0].message.content.strip()

            # 2. Xavfsizlik filtri: Agar javobda OpenAI yoki ChatGPT chiqsa, tozalaymiz
            if "openai" in reply.lower() or "chatgpt" in reply.lower():
                reply = f"Meni {active_owner} yaratgan, men {active_owner}ning shaxsiy yordamchisiman!"

            self._add_to_history(chat_key, "assistant", reply)
            return reply

        except openai.RateLimitError as e:
            logger.error(f"OpenAI RateLimit xatosi: {e}")
            return f"Assalomu alaykum! Xabaringiz {active_owner}ga yetkazildi, tez orada javob beramiz."

        except openai.AuthenticationError as e:
            logger.error(f"API kaliti xato: {e}")
            return f"Assalomu alaykum! Xabaringiz {active_owner}ga qabul qilindi, tez orada bog'lanamiz."

        except Exception as e:
            logger.error(f"AI javob olishda xatolik: {e}")
            return f"Assalomu alaykum! Xabaringiz {active_owner}ga yetkazildi, tez orada javob qaytaramiz."
