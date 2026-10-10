import asyncio
import html
import json
import logging
import os
import re
import sys
from datetime import datetime
from dotenv import load_dotenv

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
from call_service import CallService
from reminders_service import ReminderManager

# .env faylini yuklash
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AI_BASE_URL = os.getenv("AI_BASE_URL")
AI_MODEL = os.getenv("AI_MODEL", "openai/gpt-oss-120b")
SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT", "")
OWNER_ID = os.getenv("OWNER_ID")

if not BOT_TOKEN:
    print("XATO: BOT_TOKEN ko'rsatilmagan! .env faylini tekshiring.")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("telegram_business_bot")

# Ma'lumotlarni doimiy saqlash fayli
DATA_FILE = "bot_data.json"

def load_data() -> dict:
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Ma'lumotlar faylini o'qishda xatolik: {e}")
    return {
        "connections": {},
        "admins": [],
        "owner_name": "Zayniddin",
        "owner_status": "offline",  # "online" yoki "offline"
        "chat_bot_messages": {},    # { "conn_id_chat_id": [msg_id, ...] }
        "admin_notifications": {},  # { "conn_id_chat_id": [[admin_id, msg_id], ...] }
        "reminders": []             # [ { "id": "...", "task": "...", ... } ]
    }

def save_data(data: dict):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ma'lumotlar faylini saqlashda xatolik: {e}")

bot_data = load_data()
bot_data.setdefault("owner_status", "offline")
bot_data.setdefault("chat_bot_messages", {})
bot_data.setdefault("admin_notifications", {})
bot_data.setdefault("reminders", [])
if not bot_data.get("owner_name") or bot_data.get("owner_name") == "Akkaunt egasi":
    bot_data["owner_name"] = "Zayniddin"

current_owner_name = bot_data["owner_name"]

# Servislarni ishga tushirish
ai_service = AIService(
    api_key=OPENAI_API_KEY,
    model=AI_MODEL,
    base_url=AI_BASE_URL if AI_BASE_URL else None,
    owner_name=current_owner_name,
    system_prompt=SYSTEM_PROMPT
)
call_service = CallService()
reminder_manager = ReminderManager(load_data, save_data)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Xotiradagi xabarlar xaritasi (notification_msg_id -> client info)
notification_map: dict[int, dict] = {}


class FormStates(StatesGroup):
    waiting_for_reply = State()
    waiting_for_owner_name = State()
    waiting_for_reminder_text = State()
    waiting_for_userbot_phone = State()
    waiting_for_userbot_code = State()
    waiting_for_userbot_password = State()


# ==========================================
# YORDAMCHI VA TOZALASH FUNKSIYALARI
# ==========================================

def get_all_target_admins() -> set[int]:
    """Barcha bildirishnoma oluvchi adminlar va hisob egalari ID lari ro'yxatini qaytaradi."""
    targets = set(bot_data.get("admins", []))
    if OWNER_ID:
        try:
            targets.add(int(OWNER_ID))
        except ValueError:
            pass
    for conn in bot_data.get("connections", {}).values():
        if conn.get("owner_chat_id"):
            targets.add(int(conn["owner_chat_id"]))
        elif conn.get("owner_id"):
            targets.add(int(conn["owner_id"]))
    return targets


async def on_reminder_triggered(rem: dict):
    """Eslatma vaqti yetganda qo'ng'iroq qilish va barcha adminlarni ogohlantirish."""
    targets = get_all_target_admins()
    rem_id = rem.get("id")
    task_text = rem.get("task", "Muhim vazifa")
    dt_str = rem.get("datetime_iso", "")
    source = rem.get("source", "manual")
    client_name = rem.get("client_name", "")

    time_display = dt_str
    try:
        dt_obj = datetime.fromisoformat(dt_str)
        time_display = dt_obj.strftime("%H:%M (%d-%m-%Y)")
    except Exception:
        pass

    source_text = "✍️ Siz o'zingiz kiritgansiz" if source == "manual" else f"🤖 AI mijoz ({client_name}) suhbatidan aniqlagan"

    userbot_is_ready = await call_service.is_authorized()
    call_notice = (
        "📞 <b>Qo'ng'iroq jiringlamoqda!</b> Telefoningizga qarang..."
        if userbot_is_ready
        else "⚠️ <i>Userbot hali ulanmagan. To'liq qo'ng'iroq uchun /userbot sozlamasini bajaring.</i>"
    )

    alert_text = (
        "🚨 <b>DIQQAT! MUHIM ESLATMA VAQTI KELDI!</b> 🚨\n\n"
        f"📝 <b>Vazifa:</b> <blockquote>{html.escape(task_text)}</blockquote>\n"
        f"⏰ <b>Belgilangan vaqt:</b> <b>{time_display}</b>\n"
        f"ℹ️ <b>Manba:</b> {source_text}\n\n"
        f"{call_notice}"
    )

    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Bajarildi / Qabul qildim", callback_data=f"rem_done_{rem_id}")],
            [InlineKeyboardButton(text="⏰ 10 daqiqadan so'ng yana eslat", callback_data=f"rem_snooze_{rem_id}_10")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"rem_cancel_{rem_id}")]
        ]
    )

    # 1. Telegram bot orqali bildirishnoma jo'natish
    for adm_id in targets:
        try:
            await bot.send_message(
                chat_id=adm_id,
                text=alert_text,
                parse_mode="HTML",
                reply_markup=markup
            )
        except Exception as e:
            logger.error(f"Eslatma yuborishda xatolik ({adm_id}): {e}")

    # 2. Userbot orqali Telegramda ovozli qo'ng'iroq qilish
    if userbot_is_ready:
        for adm_id in targets:
            try:
                logger.info(f"📞 Eslatma qo'ng'irog'i yo'llanmoqda: {adm_id}")
                asyncio.create_task(call_service.make_call(target_user_id=adm_id, duration_seconds=25))
                asyncio.create_task(
                    call_service.send_direct_userbot_alert(
                        target_user_id=adm_id,
                        message_text=f"🚨 ESLATMA VAQTI KELDI: {task_text}"
                    )
                )
            except Exception as e:
                logger.warning(f"Qo'ng'iroq chiqarishda xatolik: {e}")



