import asyncio
import html
import io
import json
import logging
import os
import re
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    BusinessConnection,
    BusinessMessagesDeleted,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from aiogram.enums import ChatAction

from ai_service import AIService

# .env yuklash
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AI_BASE_URL = os.getenv("AI_BASE_URL", "https://api.groq.com/openai/v1")
AI_MODEL = os.getenv("AI_MODEL", "openai/gpt-oss-120b")
SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT", "")
OWNER_ID = os.getenv("OWNER_ID")
OWNER_NAME_DEFAULT = os.getenv("OWNER_NAME", "Zayniddin")
PORT = int(os.getenv("PORT", "8080"))

if not BOT_TOKEN:
    print("XATO: BOT_TOKEN topilmadi! .env faylini tekshiring.")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("telegram_business_bot")

DATA_FILE = "bot_data.json"
START_TIME = time.time()

# Toshkent vaqt mintaqasi (UTC+5)
TZ_TASHKENT = timezone(timedelta(hours=5))

def get_now_tashkent() -> datetime:
    """Toshkent vaqti (UTC+5)."""
    return datetime.now(TZ_TASHKENT)

def get_now_tashkent_str() -> str:
    """AI uchun chiroyli sana va vaqt matni."""
    weekdays = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"]
    now = get_now_tashkent()
    wd = weekdays[now.weekday()]
    return f"{now.strftime('%Y-%m-%d %H:%M:%S')} ({wd})"

# Loop va takrorlanishdan himoya qilish uchun oxirgi xabarlar keshi
PROCESSED_MESSAGES = set()
LAST_REPLY_TIME = {}  # {chat_key: timestamp}


def load_data() -> dict:
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Ma'lumotlar faylini o'qishda xatolik: {e}")
    return {
        "auto_reply_enabled": True,
        "connections": {},
        "admins": [],
        "user_names": {},
        "owner_statuses": {},
        "custom_prompts": {},
        "chat_bot_messages": {},
        "reminders": [],
        "stats": {
            "total_messages": 0,
            "ai_replies": 0,
            "voice_transcriptions": 0,
            "leads_detected": 0,
            "reminders_created": 0,
            "reminders_sent": 0
        }
    }


def save_data(data: dict):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ma'lumotlarni saqlashda xatolik: {e}")


bot_data = load_data()
if "auto_reply_enabled" not in bot_data:
    bot_data["auto_reply_enabled"] = True
if "reminders" not in bot_data:
    bot_data["reminders"] = []
if "stats" not in bot_data:
    bot_data["stats"] = {}

stats_defaults = {
    "total_messages": 0,
    "ai_replies": 0,
    "voice_transcriptions": 0,
    "leads_detected": 0,
    "reminders_created": 0,
    "reminders_sent": 0
}
for k, v in stats_defaults.items():
    if k not in bot_data["stats"]:
        bot_data["stats"][k] = v

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

ai_service = AIService(
    api_key=OPENAI_API_KEY,
    model=AI_MODEL,
    base_url=AI_BASE_URL,
    owner_name=OWNER_NAME_DEFAULT,
    system_prompt=SYSTEM_PROMPT
)

notification_map = {}


class FormStates(StatesGroup):
    waiting_for_reply = State()
    waiting_for_name = State()
    waiting_for_prompt = State()


# Yordamchi funksiyalar
def is_auto_reply_on() -> bool:
    return bool(bot_data.get("auto_reply_enabled", True))


def set_auto_reply(status: bool):
    bot_data["auto_reply_enabled"] = status
    save_data(bot_data)


def get_user_name(user_id: int, fallback: str = "Zayniddin") -> str:
    names = bot_data.setdefault("user_names", {})
    return names.get(str(user_id), fallback or OWNER_NAME_DEFAULT)


def set_user_name(user_id: int, name: str):
    names = bot_data.setdefault("user_names", {})
    names[str(user_id)] = name.strip()
    save_data(bot_data)


def get_all_target_admins() -> list:
    targets = list(bot_data.get("admins", []))
    if OWNER_ID:
        try:
            oid = int(OWNER_ID)
            if oid not in targets:
                targets.append(oid)
        except ValueError:
            pass
    return targets


def is_lead_intent(text: str) -> bool:
    patterns = [
        r'\+?998\s?\d{2}\s?\d{3}\s?\d{2}\s?\d{2}',
        r'\b\d{9}\b',
        r'telefon',
        r'nomer',
        r'bog\'lan',
        r'aloqa',
        r'uchrash',
        r'gaplashaylik',
        r'call',
        r'raqam'
    ]
    t = text.lower()
    for p in patterns:
        if re.search(p, t):
            return True
    return False


