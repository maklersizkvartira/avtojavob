import asyncio
import html
import json
import logging
import os
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
        "owner_name": "Akkaunt egasi",
        "owner_status": "offline",  # "online" yoki "offline"
        "chat_bot_messages": {},    # { "conn_id_chat_id": [msg_id, ...] }
        "admin_notifications": {}   # { "conn_id_chat_id": [[admin_id, msg_id], ...] }
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

current_owner_name = bot_data.get("owner_name", "Akkaunt egasi")

# AI servisini ishga tushirish
ai_service = AIService(
    api_key=OPENAI_API_KEY,
    model=AI_MODEL,
    base_url=AI_BASE_URL if AI_BASE_URL else None,
    owner_name=current_owner_name,
    system_prompt=SYSTEM_PROMPT
)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Xotiradagi xabarlar xaritasi (notification_msg_id -> client info)
notification_map: dict[int, dict] = {}


class FormStates(StatesGroup):
    waiting_for_reply = State()
    waiting_for_owner_name = State()


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
        if bot_data.get("owner_name") in ["Akkaunt egasi", "", None]:
            bot_data["owner_name"] = user.full_name
            ai_service.set_owner_name(user.full_name)

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
    # 🎯 EGASI OFLAYN BO'LGANDA:
    # Bot samimiy avtojavob beradi va xabarni eslab qoladi!
    # ========================================================
    try:
        await bot.send_chat_action(
            chat_id=chat_id,
            action=ChatAction.TYPING,
            business_connection_id=conn_id
        )
    except Exception:
        pass

    chat_key = f"biz_{conn_id}_{chat_id}"
    reply_text = await ai_service.get_reply(
        chat_key=chat_key,
        user_message=message.text,
        sender_name=sender.full_name
    )

    try:
        sent_client_msg = await bot.send_message(
            chat_id=chat_id,
            text=reply_text,
            business_connection_id=conn_id
        )
        logger.info(f"📤 Avtojavob yuborildi: {reply_text[:50]}...")

        # O'chirish uchun bot yuborgan xabar ID sini saqlab qo'yamiz
        stored_key = f"{conn_id}_{chat_id}"
        bot_msgs = bot_data.setdefault("chat_bot_messages", {}).setdefault(stored_key, [])
        bot_msgs.append(sent_client_msg.message_id)
        save_data(bot_data)

    except Exception as e:
        logger.error(f"Mijozga xabar yuborishda xatolik: {e}")
        return

    # Hisob egasiga hisobot yetkazish
    await notify_admins(
        sender=sender,
        user_msg=message.text,
        bot_reply=reply_text,
        conn_id=conn_id,
        client_chat_id=chat_id
    )


@dp.deleted_business_messages()
async def on_deleted_business_messages(event: BusinessMessagesDeleted):
    logger.info(f"Biznes xabarlar o'chirildi: {event.message_ids}")


# ==========================================
# 2. SOZLAMALAR VA ONLAYN/OFLAYN REJIM
# ==========================================

def get_settings_keyboard() -> InlineKeyboardMarkup:
    status = bot_data.get("owner_status", "offline")
    status_text = "🟢 Holat: ONLAYN (Avtojavob to'xtatilgan)" if status == "online" else "🔴 Holat: OFLAYN (Avtojavob yoqiq)"
    toggle_data = "set_offline" if status == "online" else "set_online"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"🔄 {status_text}", callback_data=toggle_data)],
            [InlineKeyboardButton(text="✏️ Ega ismini o'zgartirish", callback_data="change_owner_name")],
            [InlineKeyboardButton(text="🧹 Barcha avtojavoblarni tozalash", callback_data="clean_all_now")],
            [InlineKeyboardButton(text="📊 Holatni tekshirish", callback_data="check_status")]
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

    if bot_data.get("owner_name") in ["Akkaunt egasi", "", None]:
        bot_data["owner_name"] = user.full_name
        ai_service.set_owner_name(user.full_name)

    save_data(bot_data)

    current_name = ai_service.owner_name
    status = bot_data.get("owner_status", "offline")
    status_badge = "🟢 ONLAYN" if status == "online" else "🔴 OFLAYN (Avtojavob faol)"

    text = (
        f"👑 <b>Assalomu alaykum, {html.escape(user.first_name)}!</b>\n\n"
        f"Men sizning (<b>{html.escape(current_name)}</b>ning) <b>Aqlli Shaxsiy Yordamchingizman</b>.\n\n"
        "⚡ <b>Avto-Tozalash va Onlayn/Oflayn Tizimi:</b>\n"
        f"• Joriy holatingiz: <b>{status_badge}</b>\n"
        "• <b>🔴 Oflayn bo'lsangiz:</b> Bot sizning nomingizdan odamlarga javob berib turadi.\n"
        "• <b>🟢 Onlayn bo'lsangiz:</b> Chatga kirib o'zingiz yozishingiz bilanoq, bot yozgan barcha avtojavoblar "
        "<b>avtomatik tarzda mijoz chatidan ham, botdan ham o'chib ketadi!</b> Chat toza bo'lib qoladi.\n\n"
        "Quyidagi tugmalar orqali boshqarishingiz mumkin:"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=get_settings_keyboard())


@dp.message(Command("status"))
async def cmd_status(message: Message):
    me = await bot.get_me()
    active_count = len(bot_data.get("connections", {}))
    status = bot_data.get("owner_status", "offline")
    status_badge = "🟢 ONLAYN" if status == "online" else "🔴 OFLAYN"

    status_text = (
        f"📊 <b>Bot Holati:</b>\n\n"
        f"🤖 Bot: @{me.username} ({me.first_name})\n"
        f"👑 Ega Ismi: <b>{html.escape(ai_service.owner_name)}</b>\n"
        f"⚡ Holat: <b>{status_badge}</b>\n"
        f"🔗 Telegram Business: <b>{active_count} ta ulanish</b>\n"
        f"🟢 Server: <b>Online</b>"
    )
    await message.answer(status_text, parse_mode="HTML")


@dp.message(F.text)
async def on_direct_message(message: Message):
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    chat_key = f"direct_{message.chat.id}"
    reply = await ai_service.get_reply(
        chat_key=chat_key,
        user_message=message.text,
        sender_name=message.from_user.full_name
    )
    await message.answer(reply)


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
    print(f"==========================================\n")

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")