async def cleanup_chat_messages(conn_id: str, chat_id: int):
    """
    Egasi onlayn bo'lganda yoki chatda o'zi yozganda:
    1) Mijoz bilan bo'lgan chatdagi bot yozgan barcha avtojavoblarni o'chiradi.
    2) Botning o'zidagi eski bildirishnomalarni ham tozalaydi.
    """
    chat_key = f"{conn_id}_{chat_id}"
    deleted_client_count = 0
    deleted_admin_count = 0

    # 1. Mijoz chatidagi bot avtojavoblarini o'chirish
    bot_msgs = bot_data.get("chat_bot_messages", {}).get(chat_key, [])
    if bot_msgs:
        for mid in bot_msgs:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=mid)
                deleted_client_count += 1
            except Exception as e:
                logger.debug(f"Mijoz chatidagi xabarni o'chirish: {e}")
        bot_data["chat_bot_messages"][chat_key] = []

    # 2. Admin (bot) chatidagi bildirishnomalarni o'chirish
    admin_notifs = bot_data.get("admin_notifications", {}).get(chat_key, [])
    if admin_notifs:
        for adm_id, mid in admin_notifs:
            try:
                await bot.delete_message(chat_id=adm_id, message_id=mid)
                deleted_admin_count += 1
            except Exception as e:
                logger.debug(f"Admin chatidagi bildirishnomani o'chirish: {e}")
        bot_data["admin_notifications"][chat_key] = []

    save_data(bot_data)
    if deleted_client_count > 0 or deleted_admin_count > 0:
        logger.info(
            f"🧹 Tozalash bajarildi! Mijoz chatidan: {deleted_client_count} ta, "
            f"Bot chatidan: {deleted_admin_count} ta avtojavob o'chirildi."
        )