def get_settings_keyboard(user_id: int) -> InlineKeyboardMarkup:
    active = is_auto_reply_on()
    if active:
        power_btn = InlineKeyboardButton(text="🛑 Avtojavobni O'CHIRISH (To'xtatish)", callback_data="toggle_power_off")
    else:
        power_btn = InlineKeyboardButton(text="▶️ Avtojavobni YOQISH (Faollashtirish)", callback_data="toggle_power_on")

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [power_btn],
            [
                InlineKeyboardButton(text="⏰ Eslatmalar", callback_data="btn_list_reminders"),
                InlineKeyboardButton(text="🎭 AI Uslubi", callback_data="btn_select_mode")
            ],
            [
                InlineKeyboardButton(text="✏️ Ismni o'zgartirish", callback_data="btn_change_name"),
                InlineKeyboardButton(text="🧹 Xotirani tozalash", callback_data="btn_clear_history")
            ],
            [
                InlineKeyboardButton(text="📊 Statistika", callback_data="btn_show_stats"),
                InlineKeyboardButton(text="⚡ Server Holati", callback_data="btn_check_status")
            ]
        ]
    )


def get_mode_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🎯 Standart", callback_data="mode_standard"),
                InlineKeyboardButton(text="💼 Biznes & Savdo", callback_data="mode_business")
            ],
            [
                InlineKeyboardButton(text="⚡ Qisqa & Lo'nda", callback_data="mode_concise"),
                InlineKeyboardButton(text="📚 Chuqur tahliliy", callback_data="mode_detailed")
            ],
            [
                InlineKeyboardButton(text="◀️ Orqaga", callback_data="btn_back_settings")
            ]
        ]
    )


def add_new_reminder(
    task: str,
    target_iso: str,
    display_time: str,
    source: str,
    client_chat_id: int,
    client_name: str,
    owner_user_id: int = None,
    conn_id: str = None
) -> dict:
    """Yangi eslatmani bazaga qo'shish."""
    rem_id = f"rem_{uuid.uuid4().hex[:8]}"
    item = {
        "id": rem_id,
        "task": task,
        "target_iso": target_iso,
        "display_time": display_time or target_iso,
        "created_at": get_now_tashkent().isoformat(),
        "source": source,  # "business" yoki "direct"
        "conn_id": conn_id,
        "client_chat_id": client_chat_id,
        "client_name": client_name,
        "owner_user_id": owner_user_id,
        "status": "pending"  # "pending", "sent", "cancelled"
    }
    reminders = bot_data.setdefault("reminders", [])
    reminders.append(item)
    bot_data["stats"]["reminders_created"] += 1
    save_data(bot_data)
    logger.info(f"⏰ Yangi eslatma qo'shildi: {task} ({display_time}) [ID: {rem_id}]")
    return item


# ==========================================
# 1. TELEGRAM BUSINESS VOQEALARI (MUTLAQO XAVFSIZ & AQLLI)
# ==========================================

@dp.business_connection()
async def on_business_connection(conn: BusinessConnection):
    conn_id = conn.id
    user_id = conn.user.id
    connections = bot_data.setdefault("connections", {})

    if conn.is_enabled:
        connections[conn_id] = user_id
        save_data(bot_data)
        logger.info(f"✅ Telegram Business ulandi: conn_id={conn_id}, user={conn.user.full_name} ({user_id})")

        admins = bot_data.setdefault("admins", [])
        if user_id not in admins:
            admins.append(user_id)
            save_data(bot_data)

        if str(user_id) not in bot_data.get("user_names", {}):
            set_user_name(user_id, conn.user.first_name)

        owner_name = get_user_name(user_id, conn.user.first_name)
        try:
            cur_status = "YOQILGAN 🟢" if is_auto_reply_on() else "O'CHIRILGAN 🔴"
            welcome_txt = (
                f"🎉 <b>Assalomu alaykum, {html.escape(owner_name)}!</b>\n\n"
                "Telegram Business profilingiz botga muvaffaqiyatli ulandi!\n"
                f"• Avtojavob holati: <b>{cur_status}</b>\n"
                "• ⏰ <b>Aqlli Eslatmalar:</b> Mijozlar '...da eslatib qo'ying' desa, bot avtomatik rejalashtirib, vaqti kelganda eslatadi!\n"
                "• Istalgan vaqtda avtojavobni to'xtatish uchun: <code>/off</code>"
            )
            await bot.send_message(
                chat_id=user_id,
                text=welcome_txt,
                parse_mode="HTML",
                reply_markup=get_settings_keyboard(user_id)
            )
        except Exception as e:
            logger.warning(f"Xabar yuborishda xatolik: {e}")
    else:
        if conn_id in connections:
            del connections[conn_id]
            save_data(bot_data)
        logger.info(f"❌ Telegram Business uzildi: conn_id={conn_id}")


