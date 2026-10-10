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

    async def parse_natural_reminder(self, reminder_text: str, current_time_str: str) -> dict:
        """
        Foydalanuvchi kiritgan tabiiy matndan (masalan: 'ertaga soat 15:00 da Ali bilan uchrashuv')
        aniq sana, vaqt va vazifa nomini ajratib oladi.
        """
        prompt = (
            f"Joriy sana va vaqt: {current_time_str} (Toshkent vaqti, UTC+5).\n"
            f"Foydalanuvchi eslatma so'radi: \"{reminder_text}\"\n\n"
            f"Vazifangiz:\n"
            f"1. Eslatma qaysi sana va vaqtga belgilanganini hisoblang (masalan, 'ertaga', '10 minutdan keyin', 'bugun 18:00' va h.k.).\n"
            f"2. Vazifa sarlavhasini lo'nda qilib ajrating.\n"
            f"3. Natijani FAQAT quyidagi JSON formatida qaytaring, boshqa hech qanday so'z qo'shmang:\n"
            f"{{\n"
            f'  "success": true,\n'
            f'  "task": "Vazifa nomi",\n'
            f'  "datetime_iso": "YYYY-MM-DDTHH:MM:SS"\n'
            f"}}\n"
            f"Agar vaqtni mutlaqo aniqlab bo'lmasa:\n"
            f'{{"success": false, "task": "", "datetime_iso": "", "error": "Vaqt tushunarsiz"}}\n'
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Siz qat'iy ravishda faqat toza JSON formatida javob beruvchi yordamchisiz."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=200,
            )
            raw = response.choices[0].message.content.strip()
            # JSON formatini tozalash (agar ```json ... ``` bilan kelsa)
            if "```" in raw:
                raw = re.sub(r'```json\s*|\s*```', '', raw).strip()
            data = json.loads(raw)
            return data
        except Exception as e:
            logger.warning(f"Natural reminder parse error: {e}")
            return {"success": False, "task": reminder_text, "datetime_iso": "", "error": str(e)}

    async def detect_schedule_in_chat(self, user_msg: str, bot_reply: str, current_time_str: str) -> dict:
        """
        Mijoz bilan yozishmada uchrashuv, kelishuv, qo'ng'iroq qilish vaqti mavjudligini aniqlaydi.
        """
        prompt = (
            f"Joriy sana va vaqt: {current_time_str} (Toshkent vaqti, UTC+5).\n"
            f"Mijoz xabari: \"{user_msg}\"\n"
            f"Yordamchi javobi: \"{bot_reply}\"\n\n"
            f"Vazifa: Ushbu suhbatda mijoz yoki yordamchi o'rtasida aniq kelishuv, uchrashuv yoki qo'ng'iroqlashish vaqti bormi?\n"
            f"(Masalan: 'Ertaga 15:00 da kelaman', 'Bugun 18:00 da gaplashamiz', 'Dushanba soat 10 da eslatib yuboring').\n\n"
            f"Agar aniq vaqtli kelishuv/uchrashuv bo'lsa, FAQAT quyidagi JSON formatida javob bering:\n"
            f"{{\n"
            f'  "has_schedule": true,\n'
            f'  "task": "Uchrashuv/bog\'lanish maqsadi",\n'
            f'  "datetime_iso": "YYYY-MM-DDTHH:MM:SS",\n'
            f'  "summary": "Qisqa izoh"\n'
            f"}}\n"
            f"Agar aniq vaqtli kelishuv bo'lmasa, FAQAT:\n"
            f'{{"has_schedule": false}}\n'
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Siz qat'iy ravishda faqat toza JSON formatida javob beruvchi yordamchisiz."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=250,
            )
            raw = response.choices[0].message.content.strip()
            if "```" in raw:
                raw = re.sub(r'```json\s*|\s*```', '', raw).strip()
            data = json.loads(raw)
            return data
        except Exception as e:
            logger.debug(f"Schedule detection error: {e}")
            return {"has_schedule": False}