async def notify_admins(sender, user_msg: str, bot_reply: str, conn_id: str, client_chat_id: int):
    """Hisob egasiga mijoz haqida hisobot berish."""
    targets = get_all_target_admins()
    if not targets:
        return

    username_str = f"@{sender.username}" if sender.username else "Mavjud emas"
    if sender.username:
        user_url = f"https://t.me/{sender.username}"
        profile_html = f'<a href="{user_url}">@{sender.username}</a> ({html.escape(sender.full_name)})'
    else:
        user_url = None
        profile_html = f'<a href="tg://user?id={sender.id}">{html.escape(sender.full_name)}</a>'

    now_str = datetime.now().strftime("%H:%M:%S")

    notify_text = (
        "🔔 <b>DIQQAT! YANGI MUROJAAT KELDI!</b>\n\n"
        f"👤 <b>Foydalanuvchi:</b> {profile_html}\n"
        f"🆔 <b>ID:</b> <code>{sender.id}</code>\n\n"
        f"💬 <b>U shunday demoqda:</b>\n"
        f"<blockquote>{html.escape(user_msg)}</blockquote>\n\n"
        f"🤖 <b>AI bergan dastlabki javob:</b>\n"
        f"<blockquote>{html.escape(bot_reply)}</blockquote>\n\n"
        "👉 <i>Siz ushbu xabarga 'Reply' qilib yozsangiz yoki quyidagi tugmani bossangiz, "
        "javobingiz mijozga yetkaziladi. Chatga kirsangiz, bot xabarlari avtomatik tozalanadi!</i>"
    )

    buttons = [
        [InlineKeyboardButton(text="✍️ Bot orqali javob yozish", callback_data=f"rep_{sender.id}")],
        [InlineKeyboardButton(text="🧹 Ushbu suhbatni tozalash", callback_data=f"clean_{conn_id}_{client_chat_id}")]
    ]
    if user_url:
        buttons.append([InlineKeyboardButton(text="💬 Mijoz profilini ochish", url=user_url)])

    reply_markup = InlineKeyboardMarkup(inline_keyboard=buttons)

    chat_key = f"{conn_id}_{client_chat_id}"
    admin_notif_list = bot_data.setdefault("admin_notifications", {}).setdefault(chat_key, [])

    for admin_id in targets:
        try:
            sent_msg = await bot.send_message(
                chat_id=admin_id,
                text=notify_text,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
            notification_map[sent_msg.message_id] = {
                "conn_id": conn_id,
                "client_chat_id": client_chat_id,
                "client_id": sender.id,
                "client_name": sender.full_name,
            }
            admin_notif_list.append([admin_id, sent_msg.message_id])
            save_data(bot_data)
        except Exception as e:
            logger.error(f"Adminga xabarnoma yuborishda xatolik: {e}")


# ==========================================
# 1. TELEGRAM BUSINESS HANDLERS
# ==========================================

@dp.business_connection()
async def on_business_connection(connection: BusinessConnection):
    user = connection.user
    conn_id = connection.id
    conns = bot_data.setdefault("connections", {})

    if connection.is_enabled:
        conns[conn_id] = {
            "owner_id": user.id,
            "owner_chat_id": connection.user_chat_id,
            "owner_name": user.full_name,
            "owner_username": user.username,
        }
        if not bot_data.get("owner_name") or bot_data.get("owner_name") in ["Akkaunt egasi", "", None]:
            bot_data["owner_name"] = "Zayniddin"
            ai_service.set_owner_name("Zayniddin")

        admins = bot_data.setdefault("admins", [])
        if user.id not in admins:
            admins.append(user.id)

        save_data(bot_data)
        logger.info(f"✅ Yangi biznes ulanish! {user.full_name} (ID: {user.id})")
    else:
        conns.pop(conn_id, None)
        save_data(bot_data)
        logger.info(f"❌ Biznes ulanish o'chirildi! Foydalanuvchi: {user.full_name}")


@dp.business_message(F.text)
async def on_business_message(message: Message):
    conn_id = message.business_connection_id
    sender = message.from_user
    chat_id = message.chat.id

    conns = bot_data.get("connections", {})
    conn_info = conns.get(conn_id, {})
    owner_id = conn_info.get("owner_id")

    # ========================================================
    # 🎯 AGAR XABARNI HISOB EGASI (SIZ) YOZSANGLIZ:
    # Egasi onlayn va chatga kirdi! Bot avtojavoblarni tozalaydi!
    # ========================================================
    if (owner_id and sender.id == owner_id) or (OWNER_ID and str(sender.id) == str(OWNER_ID)):
        logger.info(f"Akkaunt egasi ({sender.full_name}) yozdi. Avvalgi bot xabarlari tozalanadi...")
        await cleanup_chat_messages(conn_id, chat_id)
        return

    # Botlarga javob bermaslik
    if sender.is_bot:
        return

    logger.info(f"📩 Biznes xabar: '{message.text}' | Yuboruvchi: {sender.full_name} | Chat: {chat_id}")

    # ========================================================
    # 🎯 AGAR EGASI HOZIR "ONLINE" HOLATDA BO'LSA:
    # Bot mijozga avtojavob yozmaydi, faqat egasiga xabar yetkazadi!
    # ========================================================
    is_owner_online = (bot_data.get("owner_status") == "online")
    if is_owner_online:
        logger.info(f"Hisob egasi ONLAYN holatda. Avtojavob yuborilmadi, faqat hisobot beriladi.")
        # Egasiga shunchaki bildirishnoma tashlaymiz
        username_str = f"@{sender.username}" if sender.username else f"ID: {sender.id}"
        notify_msg = (
            f"🟢 <b>Yangi xabar keldi!</b> (Siz Onlaynsiz)\n\n"
            f"👤 <b>Mijoz:</b> {html.escape(sender.full_name)} ({username_str})\n"
            f"💬 <b>Xabar:</b> <blockquote>{html.escape(message.text)}</blockquote>\n\n"
            f"<i>Siz onlayn bo'lganingiz sababli bot avtojavob bermadi.</i>"
        )
        for adm in get_all_target_admins():
            try:
                await bot.send_message(chat_id=adm, text=notify_msg, parse_mode="HTML")
            except Exception:
                pass
        return

    # ========================================================
    # 🎯 AVTOJAVOB O'CHIRILGAN: Bot mijozga xabar yozmaydi!
    # Faqat agar xabarda uchrashuv/vaqt bo'lsa, eslatma jadvaliga taklif qiladi
    # ========================================================
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        sched_info = await ai_service.detect_schedule_in_chat(
            user_msg=message.text,
            bot_reply="",
            current_time_str=now_str
        )
        if sched_info.get("has_schedule") and sched_info.get("datetime_iso"):
            task_title = sched_info.get("task") or f"{sender.full_name} bilan uchrashuv/kelishuv"
            iso_time = sched_info.get("datetime_iso")
            summary_note = sched_info.get("summary", "")

            # Yangi eslatma yaratamiz
            new_rem = reminder_manager.add_reminder(
                task=task_title,
                rem_datetime_iso=iso_time,
                source="ai_detected",
                client_name=sender.full_name,
                target_chat_id=chat_id
            )

            # Chiroyli ko'rsatish
            display_time = iso_time
            try:
                dt_obj = datetime.fromisoformat(iso_time)
                display_time = dt_obj.strftime("%H:%M (%d-%m-%Y)")
            except Exception:
                pass

            sched_msg = (
                "⏰ <b>AI SUHBATDAN MUHIM KELISHUV/UCHRASHUVNI ANIQLADI!</b>\n\n"
                f"👤 <b>Mijoz:</b> {html.escape(sender.full_name)}\n"
                f"📅 <b>Belgilangan vaqt:</b> <b>{display_time}</b>\n"
                f"📝 <b>Mavzu:</b> <blockquote>{html.escape(task_title)}</blockquote>\n"
                f"💬 <b>Tafsilot:</b> <i>{html.escape(summary_note)}</i>\n\n"
                "🔔 <b>Ushbu vaqtda bot sizga avtomatik qo'ng'iroq qiladi va eslatadi!</b>"
            )
            markup_ai_rem = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="✅ Jadvalda qoldirish", callback_data=f"rem_confirm_{new_rem['id']}")],
                    [InlineKeyboardButton(text="❌ Kerak emas (Bekor qilish)", callback_data=f"rem_cancel_{new_rem['id']}")]
                ]
            )
            for adm_id in get_all_target_admins():
                try:
                    await bot.send_message(
                        chat_id=adm_id,
                        text=sched_msg,
                        parse_mode="HTML",
                        reply_markup=markup_ai_rem
                    )
                except Exception as e:
                    logger.debug(f"AI eslatma xabarini adminga yuborishda xatolik: {e}")
    except Exception as e:
        logger.debug(f"Schedule detection error: {e}")


@dp.deleted_business_messages()
async def on_deleted_business_messages(event: BusinessMessagesDeleted):
    logger.info(f"Biznes xabarlar o'chirildi: {event.message_ids}")


# ==========================================
# 2. SOZLAMALAR VA ONLAYN/OFLAYN REJIM
# ==========================================

def get_settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Yangi eslatma", callback_data="add_reminder_btn"),
                InlineKeyboardButton(text="📋 Eslatmalarim", callback_data="show_reminders")
            ],
            [
                InlineKeyboardButton(text="📞 Sinov qo'ng'irog'i (Test Call)", callback_data="test_call_btn")
            ],
            [
                InlineKeyboardButton(text="⚙️ Userbot sozlamalari", callback_data="userbot_settings_btn"),
                InlineKeyboardButton(text="📊 Bot holati", callback_data="check_status")
            ]
        ]
    )


