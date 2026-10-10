import asyncio
import logging
import os
import random
from typing import Optional, Tuple

from telethon import TelegramClient
from telethon.tl.functions.phone import DiscardCallRequest, RequestCallRequest
from telethon.tl.types import PhoneCallDiscardReasonDisconnect, PhoneCallProtocol

logger = logging.getLogger("call_service")

SESSION_FILE = "userbot_session"


class CallService:
    def __init__(self, api_id: Optional[int] = None, api_hash: Optional[str] = None):
        self.api_id = api_id or os.getenv("USERBOT_API_ID")
        self.api_hash = api_hash or os.getenv("USERBOT_API_HASH")
        if self.api_id:
            try:
                self.api_id = int(self.api_id)
            except ValueError:
                self.api_id = None

        self.client: Optional[TelegramClient] = None
        self._phone_code_hash: Optional[str] = None
        self._temp_phone: Optional[str] = None

    def is_configured(self) -> bool:
        """API ID va API Hash mavjudligini tekshirish."""
        return bool(self.api_id and self.api_hash)

    async def get_client(self) -> Optional[TelegramClient]:
        """Telethon clientni olish yoki ishga tushirish."""
        if not self.is_configured():
            return None

        if self.client is None:
            self.client = TelegramClient(SESSION_FILE, self.api_id, self.api_hash)
            await self.client.connect()

        if not self.client.is_connected():
            await self.client.connect()

        return self.client

    async def is_authorized(self) -> bool:
        """Userbot tizimga kirganligini tekshirish."""
        try:
            client = await self.get_client()
            if client is None:
                return False
            return await client.is_user_authorized()
        except Exception as e:
            logger.warning(f"Avtorizatsiya tekshirishda xatolik: {e}")
            return False

    async def get_me(self):
        """Userbot egasining ma'lumotlarini olish."""
        if await self.is_authorized():
            return await self.client.get_me()
        return None

    async def send_code_request(self, phone: str) -> Tuple[bool, str]:
        """Telefon raqamiga Telegram orqali tasdiqlash kodini jo'natish."""
        try:
            client = await self.get_client()
            if not client:
                return False, "API ID yoki API Hash kiritilmagan!"
            result = await client.send_code_request(phone)
            self._phone_code_hash = result.phone_code_hash
            self._temp_phone = phone
            return True, "Tasdiqlash kodi Telegramingizga yuborildi."
        except Exception as e:
            logger.error(f"Kod so'rashda xatolik: {e}")
            return False, f"Xatolik: {str(e)}"

    async def sign_in_with_code(self, code: str, password: Optional[str] = None) -> Tuple[bool, str]:
        """Kodni tekshirib tizimga kirish (kerak bo'lsa 2FA parol bilan)."""
        try:
            client = await self.get_client()
            if not client or not self._temp_phone or not self._phone_code_hash:
                return False, "Avval telefon raqamni kiritishingiz kerak."

            try:
                await client.sign_in(
                    phone=self._temp_phone,
                    code=code,
                    phone_code_hash=self._phone_code_hash
                )
                me = await client.get_me()
                return True, f"Muvaffaqiyatli ulandi! Profil: {me.first_name}"
            except Exception as e:
                err_str = str(e).lower()
                if "password" in err_str or "2fa" in err_str or "two-step" in err_str:
                    if password:
                        await client.sign_in(password=password)
                        me = await client.get_me()
                        return True, f"Muvaffaqiyatli ulandi! Profil: {me.first_name}"
                    return False, "2FA_PASSWORD_REQUIRED"
                return False, f"Xatolik: {str(e)}"
        except Exception as e:
            logger.error(f"Tizimga kirishda xatolik: {e}")
            return False, f"Xatolik: {str(e)}"

    async def make_call(self, target_user_id: int, duration_seconds: int = 25) -> Tuple[bool, str]:
        """
        Nishon foydalanuvchiga Telegram orqali ovozli qo'ng'iroq chaqiruvini yuborish.
        Foydalanuvchining telefonida Telegram qo'ng'irog'i (Ringing) jiringlaydi.
        """
        if not await self.is_authorized():
            return False, "Userbot avtorizatsiyadan o'tmagan."

        try:
            client = self.client
            target_entity = await client.get_input_entity(target_user_id)

            # E2E shifrlash uchun kalit xesh
            g_a_hash = os.urandom(32)
            protocol = PhoneCallProtocol(
                min_layer=65,
                max_layer=93,
                udp_p2p=True,
                udp_reflector=True,
                library_versions=["3.0.0"]
            )

            call_request = RequestCallRequest(
                user_id=target_entity,
                random_id=random.randint(1, 2147483647),
                g_a_hash=g_a_hash,
                protocol=protocol
            )

            call_result = await client(call_request)
            phone_call = call_result.phone_call

            logger.info(f"📞 Qo'ng'iroq boshlandi: ID={phone_call.id} Foydalanuvchi={target_user_id}")

            # Qo'ng'iroq jiringlashi uchun ma'lum vaqt kutish
            await asyncio.sleep(duration_seconds)

            # Vaqt tugagach qo'ng'iroqni tugatish
            try:
                await client(DiscardCallRequest(
                    peer=phone_call,
                    duration=duration_seconds,
                    reason=PhoneCallDiscardReasonDisconnect(),
                    connection_id=0
                ))
            except Exception as e:
                logger.debug(f"Discard call: {e}")

            return True, "Qo'ng'iroq amalga oshirildi!"

        except Exception as e:
            logger.error(f"Qo'ng'iroq qilishda xatolik: {e}")
            return False, f"Qo'ng'iroq xatosi: {str(e)}"

    async def send_direct_userbot_alert(self, target_user_id: int, message_text: str) -> bool:
        """Userbot orqali ham shaxsiy ogohlantirish yuborish."""
        if not await self.is_authorized():
            return False
        try:
            await self.client.send_message(target_user_id, message_text)
            return True
        except Exception as e:
            logger.warning(f"Userbot orqali xabar yuborishda xatolik: {e}")
            return False