@dp.business_message()
async def on_business_message(message: Message):
    # 1. Agar avtojavob o'chirilgan bo'lsa
    if not is_auto_reply_on():
        return

    conn_id = message.business_connection_id
    if not conn_id:
        return

    sender = message.from_user
    if not sender:
        return

    # 2. Cheksiz loop himoyasi
    if sender.is_bot:
        return

    me = await bot.get_me()
    if sender.id == me.id:
        return

    # 3. Flood va takrorlanish filtri
    msg_unique_key = f"{conn_id}_{message.chat.id}_{message.message_id}"
    if msg_unique_key in PROCESSED_MESSAGES:
        return
    PROCESSED_MESSAGES.add(msg_unique_key)
    if len(PROCESSED_MESSAGES) > 500:
        PROCESSED_MESSAGES.clear()

    # 4. Egani aniqlash
    connections = bot_data.setdefault("connections", {})
    owner_user_id = connections.get(conn_id)

    if not owner_user_id:
        try:
            bc = await bot.get_business_connection(conn_id)
            if bc and bc.user:
                owner_user_id = bc.user.id
                connections[conn_id] = owner_user_id
                save_data(bot_data)
        except Exception as e:
            logger.warning(f"Business connection ma'lumotlarini olishda xatolik: {e}")

    client_chat_id = message.chat.id
    stored_key = f"{conn_id}_{client_chat_id}"

    # 5. Akkaunt egasi yozsa -> avto-tozalash
    if owner_user_id and sender.id == owner_user_id:
        logger.info(f"Akkaunt egasi ({sender.id}) chatga o'zi yozdi. Avtojavoblar tozalanadi.")
        bot_msgs = bot_data.setdefault("chat_bot_messages", {}).get(stored_key, [])
        if bot_msgs:
            for mid in bot_msgs:
                try:
                    await bot.delete_business_message(
                        business_connection_id=conn_id,
                        chat_id=client_chat_id,
                        message_id=mid
                    )
                except Exception:
                    pass
            bot_data["chat_bot_messages"][stored_key] = []
            save_data(bot_data)
        return

    # 6. Interval filtri
    now_ts = time.time()
    last_time = LAST_REPLY_TIME.get(stored_key, 0)
    if now_ts - last_time < 3:
        return
    LAST_REPLY_TIME[stored_key] = now_ts

    bot_data["stats"]["total_messages"] += 1
    owner_name = get_user_name(owner_user_id, OWNER_NAME_DEFAULT) if owner_user_id else OWNER_NAME_DEFAULT

    # Matn yoki Ovozni olish
    user_text = ""
    is_voice = False

    if message.text:
        user_text = message.text
    elif message.caption:
        user_text = message.caption
    elif message.voice or message.audio:
        is_voice = True
        bot_data["stats"]["voice_transcriptions"] += 1
        try:
            file_id = message.voice.file_id if message.voice else message.audio.file_id
            file_info = await bot.get_file(file_id)
            audio_io = io.BytesIO()
            await bot.download_file(file_info.file_path, destination=audio_io)
            audio_bytes = audio_io.getvalue()
            user_text = await ai_service.transcribe_audio(audio_bytes, filename="voice.ogg")
        except Exception as e:
            logger.error(f"Ovozni yuklab olishda xatolik: {e}")

    if not user_text or not user_text.strip():
        return

    chat_key = f"biz_{conn_id}_{client_chat_id}"
    await bot.send_chat_action(
        chat_id=client_chat_id,
        action=ChatAction.TYPING,
        business_connection_id=conn_id
    )

    # 🌟 7. AQLLI ESLATMANI AVTOMATIK ANIQLASH (NATURAL LANGUAGE REMINDER)
    reminder_alert_txt = ""
    reply_text = ""

    if ai_service.is_reminder_phrase(user_text):
        now_uz = get_now_tashkent_str()
        rem_data = await ai_service.extract_reminder(user_text, now_uz)
        if rem_data and rem_data.get("has_reminder") and rem_data.get("target_iso"):
            task_desc = rem_data.get("task", "Uchrashuv / Vazifa")
            target_iso = rem_data.get("target_iso")
            disp_time = rem_data.get("display_time", target_iso)

            add_new_reminder(
                task=task_desc,
                target_iso=target_iso,
                display_time=disp_time,
                source="business",
                client_chat_id=client_chat_id,
                client_name=sender.full_name,
                owner_user_id=owner_user_id,
                conn_id=conn_id
            )

            reply_text = f"Xo'p bo'ladi! {disp_time} sizga bu haqda albatta eslatib o'taman."
            reminder_alert_txt = (
                f"\n\n⏰ <b>YANGI AVTOMATIK ESLATMA REJALASHTIRILDI!</b>\n"
                f"📌 <b>Vazifa:</b> {html.escape(task_desc)}\n"
                f"⏱ <b>Vaqt:</b> {html.escape(disp_time)}\n"
                f"<i>Bot ushbu vaqtda mijoz chatiga sizning nomingizdan avtomatik eslatma yuboradi.</i>"
            )

    # Agar eslatma bo'lmasa oddiy AI javobini olamiz
    if not reply_text:
        reply_text = await ai_service.get_reply(
            chat_key=chat_key,
            user_message=user_text,
            sender_name=sender.full_name,
            owner_name=owner_name
        )

    bot_data["stats"]["ai_replies"] += 1

    try:
        sent = await bot.send_message(
            chat_id=client_chat_id,
            text=reply_text,
            business_connection_id=conn_id
        )

        bot_msgs = bot_data.setdefault("chat_bot_messages", {}).setdefault(stored_key, [])
        bot_msgs.append(sent.message_id)
        save_data(bot_data)
    except Exception as e:
        logger.error(f"Business xabar yuborishda xatolik: {e}")
        return

    # Akkaunt egasiga bildirishnoma
    if owner_user_id:
        username_str = f"@{sender.username}" if sender.username else f"ID: {sender.id}"
        voice_badge = " <i>(🎤 Ovozli xabar transkripsiyasi)</i>" if is_voice else ""
        lead_alert = ""
        if is_lead_intent(user_text):
            bot_data["stats"]["leads_detected"] += 1
            lead_alert = "\n\n🚨 <b>DIQQAT: Foydalanuvchi aloqa yoki telefon so'radi!</b>"

        notify_text = (
            f"📩 <b>Yangi mijoz xabari!</b>\n\n"
            f"👤 <b>Mijoz:</b> {html.escape(sender.full_name)} ({username_str})\n\n"
            f"💬 <b>Xabar{voice_badge}:</b>\n<blockquote>{html.escape(user_text)}</blockquote>\n\n"
            f"🤖 <b>AI bergan javob:</b>\n<blockquote>{html.escape(reply_text)}</blockquote>"
            f"{lead_alert}"
            f"{reminder_alert_txt}"
        )

        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✍️ Mijozga javob yozish", callback_data=f"rep_{client_chat_id}")]
            ]
        )
        try:
            sent_alert = await bot.send_message(
                chat_id=owner_user_id,
                text=notify_text,
                parse_mode="HTML",
                reply_markup=kb
            )
            notification_map[sent_alert.message_id] = {
                "conn_id": conn_id,
                "client_chat_id": client_chat_id,
                "client_name": sender.full_name
            }
        except Exception:
            pass