@dp.callback_query(F.data.in_(["set_online", "set_offline"]))
async def cb_toggle_status(call: CallbackQuery):
    new_status = "online" if call.data == "set_online" else "offline"
    bot_data["owner_status"] = new_status
    save_data(bot_data)

    if new_status == "online":
        text = (
            "🟢 <b>Siz ONLAYN rejimiga o'tdingiz!</b>\n\n"
            "• Endi yangi kelgan xabarlarga bot avtojavob bermaydi (o'zingiz javob berishingiz mumkin).\n"
            "• Oflayn paytidagi barcha eski bot xabarlari tozalanadi!"
        )
        # Barcha mavjud avtojavoblarni tozalab tashlaymiz
        for chat_key in list(bot_data.get("chat_bot_messages", {}).keys()):
            try:
                parts = chat_key.split("_", 1)
                if len(parts) == 2:
                    await cleanup_chat_messages(parts[0], int(parts[1]))
            except Exception:
                pass
    else:
        text = (
            "🔴 <b>Siz OFLAYN rejimiga o'tdingiz!</b>\n\n"
            "• Endi siz yo'qligingizda bot odamlarga sizning nomingizdan samimiy javob berib turadi.\n"
            "• Qachonki chatga kirsangiz, bot o'zi yozgan barcha xabarlarni avtomatik o'chirib beradi!"
        )

    await call.message.edit_text(text, parse_mode="HTML", reply_markup=get_settings_keyboard())
    await call.answer()


@dp.callback_query(F.data == "clean_all_now")
async def cb_clean_all(call: CallbackQuery):
    count = 0
    for chat_key in list(bot_data.get("chat_bot_messages", {}).keys()):
        try:
            parts = chat_key.split("_", 1)
            if len(parts) == 2:
                await cleanup_chat_messages(parts[0], int(parts[1]))
                count += 1
        except Exception:
            pass
    await call.answer(f"Barcha chatlardagi bot avtojavoblari tozalandi!", show_alert=True)


@dp.callback_query(F.data.startswith("clean_"))
async def cb_clean_single_chat(call: CallbackQuery):
    data_str = call.data.replace("clean_", "")
    parts = data_str.split("_", 1)
    if len(parts) == 2:
        await cleanup_chat_messages(parts[0], int(parts[1]))
        await call.answer("Ushbu suhbatdagi bot xabarlari tozalandi!", show_alert=True)
    else:
        await call.answer("Xatolik yuz berdi.", show_alert=True)


@dp.callback_query(F.data == "change_owner_name")
async def cb_change_owner_name(call: CallbackQuery, state: FSMContext):
    await state.set_state(FormStates.waiting_for_owner_name)
    await call.message.reply(
        "✍️ <b>O'z ismingizni yoki brend nomingizni yozib yuboring:</b>\n\n"
        "<i>(Masalan: Sardor, Asadbek, Maklersiz Kvartira va h.k.)</i>",
        parse_mode="HTML"
    )
    await call.answer()


@dp.message(FormStates.waiting_for_owner_name, F.text)
async def process_new_owner_name(message: Message, state: FSMContext):
    new_name = message.text.strip()
    if not new_name:
        await message.reply("Iltimos, haqiqiy ism kiriting.")
        return

    bot_data["owner_name"] = new_name
    save_data(bot_data)
    ai_service.set_owner_name(new_name)
    await state.clear()

    await message.reply(
        f"✅ <b>Ega ismi saqlandi: «{html.escape(new_name)}»!</b>",
        parse_mode="HTML",
        reply_markup=get_settings_keyboard()
    )


@dp.message(Command("setname"))
async def cmd_setname(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("ℹ️ <b>Foydalanish:</b> <code>/setname Sizning_Ismingiz</code>", parse_mode="HTML")
        return

    new_name = args[1].strip()
    bot_data["owner_name"] = new_name
    save_data(bot_data)
    ai_service.set_owner_name(new_name)
    await message.reply(f"✅ <b>Ega ismi o'rnatildi: «{html.escape(new_name)}»!</b>", parse_mode="HTML")


@dp.message(Command("settings"))
async def cmd_settings(message: Message):
    current_name = ai_service.owner_name
    status = bot_data.get("owner_status", "offline")
    status_badge = "🟢 ONLAYN" if status == "online" else "🔴 OFLAYN (Avtojavob faol)"

    text = (
        "⚙️ <b>SOZLAMALAR VA BOSHQARUV PANELI</b>\n\n"
        f"👑 <b>Ega Ismi:</b> <code>{html.escape(current_name)}</code>\n"
        f"⚡ <b>Hozirgi Holat:</b> <b>{status_badge}</b>\n"
        f"🤖 <b>AI Modeli:</b> <code>{ai_service.model}</code>\n"
        f"🔗 <b>Telegram Business:</b> Faol\n\n"
        "<i>Quyidagi tugmalar orqali holatingizni o'zgartirishingiz mumkin:</i>"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=get_settings_keyboard())


@dp.callback_query(F.data == "check_status")
async def cb_check_status(call: CallbackQuery):
    me = await bot.get_me()
    active_count = len(bot_data.get("connections", {}))
    status = bot_data.get("owner_status", "offline")
    status_badge = "🟢 ONLAYN" if status == "online" else "🔴 OFLAYN"

    status_text = (
        f"📊 <b>Bot Holati:</b>\n\n"
        f"🤖 Bot: @{me.username} ({me.first_name})\n"
        f"👑 Ega Ismi: <b>{html.escape(ai_service.owner_name)}</b>\n"
        f"⚡ Holat: <b>{status_badge}</b>\n"
        f"🔗 Telegram Business ulanishlar: <b>{active_count} ta</b>\n"
        f"🟢 Server: <b>Online</b>"
    )
    await call.message.reply(status_text, parse_mode="HTML")
    await call.answer()


# ==========================================
# 2.1. ESLATMALAR VA QO'NG'IROQLAR BOSHQARUVI
# ==========================================

@dp.callback_query(F.data == "show_reminders")
@dp.message(Command("reminders"))
async def cb_show_reminders(event: CallbackQuery | Message):
    is_call = isinstance(event, CallbackQuery)
    rems = reminder_manager.get_active_reminders()

    if not rems:
        empty_text = (
            "📋 <b>Hozircha faol eslatmalar yo'q!</b>\n\n"
            "Yangi eslatma yaratish uchun «➕ Yangi eslatma» tugmasini bosing yoki <code>/eslatma</code> buyrug'idan foydalaning."
        )
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="➕ Yangi eslatma qo'shish", callback_data="add_reminder_btn")],
                [InlineKeyboardButton(text="🔙 Bosh menyu", callback_data="settings_back")]
            ]
        )
        if is_call:
            await event.message.reply(empty_text, parse_mode="HTML", reply_markup=markup)
            await event.answer()
        else:
            await event.reply(empty_text, parse_mode="HTML", reply_markup=markup)
        return

    text = "📋 <b>SIZNING FAOL ESLATMALARINGIZ:</b>\n\n"
    keyboard_buttons = []
    for r in rems:
        dt_str = r.get("datetime_iso", "")
        try:
            dt_obj = datetime.fromisoformat(dt_str)
            dt_display = dt_obj.strftime("%H:%M (%d-%m-%Y)")
        except Exception:
            dt_display = dt_str
        src = "👤 O'zingiz" if r.get("source") == "manual" else f"🤖 AI ({r.get('client_name')})"
        task_preview = (r.get("task", "")[:28] + "...") if len(r.get("task", "")) > 28 else r.get("task", "")
        text += f"⏰ <b>{dt_display}</b> — {html.escape(r.get('task', ''))}\n<i>(Manba: {src})</i>\n\n"
        keyboard_buttons.append([
            InlineKeyboardButton(text=f"❌ O'chirish: {task_preview}", callback_data=f"rem_cancel_{r['id']}")
        ])

    keyboard_buttons.append([
        InlineKeyboardButton(text="➕ Yangi eslatma", callback_data="add_reminder_btn"),
        InlineKeyboardButton(text="🔙 Bosh menyu", callback_data="settings_back")
    ])

    if is_call:
        await event.message.reply(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons))
        await event.answer()
    else:
        await event.reply(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons))


