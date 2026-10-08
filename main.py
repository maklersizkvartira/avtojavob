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
    return {"connections": {}, "admins": [], "owner_name": "Akkaunt egasi"}

def save_data(data: dict):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ma'lumotlar faylini saqlashda xatolik: {e}")

bot_data = load_data()
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
# YORDAMCHI FUNKSIYALAR
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


async def notify_admins(sender, user_msg: str, bot_reply: str, conn_id: str, client_chat_id: int):
    """
    Hisob egasiga (adminlarga) mijozning xabari haqida to'liq hisobot yuboradi
    va unga javob yozish imkoniyatini taqdim etadi.
    """
    targets = get_all_target_admins()
    if not targets:
        logger.warning("Ogohlantirish yuborish uchun birorta ham admin topilmadi! Iltimos, botga /start bosing.")
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
        "👉 <b>Iltimos, javob bering!</b>\n"
        "<i>Siz ushbu xabarga to'g'ridan-to'g'ri 'Reply' (Javob berish) qilib yozsangiz yoki quyidagi tugmani bossangiz, "
        "javobingiz mijozga yetkaziladi!</i>"
    )

    buttons = [
        [InlineKeyboardButton(text="✍️ Bot orqali javob yozish", callback_data=f"rep_{sender.id}")]
    ]
    if user_url:
        buttons.append([InlineKeyboardButton(text="💬 Mijoz profilini ochish", url=user_url)])

    reply_markup = InlineKeyboardMarkup(inline_keyboard=buttons)

    for admin_id in targets:
        try:
            sent_msg = await bot.send_message(
                chat_id=admin_id,
                text=notify_text,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
            # Reply qilinganda topish uchun xotirada saqlaymiz
            notification_map[sent_msg.message_id] = {
                "conn_id": conn_id,
                "client_chat_id": client_chat_id,
                "client_id": sender.id,
                "client_name": sender.full_name,
            }
            logger.info(f"Adminga ({admin_id}) xabarnoma yetkazildi. MsgID: {sent_msg.message_id}")
        except Exception as e:
            logger.error(f"Adminga ({admin_id}) xabar yuborishda xatolik: {e}")


# ==========================================
# 1. TELEGRAM BUSINESS HANDLERS
# ==========================================

@dp.business_connection()
async def on_business_connection(connection: BusinessConnection):
    """
    Foydalanuvchi botni o'zining Telegram Business hisobiga ulaganda yoki uzganda chaqiriladi.
    """
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
        # Agar ega ismi hali berilmagan bo'lsa, foydalanuvchi ismini qo'yamiz
        if bot_data.get("owner_name") in ["Akkaunt egasi", "", None]:
            bot_data["owner_name"] = user.full_name
            ai_service.set_owner_name(user.full_name)

        admins = bot_data.setdefault("admins", [])
        if user.id not in admins:
            admins.append(user.id)

        save_data(bot_data)
        logger.info(f"✅ Yangi biznes ulanish! {user.full_name} (ID: {user.id}) | ConnID: {conn_id}")

        try:
            await bot.send_message(
                chat_id=user.id,
                text=f"🎉 <b>Bot muvaffaqiyatli ulandi!</b>\n\n"
                     f"👑 Joriy Ega Ismi: <b>{html.escape(ai_service.owner_name)}</b>\n\n"
                     "Endi shaxsiy hisobingizga kimdir yozsa, AI sizning nomingizdan samimiy javob beradi va "
                     "shu yerga darhol kim yozgani haqida to'liq hisobot keladi!\n\n"
                     "Ismingizni o'zgartirish uchun: /settings buyrug'idan foydalaning.",
                parse_mode="HTML"
            )
        except Exception:
            pass
    else:
        conns.pop(conn_id, None)
        save_data(bot_data)
        logger.info(f"❌ Biznes ulanish o'chirildi! Foydalanuvchi: {user.full_name}")


@dp.business_message(F.text)
async def on_business_message(message: Message):
    """
    Telegram Business hisobiga kelgan xabarlarni qayta ishlash.
    """
    conn_id = message.business_connection_id
    sender = message.from_user
    chat_id = message.chat.id

    conns = bot_data.get("connections", {})
    conn_info = conns.get(conn_id, {})
    owner_id = conn_info.get("owner_id")

    # Agar xabarni hisob egasi (o'zingiz) yozgan bo'lsa, javob qaytarmaymiz
    if (owner_id and sender.id == owner_id) or (OWNER_ID and str(sender.id) == str(OWNER_ID)):
        logger.info(f"Akkaunt egasi ({sender.full_name}) yozdi. Avtojavob berilmadi.")
        return

    # Botlarga javob bermaslik
    if sender.is_bot:
        return

    logger.info(f"📩 Biznes xabar: '{message.text}' | Yuboruvchi: {sender.full_name} | Chat: {chat_id}")

    # Foydalanuvchiga 'yozmoqda...' (typing) statusini ko'rsatish
    try:
        await bot.send_chat_action(
            chat_id=chat_id,
            action=ChatAction.TYPING,
            business_connection_id=conn_id
        )
    except Exception as e:
        logger.warning(f"Typing action yuborishda xatolik: {e}")

    # AI orqali samimiy yordamchi javobini olish
    chat_key = f"biz_{conn_id}_{chat_id}"
    reply_text = await ai_service.get_reply(
        chat_key=chat_key,
        user_message=message.text,
        sender_name=sender.full_name
    )

    # Javobni mijozga yuborish
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=reply_text,
            business_connection_id=conn_id
        )
        logger.info(f"📤 Avtojavob yuborildi: {reply_text[:50]}...")
    except Exception as e:
        logger.error(f"Mijozga xabar yuborishda xatolik: {e}")
        return

    # 🔔 HISOB EGASIGA DARHOL XABAR QILISH!
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
# 2. SOZLAMALAR VA EGA ISMINI TAHRIRLASH
# ==========================================

