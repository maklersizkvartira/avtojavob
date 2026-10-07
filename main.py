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
from aiogram.types import (
    BusinessConnection,
    BusinessMessagesDeleted,
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.enums import ChatAction

from ai_service import AIService

# .env faylini yuklash
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AI_BASE_URL = os.getenv("AI_BASE_URL")
AI_MODEL = os.getenv("AI_MODEL", "qwen/qwen3.8-27b")
SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT", "")
OWNER_ID = os.getenv("OWNER_ID")  # Ixtiyoriy, agar .env da ko'rsatilsa

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

# Telegram Bot va Dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Ulanishlarni faylda saqlash (qayta ishga tushganda o'chib ketmasligi uchun)
CONNECTIONS_FILE = "connections.json"

def load_connections() -> dict:
    if os.path.exists(CONNECTIONS_FILE):
        try:
            with open(CONNECTIONS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Connections faylini o'qishda xatolik: {e}")
            return {}
    return {}

def save_connections(data: dict):
    try:
        with open(CONNECTIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Connections faylini saqlashda xatolik: {e}")

# Faol biznes ulanishlar
business_connections: dict = load_connections()


async def send_owner_notification(owner_chat_id: int, sender, user_msg: str, bot_reply: str):
    """
    Bot avtojavob berganda, hisob egasiga kim yozgani va nima deb javob berilgani haqida xabarnoma yuboradi.
    """
    try:
        username_str = f"@{sender.username}" if sender.username else "Mavjud emas"
        if sender.username:
            user_url = f"https://t.me/{sender.username}"
            profile_html = f'<a href="{user_url}">@{sender.username}</a>'
        else:
            user_url = None
            profile_html = f'<a href="tg://user?id={sender.id}">{html.escape(sender.full_name)}</a>'

        now_str = datetime.now().strftime("%H:%M:%S, %d.%m.%Y")

        notify_text = (
            "🔔 <b>Yangi Mijozga Avtojavob Berildi!</b>\n\n"
            f"👤 <b>Mijoz:</b> {html.escape(sender.full_name)}\n"
            f"🔗 <b>Username:</b> {profile_html}\n"
            f"🆔 <b>ID:</b> <code>{sender.id}</code>\n\n"
            f"💬 <b>Mijoz yozgan xabar:</b>\n"
            f"<blockquote>{html.escape(user_msg)}</blockquote>\n\n"
            f"🤖 <b>AI bergan javob:</b>\n"
            f"<blockquote>{html.escape(bot_reply)}</blockquote>\n\n"
            f"⏰ <b>Vaqt:</b> {now_str}"
        )

        reply_markup = None
        if user_url:
            reply_markup = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="💬 Mijoz profilini ochish", url=user_url)]
                ]
            )

        await bot.send_message(
            chat_id=owner_chat_id,
            text=notify_text,
            parse_mode="HTML",
            reply_markup=reply_markup
        )
        logger.info(f"Akkaunt egasiga ({owner_chat_id}) xabarnoma yetkazildi.")
    except Exception as e:
        logger.error(f"Akkaunt egasiga xabarnoma yuborishda xatolik: {e}")


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
    if connection.is_enabled:
        business_connections[conn_id] = {
            "owner_id": user.id,
            "owner_chat_id": connection.user_chat_id,
            "owner_name": user.full_name,
            "owner_username": user.username,
        }
        save_connections(business_connections)
        logger.info(
            f"✅ Yangi biznes ulanish! Foydalanuvchi: {user.full_name} (@{user.username}, id: {user.id}) | "
            f"Connection ID: {conn_id} | Chat ID: {connection.user_chat_id}"
        )
    else:
        business_connections.pop(conn_id, None)
        save_connections(business_connections)
        logger.info(
            f"❌ Biznes ulanish o'chirildi! Foydalanuvchi: {user.full_name} (@{user.username}, id: {user.id})"
        )


@dp.business_message(F.text)
async def on_business_message(message: Message):
    """
    Telegram Business hisobiga shaxsiy chatlarda kelgan xabarlarga avtomatik AI javob qaytarish.
    """
    conn_id = message.business_connection_id
    sender = message.from_user
    chat_id = message.chat.id

    conn_info = business_connections.get(conn_id, {})
    owner_id = conn_info.get("owner_id")
    owner_chat_id = conn_info.get("owner_chat_id")

    # Agar .env da OWNER_ID ko'rsatilgan bo'lsa, zaxira sifatida ishlatamiz
    if not owner_chat_id and OWNER_ID:
        try:
            owner_chat_id = int(OWNER_ID)
        except ValueError:
            pass

    # Agar xabarni hisob egasi (o'zingiz) yozgan bo'lsa, unga javob qaytarmaymiz
    if (owner_id and sender.id == owner_id) or (OWNER_ID and str(sender.id) == str(OWNER_ID)):
        logger.info(f"Akkaunt egasi ({sender.full_name}) yozdi. Avtojavob berilmadi.")
        return

    # Botlarga javob bermaslik
    if sender.is_bot:
        return

    logger.info(
        f"📩 Biznes xabar keldi: '{message.text}' | Yuboruvchi: {sender.full_name} (@{sender.username}) | Chat: {chat_id}"
    )

    # Foydalanuvchiga 'yozmoqda...' (typing) statusini ko'rsatish
    try:
        await bot.send_chat_action(
            chat_id=chat_id,
            action=ChatAction.TYPING,
            business_connection_id=conn_id
        )
    except Exception as e:
        logger.warning(f"Typing action yuborishda xatolik: {e}")

    # OpenAI / Groq orqali aqlli javob olish
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
        logger.info(f"📤 Avtojavob mijozga yuborildi: {reply_text[:50]}...")
    except Exception as e:
        logger.error(f"Xabar yuborishda xatolik: {e}")
        return

    # 🔔 HISOB EGASIGA XABARNOMA YUBORISH
    target_owner = owner_chat_id or owner_id
    if target_owner:
        await send_owner_notification(
            owner_chat_id=target_owner,
            sender=sender,
            user_msg=message.text,
            bot_reply=reply_text
        )