# ==========================================
# 2. TO'G'RIDAN-TO'G'RI CHAT (DIRECT MESSAGES)
# ==========================================

@dp.message(F.voice | F.audio)
async def on_direct_voice(message: Message):
    if message.from_user and message.from_user.is_bot:
        return

    bot_data["stats"]["total_messages"] += 1
    bot_data["stats"]["voice_transcriptions"] += 1

    sender = message.from_user
    user_name = get_user_name(sender.id, sender.first_name)

    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.RECORD_VOICE)
    status_msg = await message.reply("🎧 <i>Ovozingiz eshitilmoqda va matnga aylantirilmoqda...</i>", parse_mode="HTML")

    try:
        file_id = message.voice.file_id if message.voice else message.audio.file_id
        file_info = await bot.get_file(file_id)
        audio_io = io.BytesIO()
        await bot.download_file(file_info.file_path, destination=audio_io)
        audio_bytes = audio_io.getvalue()

        transcribed = await ai_service.transcribe_audio(audio_bytes, filename="voice.ogg")
        if not transcribed:
            await status_msg.edit_text("❌ Ovozni aniqlab bo'lmadi. Iltimos, qaytadan yozing yoki matn yuboring.")
            return

        # Eslatma tekshiruvi
        if ai_service.is_reminder_phrase(transcribed):
            now_uz = get_now_tashkent_str()
            rem_data = await ai_service.extract_reminder(transcribed, now_uz)
            if rem_data and rem_data.get("has_reminder") and rem_data.get("target_iso"):
                task_desc = rem_data.get("task", "Vazifa")
                target_iso = rem_data.get("target_iso")
                disp_time = rem_data.get("display_time", target_iso)

                add_new_reminder(
                    task=task_desc,
                    target_iso=target_iso,
                    display_time=disp_time,
                    source="direct",
                    client_chat_id=message.chat.id,
                    client_name=sender.full_name,
                    owner_user_id=sender.id
                )

                ans = (
                    f"🎙️ <b>Ovozingiz:</b> <i>«{html.escape(transcribed)}»</i>\n\n"
                    f"⏰ <b>Eslatma saqlandi!</b>\n\n"
                    f"📌 <b>Vazifa:</b> {html.escape(task_desc)}\n"
                    f"⏱ <b>Vaqt:</b> {html.escape(disp_time)}\n\n"
                    "<i>Belgilangan vaqt kelganda sizga eslatma yuboraman!</i>"
                )
                await status_msg.edit_text(ans, parse_mode="HTML")
                return

        chat_key = f"direct_{message.chat.id}"
        reply = await ai_service.get_reply(
            chat_key=chat_key,
            user_message=transcribed,
            sender_name=sender.full_name,
            owner_name=user_name
        )
        bot_data["stats"]["ai_replies"] += 1

        response_text = (
            f"🎙️ <b>Sizning ovozingiz:</b>\n<i>«{html.escape(transcribed)}»</i>\n\n"
            f"🤖 <b>Javob:</b>\n{reply}"
        )
        await status_msg.edit_text(response_text, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Ovozli xabarni qayta ishlashda xatolik: {e}")
        await status_msg.edit_text("❌ Ovozli xabarni qayta ishlashda xatolik yuz berdi.")


@dp.message(F.text & ~F.text.startswith("/"))
async def on_direct_text(message: Message, state: FSMContext):
    if message.from_user and message.from_user.is_bot:
        return

    cur_state = await state.get_state()
    if cur_state == FormStates.waiting_for_reply.state:
        data = await state.get_data()
        conn_id = data.get("conn_id")
        client_chat_id = data.get("client_chat_id")
        client_name = data.get("client_name")

        await state.clear()
        try:
            sent_msg = await bot.send_message(
                chat_id=client_chat_id,
                text=message.text,
                business_connection_id=conn_id
            )
            stored_key = f"{conn_id}_{client_chat_id}"
            bot_msgs = bot_data.setdefault("chat_bot_messages", {}).setdefault(stored_key, [])
            bot_msgs.append(sent_msg.message_id)
            save_data(bot_data)
            await message.reply(f"✅ Xabaringiz <b>{html.escape(client_name)}</b>ga yetkazildi!", parse_mode="HTML")
        except Exception as e:
            await message.reply(f"❌ Xabarni yetkazishda xatolik: {e}")
        return

    bot_data["stats"]["total_messages"] += 1
    sender = message.from_user
    user_name = get_user_name(sender.id, sender.first_name)

    # 🌟 7. Shaxsiy chatda eslatma so'ralsa
    if ai_service.is_reminder_phrase(message.text):
        now_uz = get_now_tashkent_str()
        rem_data = await ai_service.extract_reminder(message.text, now_uz)
        if rem_data and rem_data.get("has_reminder") and rem_data.get("target_iso"):
            task_desc = rem_data.get("task", "Vazifa")
            target_iso = rem_data.get("target_iso")
            disp_time = rem_data.get("display_time", target_iso)

            add_new_reminder(
                task=task_desc,
                target_iso=target_iso,
                display_time=disp_time,
                source="direct",
                client_chat_id=message.chat.id,
                client_name=sender.full_name,
                owner_user_id=sender.id
            )

            await message.answer(
                f"⏰ <b>Eslatma qabul qilindi va saqlandi!</b>\n\n"
                f"📌 <b>Vazifa:</b> {html.escape(task_desc)}\n"
                f"⏱ <b>Vaqt:</b> {html.escape(disp_time)}\n\n"
                "<i>Belgilangan vaqt bo'lganda sizga ushbu chat orqali eslataman!</i>",
                parse_mode="HTML"
            )
            return

    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    chat_key = f"direct_{message.chat.id}"

    reply = await ai_service.get_reply(
        chat_key=chat_key,
        user_message=message.text,
        sender_name=sender.full_name,
        owner_name=user_name
    )

    bot_data["stats"]["ai_replies"] += 1
    await message.answer(reply)


# ==========================================
# 3. BUYRUQLAR (COMMANDS)
# ==========================================

@dp.message(CommandStart())
async def cmd_start(message: Message):
    user = message.from_user
    admins = bot_data.setdefault("admins", [])
    if user.id not in admins:
        admins.append(user.id)
        save_data(bot_data)

    if str(user.id) not in bot_data.setdefault("user_names", {}):
        set_user_name(user.id, user.first_name)

    my_name = get_user_name(user.id, user.first_name)
    status_str = "🟢 YOQILGAN (Avtojavob beradi)" if is_auto_reply_on() else "🔴 O'CHIRILGAN (Avtojavob to'xtatilgan)"

    text = (
        f"👑 <b>Assalomu alaykum, {html.escape(my_name)}!</b>\n\n"
        f"⚡ <b>Avtojavob holati:</b> <b>{status_str}</b>\n\n"
        "• ⏰ <b>Aqlli Eslatmalar:</b> Siz yoki mijozlar shunchaki <i>«bugun 18:00 da falon ishni eslat»</i> deb yozsangiz kifoya — bot hech qanday buyruqsiz o'sha vaqtda avtomatik eslatadi!\n"
        "• <b>O'chirish uchun:</b> <code>/off</code> yoki pastdagi qizil tugmani bosing.\n"
        "• <b>Yoqish uchun:</b> <code>/on</code> yoki yashil tugmani bosing.\n\n"
        "<i>Quyidagi tugmalar orqali barcha sozlamalarni boshqaring:</i>"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=get_settings_keyboard(user.id))


@dp.message(Command("off"))
@dp.message(Command("stop"))
async def cmd_stop_auto(message: Message):
    set_auto_reply(False)
    await message.answer(
        "🛑 <b>AVTOJAVOB TO'LIQ O'CHIRILDI!</b>\n\n"
        "Bot endi Telegram Business orqali kelgan hech qanday xabarga javob yozmaydi.\n"
        "Qaytadan yoqish uchun: <code>/on</code> buyrug'ini yuboring.",
        parse_mode="HTML"
    )


@dp.message(Command("on"))
@dp.message(Command("start_bot"))
async def cmd_start_auto(message: Message):
    set_auto_reply(True)
    await message.answer(
        "🟢 <b>AVTOJAVOB YOQILDI!</b>\n\n"
        "Bot endi mijozlar yozganida AI orqali aqlli javob qaytaradi.\n"
        "O'chirish uchun: <code>/off</code> buyrug'ini yuboring.",
        parse_mode="HTML"
    )


@dp.message(Command("reminders"))
@dp.message(Command("eslatmalar"))
async def cmd_reminders(message: Message):
    reminders = bot_data.get("reminders", [])
    pending = [r for r in reminders if r.get("status") == "pending"]

    if not pending:
        await message.answer(
            "⏰ <b>Hozircha faol eslatmalar yo'q.</b>\n\n"
            "Eslatma yaratish uchun shunchaki yozing:\n"
            "<i>«10 daqiqadan keyin telefon qilishimni eslat»</i> yoki\n"
            "<i>«Bugun soat 19:30 da uchrashuv bor, eslat»</i>",
            parse_mode="HTML"
        )
        return

    text = "⏰ <b>Kutilayotgan Faol Eslatmalar:</b>\n\n"
    kb_rows = []
    for idx, r in enumerate(pending[:8], 1):
        src_label = "Mijoz uchun" if r.get("source") == "business" else "Shaxsiy"
        text += (
            f"<b>{idx}.</b> 📌 <b>{html.escape(r.get('task', ''))}</b>\n"
            f"   ⏱ Vaqt: <code>{html.escape(r.get('display_time', r.get('target_iso', '')))}</code>\n"
            f"   👤 Kimga: {html.escape(r.get('client_name', ''))} ({src_label})\n\n"
        )
        kb_rows.append([InlineKeyboardButton(text=f"❌ O'chirish: {idx}-eslatma", callback_data=f"delrem_{r['id']}")])

    kb = InlineKeyboardMarkup(inline_keyboard=kb_rows) if kb_rows else None
    await message.answer(text, parse_mode="HTML", reply_markup=kb)


@dp.message(Command("clear"))
@dp.message(Command("reset"))
async def cmd_clear(message: Message):
    chat_key = f"direct_{message.chat.id}"
    ai_service.clear_history(chat_key)
    await message.answer("🧹 <b>Suhbat xotirasi tozalandi!</b>", parse_mode="HTML")


@dp.message(Command("status"))
async def cmd_status(message: Message):
    me = await bot.get_me()
    active_count = len(bot_data.get("connections", {}))
    status_str = "🟢 YOQILGAN" if is_auto_reply_on() else "🔴 O'CHIRILGAN"
    uptime_sec = int(time.time() - START_TIME)
    uptime_str = f"{uptime_sec // 3600}s {(uptime_sec % 3600) // 60}d {uptime_sec % 60}son"
    pending_rem = len([r for r in bot_data.get("reminders", []) if r.get("status") == "pending"])

    status_text = (
        f"📊 <b>Bot Holati:</b>\n\n"
        f"🤖 Bot: @{me.username}\n"
        f"⚡ Avtojavob: <b>{status_str}</b>\n"
        f"⏰ Faol eslatmalar: <b>{pending_rem} ta</b>\n"
        f"🔗 Telegram Business: <b>{active_count} ta ulanish</b>\n"
        f"⏱ Ish vaqti: <code>{uptime_str}</code>\n"
        f"🟢 Server: Online"
    )
    await message.answer(status_text, parse_mode="HTML")


@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    stats = bot_data.get("stats", {})
    text = (
        "📈 <b>Bot Statistikasi:</b>\n\n"
        f"📨 Jami xabarlar: <b>{stats.get('total_messages', 0)} ta</b>\n"
        f"🤖 AI javoblar: <b>{stats.get('ai_replies', 0)} ta</b>\n"
        f"⏰ Rejalashtirilgan eslatmalar: <b>{stats.get('reminders_created', 0)} ta</b>\n"
        f"🔔 Yetkazilgan eslatmalar: <b>{stats.get('reminders_sent', 0)} ta</b>\n"
        f"🎙️ Ovozli transkripsiyalar: <b>{stats.get('voice_transcriptions', 0)} ta</b>\n"
        f"🚨 Muhim mijozlar: <b>{stats.get('leads_detected', 0)} ta</b>"
    )
    await message.answer(text, parse_mode="HTML")


@dp.message(Command("setname"))
async def cmd_setname(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Masalan: <code>/setname Zayniddin</code>", parse_mode="HTML")
        return
    new_name = args[1].strip()
    set_user_name(message.from_user.id, new_name)
    await message.answer(f"✅ Ism saqlandi: <b>{html.escape(new_name)}</b>", parse_mode="HTML")


# ==========================================
# 4. CALLBACK QUERIES
# ==========================================

@dp.callback_query(F.data.in_(["toggle_power_on", "toggle_power_off"]))
async def cb_toggle_power(call: CallbackQuery):
    turn_on = call.data == "toggle_power_on"
    set_auto_reply(turn_on)
    await call.message.edit_reply_markup(reply_markup=get_settings_keyboard(call.from_user.id))
    msg = "🟢 Avtojavob YOQILDI! Bot endi javob qaytaradi." if turn_on else "🛑 Avtojavob O'CHIRILDI! Bot endi javob yozmaydi."
    await call.answer(msg, show_alert=True)


@dp.callback_query(F.data == "btn_list_reminders")
async def cb_list_reminders(call: CallbackQuery):
    reminders = bot_data.get("reminders", [])
    pending = [r for r in reminders if r.get("status") == "pending"]

    if not pending:
        await call.answer("⏰ Hozircha faol eslatmalar yo'q.", show_alert=True)
        return

    text = "⏰ <b>Kutilayotgan Faol Eslatmalar:</b>\n\n"
    kb_rows = []
    for idx, r in enumerate(pending[:8], 1):
        src_label = "Mijoz uchun" if r.get("source") == "business" else "Shaxsiy"
        text += (
            f"<b>{idx}.</b> 📌 <b>{html.escape(r.get('task', ''))}</b>\n"
            f"   ⏱ <code>{html.escape(r.get('display_time', r.get('target_iso', '')))}</code> ({src_label})\n\n"
        )
        kb_rows.append([InlineKeyboardButton(text=f"❌ O'chirish: {idx}-eslatma", callback_data=f"delrem_{r['id']}")])

    kb_rows.append([InlineKeyboardButton(text="◀️ Bosh Menyu", callback_data="btn_back_settings")])
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows))
    await call.answer()