@dp.callback_query(F.data == "add_reminder_btn")
async def cb_add_reminder_prompt(call: CallbackQuery, state: FSMContext):
    await state.set_state(FormStates.waiting_for_reminder_text)
    await call.message.reply(
        "⏰ <b>Qachon va nima haqida qo'ng'iroq qilishimni yozing:</b>\n\n"
        "<i>Masalan:</i>\n"
        "• «Ertaga soat 15:30 da Ali aka bilan uchrashuv»\n"
        "• «10 minutdan keyin dori ichish»\n"
        "• «Bugun 19:00 da hisobotni yuborish»\n\n"
        "✍️ Shunchaki odamdek tabiiy tilda yozib yuboring, AI o'zi vaqtni tushunib oladi!",
        parse_mode="HTML"
    )
    await call.answer()


@dp.message(Command("eslatma"))
async def cmd_eslatma(message: Message, state: FSMContext):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await state.set_state(FormStates.waiting_for_reminder_text)
        await message.reply(
            "⏰ <b>Qachon va nima haqida qo'ng'iroq qilishimni yozing:</b>\n\n"
            "<i>(Masalan: «Ertaga 14:00 da uchrashuv» yoki «20 daqiqadan keyin qo'ng'iroq qilish»)</i>",
            parse_mode="HTML"
        )
        return

    await process_reminder_text_common(message, args[1].strip(), state)


@dp.message(FormStates.waiting_for_reminder_text, F.text)
async def process_reminder_input_state(message: Message, state: FSMContext):
    await process_reminder_text_common(message, message.text.strip(), state)


async def process_reminder_text_common(message: Message, text: str, state: FSMContext):
    await state.clear()
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    parsed = await ai_service.parse_natural_reminder(text, now_str)

    if not parsed.get("success") or not parsed.get("datetime_iso"):
        await message.reply(
            "⚠️ <b>Vaqtni aniqlab bo'lmadi!</b>\n\n"
            "Iltimos, aniqroq yozing. Masalan: «Ertaga 16:00 da shartnoma imzolash» yoki «15 daqiqadan so'ng».",
            parse_mode="HTML"
        )
        return

    task_name = parsed.get("task") or text
    iso_time = parsed.get("datetime_iso")

    rem = reminder_manager.add_reminder(
        task=task_name,
        rem_datetime_iso=iso_time,
        source="manual",
        target_chat_id=message.chat.id
    )

    try:
        dt_obj = datetime.fromisoformat(iso_time)
        display_time = dt_obj.strftime("%H:%M (%d-%m-%Y)")
    except Exception:
        display_time = iso_time

    userbot_ready = await call_service.is_authorized()
    userbot_status = "🟢 Ulangan (Telegramdan qo'ng'iroq qilinadi)" if userbot_ready else "⚠️ Ulanmagan (/userbot orqali ulashingiz mumkin)"

    confirm_text = (
        "✅ <b>YANGI ESLATMA VA QO'NG'IROQ SAQLANDI!</b>\n\n"
        f"📝 <b>Vazifa:</b> <blockquote>{html.escape(task_name)}</blockquote>\n"
        f"⏰ <b>Vaqti:</b> <b>{display_time}</b>\n"
        f"📞 <b>Qo'ng'iroq tizimi:</b> {userbot_status}\n\n"
        "<i>Belgilangan daqiqada bot sizga avtomatik qo'ng'iroq qiladi va eslatadi!</i>"
    )
    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Ushbu eslatmani o'chirish", callback_data=f"rem_cancel_{rem['id']}")],
            [InlineKeyboardButton(text="📋 Barcha eslatmalarim", callback_data="show_reminders")]
        ]
    )
    await message.reply(confirm_text, parse_mode="HTML", reply_markup=markup)