def get_settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Ega ismini o'zgartirish", callback_data="change_owner_name")],
            [InlineKeyboardButton(text="📊 Holatni tekshirish", callback_data="check_status")]
        ]
    )


@dp.callback_query(F.data == "change_owner_name")
async def cb_change_owner_name(call: CallbackQuery, state: FSMContext):
    await state.set_state(FormStates.waiting_for_owner_name)
    await call.message.reply(
        "✍️ <b>O'z ismingizni yoki brend nomingizni yozib yuboring:</b>\n\n"
        "<i>(Masalan: Sardor, Asadbek, Maklersiz Kvartira va h.k.)</i>\n\n"
        "Shundan so'ng bot kimdir «Egang kim?» yoki «Seni kim yaratgan?» desa, "
        "aynan shu ismni aytib javob beradi!",
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
        f"✅ <b>Ega ismi muvaffaqiyatli saqlandi: «{html.escape(new_name)}»!</b>\n\n"
        f"Endi bot sizning shaxsiy yordamchingiz sifatida taniladi:\n"
        f"• «Egang kim?» ➡️ <i>«Meni {html.escape(new_name)} yaratgan, men {html.escape(new_name)}ning shaxsiy yordamchisiman!»</i>\n"
        f"• Hech qachon OpenAI yoki ChatGPT degan so'zlar tilga olinmaydi.",
        parse_mode="HTML",
        reply_markup=get_settings_keyboard()
    )


@dp.message(Command("setname"))
async def cmd_setname(message: Message):
    """Buyruq orqali to'g'ridan-to'g'ri ism o'rnatish: /setname Sardor"""
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply(
            "ℹ️ <b>Foydalanish:</b> <code>/setname Sizning_Ismingiz</code>\n\n"
            "Masalan: <code>/setname Asadbek</code>",
            parse_mode="HTML"
        )
        return

    new_name = args[1].strip()
    bot_data["owner_name"] = new_name
    save_data(bot_data)
    ai_service.set_owner_name(new_name)

    await message.reply(
        f"✅ <b>Ega ismi o'rnatildi: «{html.escape(new_name)}»!</b>\n\n"
        f"Bot endi faqat sizning nomingizdan («{html.escape(new_name)}ning shaxsiy yordamchisi») deb javob qaytaradi.",
        parse_mode="HTML"
    )


@dp.message(Command("settings"))
async def cmd_settings(message: Message):
    current_name = ai_service.owner_name
    text = (
        "⚙️ <b>SOZLAMALAR VA BOSHQARUV PANELI</b>\n\n"
        f"👑 <b>Joriy Ega Ismi:</b> <code>{html.escape(current_name)}</code>\n"
        f"🤖 <b>AI Modeli:</b> <code>{ai_service.model}</code>\n"
        f"🔗 <b>Telegram Business:</b> Faol\n\n"
        "O'zgartirish uchun quyidagi tugmani bosing:"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=get_settings_keyboard())