@dp.callback_query(F.data.startswith("delrem_"))
async def cb_delete_reminder(call: CallbackQuery):
    rem_id = call.data.replace("delrem_", "")
    reminders = bot_data.get("reminders", [])
    for r in reminders:
        if r.get("id") == rem_id:
            r["status"] = "cancelled"
            save_data(bot_data)
            await call.answer("❌ Eslatma bekor qilindi!", show_alert=True)
            break
    await cb_back_settings(call)


@dp.callback_query(F.data == "btn_select_mode")
async def cb_select_mode(call: CallbackQuery):
    await call.message.edit_text(
        "🎭 <b>AI Javob Uslubini Tanlang:</b>",
        parse_mode="HTML",
        reply_markup=get_mode_keyboard()
    )
    await call.answer()


@dp.callback_query(F.data.startswith("mode_"))
async def cb_apply_mode(call: CallbackQuery):
    chosen_mode = call.data.replace("mode_", "")
    chat_key = f"direct_{call.message.chat.id}"
    ai_service.set_mode(chat_key, chosen_mode)
    await call.answer(f"✅ AI Uslubi: {chosen_mode.upper()}", show_alert=True)
    await call.message.edit_text(
        f"✅ <b>AI Uslubi: {chosen_mode.upper()}</b> ga o'rnatildi!",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="◀️ Bosh Menyu", callback_data="btn_back_settings")]]
        )
    )