@dp.callback_query(F.data.startswith("rem_done_"))
async def cb_rem_done(call: CallbackQuery):
    rem_id = call.data.replace("rem_done_", "")
    reminder_manager.mark_done(rem_id)
    await call.message.edit_text("✅ <b>Eslatma bajarildi deb belgilandi!</b> Rahmat.", parse_mode="HTML")
    await call.answer("Qabul qilindi!")


@dp.callback_query(F.data.startswith("rem_cancel_"))
async def cb_rem_cancel(call: CallbackQuery):
    rem_id = call.data.replace("rem_cancel_", "")
    reminder_manager.cancel_reminder(rem_id)
    await call.message.edit_text("❌ <b>Eslatma bekor qilindi va o'chirildi!</b>", parse_mode="HTML")
    await call.answer("Bekor qilindi!")


@dp.callback_query(F.data.startswith("rem_confirm_"))
async def cb_rem_confirm(call: CallbackQuery):
    rem_id = call.data.replace("rem_confirm_", "")
    rem = reminder_manager.get_reminder(rem_id)
    if rem:
        await call.message.edit_text(
            f"✅ <b>Eslatma jadvalda tasdiqlandi!</b>\n\n"
            f"📝 <b>Vazifa:</b> {html.escape(rem.get('task', ''))}\n"
            f"⏰ Belgilangan vaqtda bot sizga telefon qiladi.",
            parse_mode="HTML"
        )
    await call.answer("Tasdiqlandi!")


@dp.callback_query(F.data.startswith("rem_snooze_"))
async def cb_rem_snooze(call: CallbackQuery):
    data_str = call.data.replace("rem_snooze_", "")
    parts = data_str.rsplit("_", 1)
    if len(parts) == 2 and parts[1].isdigit():
        rem_id = parts[0]
        mins = int(parts[1])
    else:
        rem_id = data_str
        mins = 10

    res = reminder_manager.snooze(rem_id, minutes=mins)
    if res:
        await call.message.edit_text(f"⏰ <b>Eslatma {mins} daqiqaga kechiktirildi!</b> Qayta qo'ng'iroq qilinadi.", parse_mode="HTML")
    await call.answer("Kechiktirildi!")


# ==========================================
# 2.2. TELEGRAM USERBOT VA QO'NG'IROQ SOZLAMALARI
# ==========================================

@dp.callback_query(F.data == "test_call_btn")
@dp.message(Command("testcall"))
async def trigger_test_call(event: CallbackQuery | Message):
    user_id = event.from_user.id
    is_call = isinstance(event, CallbackQuery)

    if not await call_service.is_authorized():
        text = (
            "⚠️ <b>Userbot hali ulanmagan!</b>\n\n"
            "Telegram orqali to'g'ridan-to'g'ri ovozli qo'ng'iroq qilish uchun Userbot sozlanishi kerak.\n"
            "Quyidagi «📱 Userbotni sozlash» tugmasini bosing yoki <code>/userbot</code> buyrug'ini yuboring."
        )
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📱 Userbotni sozlash", callback_data="userbot_settings_btn")],
                [InlineKeyboardButton(text="🔙 Bosh menyu", callback_data="settings_back")]
            ]
        )
        if is_call:
            await event.message.reply(text, parse_mode="HTML", reply_markup=markup)
            await event.answer()
        else:
            await event.reply(text, parse_mode="HTML", reply_markup=markup)
        return

    notice = "📞 <b>Sinov qo'ng'irog'i boshlandi!</b>\nTelegramingizga qarang, hozir qo'ng'iroq jiringlaydi..."
    if is_call:
        await event.message.reply(notice, parse_mode="HTML")
        await event.answer("Qo'ng'iroq yo'llanmoqda...")
    else:
        await event.reply(notice, parse_mode="HTML")

    asyncio.create_task(call_service.make_call(target_user_id=user_id, duration_seconds=20))


@dp.callback_query(F.data == "userbot_settings_btn")
@dp.message(Command("userbot"))
async def cb_userbot_settings(event: CallbackQuery | Message):
    is_call = isinstance(event, CallbackQuery)
    is_auth = await call_service.is_authorized()

    if is_auth:
        me = await call_service.get_me()
        user_str = f"@{me.username}" if me and me.username else (me.first_name if me else "Faol")
        phone_str = f"({me.phone})" if me and me.phone else ""
        text = (
            "⚙️ <b>TELEGRAM USERBOT SOZLAMALARI</b>\n\n"
            f"🟢 <b>Holat:</b> Faol va ulangan!\n"
            f"👤 <b>Userbot profili:</b> {html.escape(user_str)} {phone_str}\n\n"
            "📞 Bot muhim eslatmalar vaqtida ushbu profil orqali sizga avtomatik ovozli qo'ng'iroq qiladi."
        )
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📞 Sinov qo'ng'irog'i qilish", callback_data="test_call_btn")],
                [InlineKeyboardButton(text="🔄 Akkauntni uzish (Boshqa raqam ulash)", callback_data="logout_userbot_btn")],
                [InlineKeyboardButton(text="🔙 Bosh menyu", callback_data="settings_back")]
            ]
        )
    else:
        text = (
            "⚙️ <b>TELEGRAM USERBOT SOZLAMALARI</b>\n\n"
            "🔴 <b>Holat:</b> Ulanmagan\n\n"
            "Telegram botlari rasman to'g'ridan-to'g'ri qo'ng'iroq qila olmagani sababli, "
            "bot sizga avtomatik telefon qilishi uchun ikkinchi Telegram profilingiz (yoki o'z profilingiz) "
            "yordamchi sifatida ulanadi.\n\n"
            "Buning uchun sizga Telegramdan keladigan 5 xonali tasdiqlash kodi kerak bo'ladi."
        )
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📱 Profilni ulash (Telefon kiritish)", callback_data="start_userbot_login")],
                [InlineKeyboardButton(text="🔙 Bosh menyu", callback_data="settings_back")]
            ]
        )

    if is_call:
        await event.message.reply(text, parse_mode="HTML", reply_markup=markup)
        await event.answer()
    else:
        await event.reply(text, parse_mode="HTML", reply_markup=markup)