@dp.deleted_business_messages()
async def on_deleted_business_messages(event: BusinessMessagesDeleted):
    logger.info(f"Biznes xabarlar o'chirildi: {event.message_ids} in chat {event.chat.id}")


# ==========================================
# 2. ODDIY BOT BUYRUQLARI VA XABARLARI
# ==========================================

@dp.message(CommandStart())
async def cmd_start(message: Message):
    # Foydalanuvchi botga /start bosganda, uni ma'lumotlar bazasida saqlab qo'yamiz
    user = message.from_user
    logger.info(f"User /start bosdi: {user.full_name} (ID: {user.id})")

    # Agar ulanishlarda hali owner_chat_id belgilanmagan bo'lsa, moslashtirib qo'yamiz
    updated = False
    for conn_id, info in business_connections.items():
        if info.get("owner_id") == user.id:
            info["owner_chat_id"] = message.chat.id
            updated = True
    if updated:
        save_connections(business_connections)

    text = (
        f"👋 <b>Assalomu alaykum, {html.escape(user.first_name)}!</b>\n\n"
        "Men <b>Telegram Business & AI Avtojavob</b> botiman.\n\n"
        "⚡ <b>Meni Telegram profilingizga qanday ulash mumkin:</b>\n"
        "1️⃣ Telegram <b>Sozlamalar (Настройки)</b> bo'limiga kiring.\n"
        "2️⃣ <b>Telegram Business</b> bo'limini tanlang.\n"
        "3️⃣ <b>Chatbotlar (Чат-боты)</b> bandiga kiring.\n"
        f"4️⃣ Qidiruvga <code>@{ (await bot.get_me()).username }</code> deb yozing va botni ulang!\n\n"
        "🎯 <b>Qanday ishlaydi:</b>\n"
        "• Shaxsiy profilingizga kimdir yozsa, AI sizning nomingizdan aqlli javob beradi.\n"
        "• Bot darhol <b>shu yerga (botingizga)</b> xabar yuborib, qaysi mijoz nima deb yozgani, uning username va profil havolasini sizga tashlaydi!\n\n"
        "ℹ️ Bot holatini tekshirish: /status\n"
        "⚙️ Sozlamalar va yordam: /help"
    )
    await message.answer(text, parse_mode="HTML")


@dp.message(Command("help"))
async def cmd_help(message: Message):
    help_text = (
        "📖 <b>Telegram Business Bot Yo'riqnomasi:</b>\n\n"
        "<b>BotFather sozlamalari:</b>\n"
        "Bot Telegram Business bilan ishlashi uchun @BotFather da ruxsat berilgan bo'lishi kerak:\n"
        "1. @BotFather ga kiring\n"
        "2. <code>/mybots</code> buyrug'ini bering va botingizni tanlang\n"
        "3. <b>Bot Settings</b> -> <b>Telegram Business</b> bo'limiga kiring\n"
        "4. U yerdan <b>Turn On</b> qilib biznes rejimini yoqing.\n\n"
        "<b>Profilga ulash:</b>\n"
        "Telegram -> Sozlamalar -> Telegram Business -> Chatbotlar -> Botni tanlang.\n\n"
        "Bot har bir avtojavob berilgan mijoz haqida sizga hisobot yuborib turadi."
    )
    await message.answer(help_text, parse_mode="HTML")


@dp.message(Command("status"))
async def cmd_status(message: Message):
    me = await bot.get_me()
    active_count = len(business_connections)
    status_text = (
        f"📊 <b>Bot Holati:</b>\n\n"
        f"🤖 Bot: @{me.username} ({me.first_name})\n"
        f"🧠 AI Model: <code>{ai_service.model}</code>\n"
        f"🔗 Faol biznes ulanishlar soni: <b>{active_count} ta</b>\n"
        f"🟢 Server holati: <b>Ishlamoqda (Online)</b>"
    )
    await message.answer(status_text, parse_mode="HTML")


@dp.message(F.text)
async def on_direct_message(message: Message):
    """
    Agar botga to'g'ridan-to'g'ri (bot ichida) yozishsa ham AI javob qaytaradi.
    """
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    chat_key = f"direct_{message.chat.id}"
    reply = await ai_service.get_reply(
        chat_key=chat_key,
        user_message=message.text,
        sender_name=message.from_user.full_name
    )
    await message.answer(reply)


# ==========================================
# ASOSIY FUNKSIYA
# ==========================================

async def main():
    me = await bot.get_me()
    logger.info(f"Bot ishga tushdi: @{me.username} ({me.first_name})")
    print(f"\n==========================================")
    print(f"🤖 Bot muvaffaqiyatli ishga tushdi: @{me.username}")
    print(f"==========================================\n")
    
    # Eskirgan updatelarni o'chirish va polling boshlash
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")