@dp.callback_query(F.data == "btn_back_settings")
async def cb_back_settings(call: CallbackQuery):
    user_id = call.from_user.id
    my_name = get_user_name(user_id, call.from_user.first_name)
    status_str = "🟢 YOQILGAN" if is_auto_reply_on() else "🔴 O'CHIRILGAN"

    await call.message.edit_text(
        f"👑 <b>Boshqaruv Paneli: {html.escape(my_name)}</b>\n\n"
        f"⚡ Avtojavob: <b>{status_str}</b>\n\n"
        "Kerakli bo'limni tanlang:",
        parse_mode="HTML",
        reply_markup=get_settings_keyboard(user_id)
    )
    await call.answer()


@dp.callback_query(F.data == "btn_clear_history")
async def cb_clear_history(call: CallbackQuery):
    chat_key = f"direct_{call.message.chat.id}"
    ai_service.clear_history(chat_key)
    await call.answer("🧹 Suhbat xotirasi tozalandi!", show_alert=True)


@dp.callback_query(F.data == "btn_show_stats")
async def cb_show_stats(call: CallbackQuery):
    stats = bot_data.get("stats", {})
    text = (
        "📈 <b>Statistika:</b>\n\n"
        f"📨 Jami xabarlar: <b>{stats.get('total_messages', 0)} ta</b>\n"
        f"🤖 AI javoblar: <b>{stats.get('ai_replies', 0)} ta</b>\n"
        f"⏰ Eslatmalar rejalashtirildi: <b>{stats.get('reminders_created', 0)} ta</b>\n"
        f"🔔 Yetkazilgan eslatmalar: <b>{stats.get('reminders_sent', 0)} ta</b>\n"
        f"🎙️ Ovozli transkripsiyalar: <b>{stats.get('voice_transcriptions', 0)} ta</b>\n"
        f"🚨 Muhim mijozlar: <b>{stats.get('leads_detected', 0)} ta</b>"
    )
    await call.message.reply(text, parse_mode="HTML")
    await call.answer()