@dp.callback_query(F.data == "logout_userbot_btn")
async def cb_userbot_logout(call: CallbackQuery, state: FSMContext):
    await call_service.logout()
    await state.clear()
    await call.message.reply(
        "🗑 <b>Eski akkaunt muvaffaqiyatli uzildi!</b>\n\n"
        "Endi yangi (ikkinchi) raqamingizni kiritish uchun quyidagi tugmani bosing yoki to'g'ridan-to'g'ri yangi raqamingizni yozib yuboring:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📱 Yangi raqamni ulash", callback_data="start_userbot_login")],
                [InlineKeyboardButton(text="🔙 Bosh menyu", callback_data="settings_back")]
            ]
        )
    )
    await call.answer("Akkaunt uzildi!")



@dp.callback_query(F.data == "start_userbot_login")
async def cb_start_userbot_login(call: CallbackQuery, state: FSMContext):
    await state.set_state(FormStates.waiting_for_userbot_phone)
    await call.message.reply(
        "📱 <b>Qo'ng'iroq qiluvchi profilning telefon raqamini kiriting:</b>\n\n"
        "<i>Xalqaro formatda kiriting, masalan:</i> <code>+998901234567</code>",
        parse_mode="HTML"
    )
    await call.answer()


@dp.message(FormStates.waiting_for_userbot_phone, F.text)
async def process_userbot_phone_step(message: Message, state: FSMContext):
    phone = message.text.strip().replace(" ", "")
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    if not call_service.is_configured():
        call_service.api_id = 2040
        call_service.api_hash = "b18441a1ff607e10a989891a5462e627"

    success, msg = await call_service.send_code_request(phone)
    if success:
        await state.set_state(FormStates.waiting_for_userbot_code)
        await message.reply(
            "📩 <b>Tasdiqlash kodi Telegram ilovangizga yuborildi!</b>\n\n"
            "Iltimos, kelgan kodni yozib yuboring (Telegram bloklamasligi uchun harflar/bo'shliq bilan yozishingiz ham mumkin, masalan: <code>1 2 3 4 5</code>):",
            parse_mode="HTML"
        )
    else:
        await state.clear()
        await message.reply(f"❌ <b>Xatolik:</b>\n{html.escape(msg)}\n\nQaytadan urinish: /userbot", parse_mode="HTML")


@dp.message(FormStates.waiting_for_userbot_code, F.text)
async def process_userbot_code_step(message: Message, state: FSMContext):
    code = message.text.strip().replace(" ", "").replace("-", "")
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    success, msg = await call_service.sign_in_with_code(code)
    if success:
        await state.clear()
        await message.reply(
            f"🎉 <b>MUVAFFAQINLI ULANDI!</b>\n\n{html.escape(msg)}\n\n"
            "Endi bot sizga belgilangan vaqtda bemalol avtomatik telefon qila oladi!",
            parse_mode="HTML",
            reply_markup=get_settings_keyboard()
        )
    elif msg == "2FA_PASSWORD_REQUIRED":
        await state.set_state(FormStates.waiting_for_userbot_password)
        await message.reply(
            "🔐 <b>Ushbu akkauntda Ikki bosqichli tasdiqlash (2FA Cloud Password) yoqilgan!</b>\n\n"
            "Iltimos, 2FA parolingizni kiriting:",
            parse_mode="HTML"
        )
    else:
        await state.clear()
        await message.reply(f"❌ Kod noto'g'ri yoki xatolik: {html.escape(msg)}\nQayta urinish: /userbot", parse_mode="HTML")


@dp.message(FormStates.waiting_for_userbot_password, F.text)
async def process_userbot_password_step(message: Message, state: FSMContext):
    pwd = message.text.strip()
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    success, msg = await call_service.sign_in_with_password(password=pwd)
    await state.clear()
    if success:
        await message.reply(
            f"🎉 <b>MUVAFFAQINLI ULANDI!</b>\n\n{html.escape(msg)}\n\n"
            "Endi bot sizga belgilangan vaqtda bemalol avtomatik telefon qila oladi!",
            parse_mode="HTML",
            reply_markup=get_settings_keyboard()
        )
    else:
        await message.reply(
            f"❌ <b>2FA Parol noto'g'ri:</b>\n{html.escape(msg)}\n\nQaytadan urinish uchun: /userbot",
            parse_mode="HTML"
        )



@dp.callback_query(F.data == "settings_back")
async def cb_settings_back(call: CallbackQuery):
    await call.message.edit_text(
        "⚙️ <b>SOZLAMALAR VA BOSHQARUV PANELI</b>",
        parse_mode="HTML",
        reply_markup=get_settings_keyboard()
    )
    await call.answer()


# ==========================================
# 3. MIJOZGA JAVOB YOZISH (IKKI TOMONLAMA CHAT)
# ==========================================

@dp.callback_query(F.data.startswith("rep_"))
async def cb_start_reply(call: CallbackQuery, state: FSMContext):
    msg_id = call.message.message_id
    info = notification_map.get(msg_id)

    if not info:
        await call.answer("Ushbu murojaat ma'lumotlari yangilangan, bevosita profilga yozing.", show_alert=True)
        return

    await state.set_state(FormStates.waiting_for_reply)
    await state.update_data(
        conn_id=info["conn_id"],
        client_chat_id=info["client_chat_id"],
        client_name=info["client_name"]
    )

    await call.message.reply(
        f"✍️ <b>{html.escape(info['client_name'])}</b> ga javob yozing:\n"
        "<i>(Xabar yuborishingiz bilan u mijozga boradi va avtojavoblar tozalanadi)</i>",
        parse_mode="HTML"
    )
    await call.answer()


