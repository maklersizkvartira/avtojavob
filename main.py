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

# AI servisini ishga tushirish
ai_service = AIService(
    api_key=OPENAI_API_KEY,
    model=AI_MODEL,
    base_url=AI_BASE_URL if AI_BASE_URL else None,
    system_prompt=SYSTEM_PROMPT
)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Ma'lumotlarni doimiy saqlash fayli
DATA_FILE = "bot_data.json"

def load_data() -> dict:
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Ma'lumotlar faylini o'qishda xatolik: {e}")
    return {"connections": {}, "admins": [], "dialog_map": {}}

def save_data(data: dict):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ma'lumotlar faylini saqlashda xatolik: {e}")

bot_data = load_data()

# Xotiradagi xabarlar xaritasi (notification_msg_id -> client info)
notification_map: dict[int, dict] = {}


class AdminReplyState(StatesGroup):
    waiting_for_reply = State()


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
        # Adminlar ro'yxatiga ham qo'shib qo'yamiz
        admins = bot_data.setdefault("admins", [])
        if user.id not in admins:
            admins.append(user.id)

        save_data(bot_data)
        logger.info(f"✅ Yangi biznes ulanish! {user.full_name} (ID: {user.id}) | ConnID: {conn_id}")

        # Egasiga tabrik xabari
        try:
            await bot.send_message(
                chat_id=user.id,
                text="🎉 <b>Bot muvaffaqiyatli ulandi!</b>\n\n"
                     "Endi shaxsiy hisobingizga kimdir yozsa, AI sizning nomingizdan samimiy javob qaytaradi va "
                     "shu yerga darhol kim yozgani haqida to'liq hisobot keladi!",
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
# 2. HISOB EGASI UCHUN BUYRUQ VA JAVOB QAYTARISH
# ==========================================

@dp.callback_query(F.data.startswith("rep_"))
async def cb_start_reply(call: CallbackQuery, state: FSMContext):
    """
    Hisob egasi '✍️ Bot orqali javob yozish' tugmasini bosganda ishga tushadi.
    """
    client_id = int(call.data.replace("rep_", ""))
    msg_id = call.message.message_id
    info = notification_map.get(msg_id)

    if not info:
        await call.answer("Ushbu murojaat ma'lumotlari yangilangan, bevosita profilga yozing.", show_alert=True)
        return

    await state.set_state(AdminReplyState.waiting_for_reply)
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


@dp.message(AdminReplyState.waiting_for_reply, F.text)
async def process_admin_reply_state(message: Message, state: FSMContext):
    """
    Admin tugma orqali javob matnini yuborganida.
    """
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
    """
    Admin to'g'ridan-to'g'ri bildirishnoma xabariga 'Reply' (Javob berish) qilib yozganda.
    """
    replied_msg_id = message.reply_to_message.message_id
    info = notification_map.get(replied_msg_id)

    if not info:
        # Oddiy suhbat bo'lishi mumkin
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
# 3. ODDIY BOT BUYRUQLARI VA START
# ==========================================

@dp.message(CommandStart())
async def cmd_start(message: Message):
    user = message.from_user
    admins = bot_data.setdefault("admins", [])
    if user.id not in admins:
        admins.append(user.id)
        save_data(bot_data)
        logger.info(f"Yangi admin ro'yxatga olindi: {user.full_name} (ID: {user.id})")

    text = (
        f"👑 <b>Assalomu alaykum, {html.escape(user.first_name)}!</b>\n\n"
        "Men sizning <b>Aqlli Shaxsiy Yordamchingizman</b>.\n\n"
        "🌟 <b>Tizim qanday ishlaydi:</b>\n"
        "1️⃣ Telegram akkauntingizga mijozlar yozganda, men sizning nomingizdan muloyim javob beraman "
        "(xabarni sizga yetkazganimni bildiraman va kerakli savollarni beraman).\n"
        "2️⃣ Har bir yozgan mijoz bo'yicha <b>darhol shu yerga to'liq ma'lumot</b> keladi:\n"
        "   <i>«Falonchi mijoz shunday-shunday demoqda, javob bering»</i> deb.\n"
        "3️⃣ Siz shunchaki ushbu xabarga <b>'Reply'</b> qilib yozsangiz, javobingiz to'g'ridan-to'g'ri o'sha mijozga boradi!\n\n"
        "ℹ️ <b>Holatni tekshirish:</b> /status\n"
        "⚙️ <b>Qo'llanma:</b> /help"
    )
    await message.answer(text, parse_mode="HTML")


@dp.message(Command("status"))
async def cmd_status(message: Message):
    me = await bot.get_me()
    active_count = len(bot_data.get("connections", {}))
    admins_count = len(bot_data.get("admins", []))
    status_text = (
        f"📊 <b>Bot Holati:</b>\n\n"
        f"🤖 Bot: @{me.username} ({me.first_name})\n"
        f"🧠 AI Model: <code>{ai_service.model}</code>\n"
        f"🔗 Faol Telegram Business ulanishlar: <b>{active_count} ta</b>\n"
        f"👥 Bildirishnoma oluvchi adminlar: <b>{admins_count} ta</b>\n"
        f"🟢 Server: <b>Online (Faol)</b>"
    )
    await message.answer(status_text, parse_mode="HTML")


@dp.message(Command("help"))
async def cmd_help(message: Message):
    help_text = (
        "📖 <b>Foydalanish Qo'llanmasi:</b>\n\n"
        "1. <b>Mijoz xabar yozganda:</b> Bot sizga darhol uning ismi, profili va nima degani haqida bildirishnoma tashlaydi.\n"
        "2. <b>Mijozga javob berish uchun:</b> Kelgan xabarga 'Reply' qilib yozing yoki '✍️ Bot orqali javob yozish' tugmasini bosing.\n"
        "3. <b>Biznes sozlamalari:</b> Agar bot ulanmagan bo'lsa, Telegram Sozlamalar -> Telegram Business -> Chatbotlar bo'limidan botni ulang."
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
    logger.info(f"Bot ishga tushdi: @{me.username} ({me.first_name})")
    print(f"\n==========================================")
    print(f"🤖 Bot muvaffaqiyatli ishga tushdi: @{me.username}")
    print(f"==========================================\n")
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")