@dp.callback_query(F.data == "btn_check_status")
async def cb_check_status(call: CallbackQuery):
    status_str = "🟢 YOQILGAN" if is_auto_reply_on() else "🔴 O'CHIRILGAN"
    text = f"⚡ <b>Avtojavob holati:</b> <b>{status_str}</b>\n🟢 Server: Online"
    await call.message.reply(text, parse_mode="HTML")
    await call.answer()


# ==========================================
# 5. AVTOMATIK ESLATMALAR WORKERI (BACKGROUND WORKER)
# ==========================================

async def reminders_worker():
    """Doimiy fonda eslatmalar vaqtini kuzatib boruvchi sikl."""
    logger.info("⏰ Eslatmalar tekshiruvchi worker ishga tushdi.")
    while True:
        try:
            now_dt = get_now_tashkent().replace(tzinfo=None)
            reminders = bot_data.get("reminders", [])
            has_changes = False

            for rem in reminders:
                if rem.get("status") != "pending":
                    continue

                target_iso = rem.get("target_iso")
                if not target_iso:
                    continue

                try:
                    target_dt = datetime.fromisoformat(target_iso)
                    if target_dt.tzinfo is not None:
                        target_dt = target_dt.astimezone(TZ_TASHKENT).replace(tzinfo=None)
                except Exception:
                    continue

                # Vaqti yetib keldumi?
                if now_dt >= target_dt:
                    rem["status"] = "sent"
                    rem["sent_at"] = now_dt.isoformat()
                    has_changes = True
                    bot_data["stats"]["reminders_sent"] += 1

                    task_text = rem.get("task", "")
                    disp_time = rem.get("display_time", "")
                    source = rem.get("source", "direct")
                    client_chat_id = rem.get("client_chat_id")
                    conn_id = rem.get("conn_id")
                    client_name = rem.get("client_name", "")
                    owner_user_id = rem.get("owner_user_id")

                    # 1. Telegram Business orqali mijozga yuborish
                    if source == "business" and conn_id and client_chat_id:
                        msg_to_client = (
                            f"Assalomu alaykum! Siz so'raganingizdek eslatib o'taman:\n"
                            f"📌 {task_text}"
                        )
                        try:
                            await bot.send_message(
                                chat_id=client_chat_id,
                                text=msg_to_client,
                                business_connection_id=conn_id
                            )
                            logger.info(f"✅ Mijozga eslatma yuborildi: {client_name} -> {task_text}")
                        except Exception as e:
                            logger.error(f"Mijozga eslatma yuborishda xatolik: {e}")

                        # Akkaunt egasiga ham bildirishnoma
                        if owner_user_id:
                            msg_to_owner = (
                                f"🔔 <b>[ESLATMA VAQTI KELDI]</b>\n\n"
                                f"👤 <b>Mijoz:</b> {html.escape(client_name)}\n"
                                f"📌 <b>Vazifa:</b> {html.escape(task_text)}\n"
                                f"⏱ <b>Vaqt:</b> {html.escape(disp_time)}\n\n"
                                f"✅ <i>Mijoz chatiga sizning nomingizdan eslatma avtomatik yetkazildi!</i>"
                            )
                            try:
                                await bot.send_message(chat_id=owner_user_id, text=msg_to_owner, parse_mode="HTML")
                            except Exception:
                                pass

                    # 2. Shaxsiy eslatma (Akkaunt egasining o'ziga)
                    else:
                        target_chat = client_chat_id or owner_user_id
                        if target_chat:
                            msg_self = (
                                f"🔔 <b>ESLATMA VAQTI BO'LDI!</b>\n\n"
                                f"📌 <b>Vazifa:</b> {html.escape(task_text)}\n\n"
                                f"<i>Rejalashtirilgan vaqt: {html.escape(disp_time)}</i>"
                            )
                            try:
                                await bot.send_message(chat_id=target_chat, text=msg_self, parse_mode="HTML")
                                logger.info(f"✅ Shaxsiy eslatma yuborildi: {task_text}")
                            except Exception as e:
                                logger.error(f"Shaxsiy eslatma yuborishda xatolik: {e}")

            if has_changes:
                save_data(bot_data)

        except Exception as e:
            logger.error(f"Eslatmalar workerida xatolik: {e}")

        await asyncio.sleep(5)