@dp.callback_query(F.data == "check_status")
async def cb_check_status(call: CallbackQuery):
    me = await bot.get_me()
    active_count = len(bot_data.get("connections", {}))
    status_text = (
        f"📊 <b>Bot Holati:</b>\n\n"
        f"🤖 Bot: @{me.username} ({me.first_name})\n"
        f"👑 Ega Ismi: <b>{html.escape(ai_service.owner_name)}</b>\n"
        f"🧠 AI Model: <code>{ai_service.model}</code>\n"
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
        f"✍️ <b>{html.escape(info['client_name'])}</b> ga yubormoqchi bo'lgan javobingizni yozing:\n\n"
        "<i>(Xabar yuborishingiz bilan u to'g'ridan-to'g'ri mijozga yetkaziladi)</i>",
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
            f"✅ <b>Javobingiz {html.escape(client_name)} ga muvaffaqiyatli yetkazildi!</b>\n\n"
            f"<i>Yuborilgan xabar:</i> «{html.escape(message.text)}»",
            parse_mode="HTML"
        )
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
        logger.info(f"Admin javobi mijozga ({client_chat_id}) yetkazildi.")
    except Exception as e:
        await message.reply(f"❌ Xabarni mijozga yetkazishda xatolik: {e}")


# ==========================================
# 4. START VA ODDIY BUYRUQLAR
# ==========================================

@dp.message(CommandStart())
async def cmd_start(message: Message):
    user = message.from_user
    admins = bot_data.setdefault("admins", [])
    if user.id not in admins:
        admins.append(user.id)

    # Agar hali ega ismi o'rnatilmagan bo'lsa, avtomatik biriktiramiz
    if bot_data.get("owner_name") in ["Akkaunt egasi", "", None]:
        bot_data["owner_name"] = user.full_name
        ai_service.set_owner_name(user.full_name)

    save_data(bot_data)
    logger.info(f"Admin ro'yxatga olindi: {user.full_name} (ID: {user.id})")

    current_name = ai_service.owner_name

    text = (
        f"👑 <b>Assalomu alaykum, {html.escape(user.first_name)}!</b>\n\n"
        f"Men sizning (<b>{html.escape(current_name)}</b>ning) <b>Aqlli Shaxsiy Yordamchingizman</b>.\n\n"
        "🌟 <b>Imkoniyatlar:</b>\n"
        "• Mijozlar profilingizga yozsa, men sizning nomingizdan muloyim javob beraman.\n"
        f"• «Egang kim?» yoki «Seni kim yaratgan?» deyishsa: <i>«Meni {html.escape(current_name)} yaratgan, men {html.escape(current_name)}ning shaxsiy yordamchisiman»</i> deb javob beraman (hech qachon OpenAI so'zi chiqmaydi).\n"
        "• Har bir murojaat bo'yicha <b>darhol shu yerga to'liq hisobot</b> keladi.\n"
        "• Siz ushbu xabarga <b>'Reply'</b> qilib yozsangiz, javobingiz to'g'ridan-to'g'ri mijozga boradi!\n\n"
        "⚙️ Ismni o'zgartirish: /settings yoki <code>/setname Ismingiz</code>"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=get_settings_keyboard())


@dp.message(Command("status"))
async def cmd_status(message: Message):
    me = await bot.get_me()
    active_count = len(bot_data.get("connections", {}))
    status_text = (
        f"📊 <b>Bot Holati:</b>\n\n"
        f"🤖 Bot: @{me.username} ({me.first_name})\n"
        f"👑 Ega Ismi: <b>{html.escape(ai_service.owner_name)}</b>\n"
        f"🧠 AI Model: <code>{ai_service.model}</code>\n"
        f"🔗 Telegram Business: <b>{active_count} ta ulanish</b>\n"
        f"🟢 Server: <b>Online</b>"
    )
    await message.answer(status_text, parse_mode="HTML")


@dp.message(Command("help"))
async def cmd_help(message: Message):
    help_text = (
        "📖 <b>Buyruqlar va Qo'llanma:</b>\n\n"
        "• /settings — Sozlamalar va Ega ismini o'zgartirish tugmasi.\n"
        "• <code>/setname Ismingiz</code> — Ismingizni 1 soniyada o'zgartirish (Masalan: <code>/setname Sardor</code>).\n"
        "• /status — Bot holati va statistika.\n\n"
        "<b>Mijozga javob berish:</b> Kelgan xabarga shunchaki 'Reply' qilib yozing."
    )
    await message.answer(help_text, parse_mode="HTML")


@dp.message(F.text)
async def on_direct_message(message: Message):
    """Botning o'ziga to'g'ridan-to'g'ri yozilgan xabarlar."""
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
    print(f"==========================================\n")
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")