@dp.message(FormStates.waiting_for_reply, F.text)
async def process_admin_reply_state(message: Message, state: FSMContext):
    data = await state.get_data()
    conn_id = data.get("conn_id")
    client_chat_id = data.get("client_chat_id")
    client_name = data.get("client_name", "Mijoz")

    try:
        await bot.send_message(
            chat_id=client_chat_id,
            text=message.text,
            business_connection_id=conn_id
        )
        await message.reply(
            f"✅ <b>Javobingiz {html.escape(client_name)} ga yetkazildi!</b>\n\n"
            f"<i>Yuborilgan:</i> «{html.escape(message.text)}»",
            parse_mode="HTML"
        )
        # Javob yozilgach, avvalgi vaqtinchalik avtojavoblar tozalanadi
        await cleanup_chat_messages(conn_id, client_chat_id)
    except Exception as e:
        await message.reply(f"❌ Xabar yuborishda xatolik yuz berdi: {e}")

    await state.clear()


@dp.message(F.reply_to_message, F.text)
async def process_admin_direct_reply(message: Message):
    """Admin bildirishnoma xabariga 'Reply' qilib yozganida."""
    replied_msg_id = message.reply_to_message.message_id
    info = notification_map.get(replied_msg_id)

    if not info:
        return

    conn_id = info["conn_id"]
    client_chat_id = info["client_chat_id"]
    client_name = info["client_name"]

    try:
        await bot.send_message(
            chat_id=client_chat_id,
            text=message.text,
            business_connection_id=conn_id
        )
        await message.reply(
            f"✅ <b>Javobingiz {html.escape(client_name)} ga yetkazildi!</b>",
            parse_mode="HTML"
        )
        # Avtojavoblarni tozalash
        await cleanup_chat_messages(conn_id, client_chat_id)
    except Exception as e:
        await message.reply(f"❌ Xabarni yetkazishda xatolik: {e}")


# ==========================================
# 4. START VA ODDIY BUYRUQLAR
# ==========================================

@dp.message(CommandStart())
async def cmd_start(message: Message):
    user = message.from_user
    admins = bot_data.setdefault("admins", [])
    if user.id not in admins:
        admins.append(user.id)
    save_data(bot_data)

    userbot_ready = await call_service.is_authorized()
    call_status_badge = "🟢 Faol (Uzluksiz qo'ng'iroq tayyor)" if userbot_ready else "⚠️ Ulanmagan (/userbot orqali ulang)"

    text = (
        f"👑 <b>Assalomu alaykum, {html.escape(user.first_name)}!</b>\n\n"
        "Men sizning <b>Aqlli Eslatma va Avtomatik Qo'ng'iroq</b> xizmatingizman.\n\n"
        "⏰ <b>Qanday ishlayman?</b>\n"
        "Menga istalgan muhim ishingizni yozib yuboring (masalan: <i>«Ertaga 15:30 da Ali bilan uchrashuv»</i> yoki <i>«10 minutdan keyin dori ichish»</i>).\n\n"
        "📞 Belgilangan daqiqada <b>mening o'zim sizga Telegram orqali telefon qilaman</b> va eslataman!\n\n"
        f"📞 <b>Qo'ng'iroq tizimi:</b> {call_status_badge}\n\n"
        "<i>Quyidagi tugmalar orqali boshqarishingiz mumkin:</i>"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=get_settings_keyboard())


@dp.message(Command("status"))
async def cmd_status(message: Message):
    me = await bot.get_me()
    active_rems = len(reminder_manager.get_active_reminders())
    userbot_ready = await call_service.is_authorized()
    call_badge = "🟢 Faol va ulangan" if userbot_ready else "🔴 Ulanmagan (/userbot)"

    status_text = (
        f"📊 <b>Bot Holati:</b>\n\n"
        f"🤖 Bot: @{me.username} ({me.first_name})\n"
        f"⏰ Faol eslatmalar: <b>{active_rems} ta</b>\n"
        f"📞 Qo'ng'iroq tizimi (Userbot): <b>{call_badge}</b>\n"
        f"🟢 Server: <b>Online</b>"
    )
    await message.answer(status_text, parse_mode="HTML")


@dp.message(F.text)
async def on_direct_message(message: Message, state: FSMContext):
    """
    Foydalanuvchi botga xabar yozganda:
    1. Agar telefon raqam bo'lsa -> Userbot ulanishini boshlaydi.
    2. Aks holda -> AI uni eslatma deb qabul qiladi.
    """
    text = message.text.strip()
    cleaned_phone = text.replace(" ", "").replace("-", "")

    # Telefon raqam ekanligini tekshirish (masalan: +998901234567 yoki 998901234567)
    if (cleaned_phone.startswith("+") or cleaned_phone.isdigit()) and 9 <= len(cleaned_phone.replace("+", "")) <= 15:
        if not any(w in text.lower() for w in ["soat", "da", "uchrashuv", "eslat", "bugun", "ertaga"]):
            logger.info(f"Foydalanuvchi telefon raqam kiritdi: {cleaned_phone}")
            await state.set_state(FormStates.waiting_for_userbot_phone)
            await process_userbot_phone_step(message, state)
            return

    await process_reminder_text_common(message, text, state)




# ==========================================
# ASOSIY ISHGA TUSHIRISH
# ==========================================

async def main():
    me = await bot.get_me()
    logger.info(f"Bot ishga tushdi: @{me.username} ({me.first_name}) | Ega: {ai_service.owner_name}")
    print(f"\n==========================================")
    print(f"🤖 Bot muvaffaqiyatli ishga tushdi: @{me.username}")
    print(f"👑 Ega ismi: {ai_service.owner_name}")
    print(f"⚡ Holat: {bot_data.get('owner_status', 'offline')}")
    print(f"⏰ Eslatmalar va qo'ng'iroq tizimi: FAOL")
    print(f"==========================================\n")

    # Eslatmalar va qo'ng'iroqlar tekshiruvini fonda ishga tushirish
    asyncio.create_task(reminder_manager.run_loop(on_reminder_triggered))
    # Userbot sessiyasini tekshirish/ishga tushirish
    asyncio.create_task(call_service.get_client())

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")