# ==========================================
# 6. HEALTHCHECK HTTP SERVER
# ==========================================

async def healthcheck_handler(request):
    uptime_sec = int(time.time() - START_TIME)
    return web.json_response({
        "status": "ok",
        "bot": "AvtoJavob AI",
        "auto_reply_enabled": is_auto_reply_on(),
        "uptime_seconds": uptime_sec,
        "connections": len(bot_data.get("connections", {})),
        "reminders_count": len(bot_data.get("reminders", []))
    })


async def start_http_server():
    app = web.Application()
    app.router.add_get("/", healthcheck_handler)
    app.router.add_get("/health", healthcheck_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"⚡ Railway Healthcheck HTTP Server listening on port {PORT}")


# ==========================================
# 7. ASOSIY ISHGA TUSHIRISH
# ==========================================

async def main():
    me = await bot.get_me()
    logger.info(f"Bot ishga tushdi: @{me.username} ({me.first_name})")
    print(f"\n==========================================")
    print(f"🤖 Bot muvaffaqiyatli ishga tushdi: @{me.username}")
    print(f"⚡ Avtojavob holati: {'YOQILGAN 🟢' if is_auto_reply_on() else 'O\'CHIRILGAN 🔴'}")
    print(f"⏰ Aqlli Avtomatik Eslatmalar Tizimi: FAOL")
    print(f"==========================================\n")

    # Parallel fon vazifalari
    asyncio.create_task(start_http_server())
    asyncio.create_task(reminders_worker())

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")
