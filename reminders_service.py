import asyncio
from datetime import datetime, timedelta, timezone
import html
import logging
import uuid
from typing import Callable, Dict, List, Optional

logger = logging.getLogger("reminders_service")

# Toshkent vaqt zonasi (UTC+5) - server qayerda bo'lsa ham O'zbekiston vaqti olinadi
TZ_TASHKENT = timezone(timedelta(hours=5))

def get_now() -> datetime:
    """Toshkent vaqti (UTC+5)."""
    return datetime.now(TZ_TASHKENT).replace(tzinfo=None)

def safe_parse_dt(dt_str: str) -> Optional[datetime]:
    """Sanani xavfsiz o'qib, Toshkent vaqti (naive) formatiga keltiradi."""
    if not dt_str:
        return None
    try:
        dt = datetime.fromisoformat(dt_str)
        if dt.tzinfo is not None:
            dt = dt.astimezone(TZ_TASHKENT).replace(tzinfo=None)
        return dt
    except Exception:
        return None



class ReminderManager:
    def __init__(self, data_getter: Callable[[], dict], data_saver: Callable[[dict], None]):
        self.data_getter = data_getter
        self.data_saver = data_saver
        self.running = False

    def _get_reminders(self) -> List[dict]:
        data = self.data_getter()
        return data.setdefault("reminders", [])

    def add_reminder(
        self,
        task: str,
        rem_datetime_iso: str,
        source: str = "manual",
        client_name: str = "",
        target_chat_id: Optional[int] = None
    ) -> dict:
        """Yangi eslatma yaratish."""
        data = self.data_getter()
        reminders = data.setdefault("reminders", [])

        rem_id = f"rem_{uuid.uuid4().hex[:8]}"
        new_rem = {
            "id": rem_id,
            "task": task,
            "datetime_iso": rem_datetime_iso,
            "created_at": get_now().isoformat(),
            "source": source,  # "manual" yoki "ai_detected"
            "client_name": client_name,
            "target_chat_id": target_chat_id,
            "status": "pending",  # "pending", "triggered", "done", "cancelled"
            "call_status": "none"  # "none", "calling", "completed", "failed"
        }
        reminders.append(new_rem)
        self.data_saver(data)
        logger.info(f"⏰ Yangi eslatma qo'shildi: {task} ({rem_datetime_iso}) [ID: {rem_id}]")
        return new_rem

    def get_active_reminders(self) -> List[dict]:
        """Bajarilmagan faol eslatmalar."""
        reminders = self._get_reminders()
        return [r for r in reminders if r.get("status") in ["pending", "triggered"]]

    def get_reminder(self, rem_id: str) -> Optional[dict]:
        """ID bo'yicha eslatmani topish."""
        for r in self._get_reminders():
            if r.get("id") == rem_id:
                return r
        return None

    def cancel_reminder(self, rem_id: str) -> bool:
        """Eslatmani bekor qilish."""
        data = self.data_getter()
        for r in data.setdefault("reminders", []):
            if r.get("id") == rem_id:
                r["status"] = "cancelled"
                self.data_saver(data)
                return True
        return False

    def mark_done(self, rem_id: str) -> bool:
        """Eslatmani bajarilgan deb belgilash."""
        data = self.data_getter()
        for r in data.setdefault("reminders", []):
            if r.get("id") == rem_id:
                r["status"] = "done"
                self.data_saver(data)
                return True
        return False

    def snooze(self, rem_id: str, minutes: int = 10) -> Optional[dict]:
        """Eslatmani ma'lum daqiqaga kechiktirish."""
        data = self.data_getter()
        for r in data.setdefault("reminders", []):
            if r.get("id") == rem_id:
                new_dt = get_now() + timedelta(minutes=minutes)
                r["datetime_iso"] = new_dt.isoformat()
                r["status"] = "pending"
                r["call_status"] = "snoozed"
                self.data_saver(data)
                return r
        return None

    async def run_loop(self, on_trigger_callback: Callable[[dict], asyncio.Future]):
        """
        Doimiy tekshiruvchi asinxron loop.
        Har 10 soniyada vaqti kelgan eslatmalarni ishga tushiradi.
        """
        self.running = True
        logger.info("⏰ Eslatmalar va qo'ng'iroqlar skaneri ishga tushdi (Toshkent vaqti UTC+5).")

        while self.running:
            try:
                now = get_now()
                data = self.data_getter()
                reminders = data.setdefault("reminders", [])
                has_updates = False

                for rem in reminders:
                    if rem.get("status") == "pending":
                        dt_str = rem.get("datetime_iso")
                        rem_dt = safe_parse_dt(dt_str)
                        if rem_dt is None:
                            continue

                        # Agar vaqti yetgan yoki o'tgan bo'lsa
                        if now >= rem_dt:
                            logger.info(f"⏰ Eslatma vaqti keldi! ID: {rem.get('id')} Vazifa: {rem.get('task')}")
                            rem["status"] = "triggered"
                            rem["triggered_at"] = now.isoformat()
                            has_updates = True
                            # Eslatma va qo'ng'iroq chaqiruvini bajarish
                            asyncio.create_task(on_trigger_callback(rem))


                if has_updates:
                    self.data_saver(data)

            except Exception as e:
                logger.error(f"Eslatmalar tsiklida xatolik: {e}")

            await asyncio.sleep(10)
