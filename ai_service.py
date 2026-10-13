import io
import json
import logging
import re
from collections import defaultdict
from typing import Dict, List, Optional
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
        self.fallback_model = "openai/gpt-oss-20b"
        self.owner_name = owner_name or "Zayniddin"
        self.custom_prompt = system_prompt
        self.histories: Dict[str, List[dict]] = defaultdict(list)
        self.max_history = 10
        self.chat_modes: Dict[str, str] = {}  # {chat_key: "standard" | "business" | "concise" | "detailed"}

    def set_owner_name(self, name: str):
        """Global ega ismini yangilash."""
        if name and name.strip():
            self.owner_name = name.strip()

    def set_mode(self, chat_key: str, mode: str):
        """Chat uchun AI uslubini tanlash."""
        self.chat_modes[chat_key] = mode

    def get_mode(self, chat_key: str) -> str:
        return self.chat_modes.get(chat_key, "standard")

    def clear_history(self, chat_key: str):
        """Suhbat tarixini tozalash."""
        if chat_key in self.histories:
            self.histories[chat_key] = []

    def is_creator_question(self, text: str) -> bool:
        """Egang kim, seni kim yaratgan kabi savollarni aniqlash."""
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
            r'kimning odamisan',
            r'kim seni qildi'
        ]
        for p in patterns:
            if re.search(p, t):
                return True
        return False

    def build_system_prompt(self, owner_name: str = None, mode: str = "standard") -> str:
        """Tanlangan rejim va ega ismiga moslangan aqlli tizim yo'riqnomasi."""
        name = owner_name or self.owner_name or "Zayniddin"
        
        mode_instruction = ""
        if mode == "concise":
            mode_instruction = "\nUSLUB: Qisqa, aniq, faqat eng muhim nuqtalarni lo'nda qilib yozing."
        elif mode == "detailed":
            mode_instruction = "\nUSLUB: To'liq, tahliliy va barcha tafsilotlarni keng yoritib tushuntiring."
        elif mode == "business":
            mode_instruction = "\nUSLUB: Rasmiy, ishbilarmon va mijozlar bilan savdo/hamkorlikka qaratilgan xushmuomala ohang."
        else:
            mode_instruction = "\nUSLUB: Samimiy, jonli, tabiiy insondek va qulay suhbatdosh ohangi."

        custom_instructions = f"\nQo'shimcha biznes yo'riqnomasi:\n{self.custom_prompt}\n" if self.custom_prompt else ""

        return (
            f"Siz — {name}ning aqlli, ko'p qirrali va zamonaviy shaxsiy yordamchisisiz (AI Assistant)!\n\n"
            f"ASOSIY QOIDALAR:\n"
            f"1. SAVOLLARGA TO'G'RI VA ANIQ JAVOB BERING: Har qanday savol (dasturlash, maslahatlar, ma'lumotlar, "
            f"kundalik savollar, biznes, hisob-kitoblar va boshqalar) bo'yicha yuqori intellekt bilan to'liq yordam bering.\n"
            f"2. QOLIPDAN MUTLAQO QOCHING: 'Falonchi hozir band' deb bir xil qolip gaplarni takrorlamang. "
            f"Mijoz yoki foydalanuvchining ayni damdagi savoliga darhol mazmunli javob bering.\n"
            f"3. IDENTIKLIK: Agar 'Seni kim yaratgan?', 'Egang kim?', 'Kimning yordamchisisan?' deb so'rashsa: "
            f"'Meni {name} yaratgan, men {name}ning shaxsiy AI yordamchisiman!' deb javob bering. "
            f"O'zingizni hech qachon OpenAI yoki boshqa tashqi tizim deb tanishtirmang.\n"
            f"4. TIL: O'zbek tilida (yoki foydalanuvchi qaysi tilda yozsa, shu tilda) beg'ubor, savodli va tabiiy gapiring."
            f"{mode_instruction}"
            f"{custom_instructions}"
        )

    def _get_history(self, chat_key: str) -> List[dict]:
        return self.histories[chat_key]

    def _add_to_history(self, chat_key: str, role: str, content: str):
        history = self.histories[chat_key]
        history.append({"role": role, "content": content})
        if len(history) > self.max_history * 2:
            self.histories[chat_key] = history[-(self.max_history * 2):]

    async def transcribe_audio(self, audio_bytes: bytes, filename: str = "voice.ogg") -> Optional[str]:
        """Groq Whisper modeli orqali ovozli xabarni matnga aylantirish."""
        try:
            audio_file = io.BytesIO(audio_bytes)
            audio_file.name = filename
            transcription = await self.client.audio.transcriptions.create(
                model="whisper-large-v3-turbo",
                file=audio_file,
                response_format="text"
            )
            if isinstance(transcription, str):
                return transcription.strip()
            return getattr(transcription, "text", "").strip()
        except Exception as e:
            logger.error(f"Whisper transkripsiya xatosi: {e}")
            return None

    async def get_reply(
        self,
        chat_key: str,
        user_message: str,
        sender_name: str = "",
        owner_name: str = None
    ) -> str:
        """
        AI orqali aqlli va tezkor javob olish.
        """
        active_owner = owner_name or self.owner_name or "Zayniddin"
        mode = self.get_mode(chat_key)
        self._add_to_history(chat_key, "user", user_message)

        # 1. Egang kim / Seni kim yaratgan savollari bo'lsa darhol tegishli ega nomi bilan javob berish
        if self.is_creator_question(user_message):
            reply = f"Meni {active_owner} yaratgan, men {active_owner}ning shaxsiy AI yordamchisiman!"
            self._add_to_history(chat_key, "assistant", reply)
            return reply

        system_instruction = self.build_system_prompt(active_owner, mode=mode)
        messages = [{"role": "system", "content": system_instruction}]
        messages.extend(self._get_history(chat_key))

        models_to_try = [self.model, self.fallback_model]

        for current_model in models_to_try:
            try:
                response = await self.client.chat.completions.create(
                    model=current_model,
                    messages=messages,
                    temperature=0.6,
                    frequency_penalty=0.2,
                    presence_penalty=0.2,
                    max_tokens=800,
                )
                reply = response.choices[0].message.content.strip()

                # Xavfsizlik filtri: agar javobda OpenAI/ChatGPT uchrasa tozalaymiz
                if "openai" in reply.lower() or "chatgpt" in reply.lower():
                    reply = re.sub(r'(?i)openai|chatgpt', active_owner, reply)

                self._add_to_history(chat_key, "assistant", reply)
                return reply

            except openai.RateLimitError as e:
                logger.warning(f"{current_model} RateLimit xatosi: {e}. Keyingi model sinab ko'riladi.")
                continue
            except openai.AuthenticationError as e:
                logger.error(f"API kaliti noto'g'ri: {e}")
                return f"Assalomu alaykum! Xabaringiz {active_owner}ga qabul qilindi, tez orada bog'lanamiz."
            except Exception as e:
                logger.warning(f"{current_model} xatolik berdi: {e}. Zaxira model tekshirilmoqda.")
                continue

        return f"Assalomu alaykum! Xabaringiz {active_owner}ga yetkazildi, tez orada javob qaytaramiz."
