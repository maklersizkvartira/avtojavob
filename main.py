import asyncio
import logging
import os
import sys
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    BusinessConnection,
    BusinessMessagesDeleted,
    Message,
)
from aiogram.enums import ChatAction

from ai_service import AIService

# .env faylini yuklash
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AI_MODEL = os.getenv("AI_MODEL", "gpt-4o-mini")
SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT", "")

if not BOT_TOKEN:
    print("XATO: BOT_TOKEN ko'rsatilmagan! .env faylini tekshiring.")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("telegram_business_bot")

# AI servisini ishga tushirish
ai_service = AIService(api_key=OPENAI_API_KEY, model=AI_MODEL, system_prompt=SYSTEM_PROMPT)

# Telegram Bot va Dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Faol biznes ulanishlar (connection_id -> owner_user_id)
business_connections: dict[str, int] = {}


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
        business_connections[conn_id] = user.id
        logger.info(
            f"✅ Yangi biznes ulanish! Foydalanuvchi: {user.full_name} (@{user.username}, id: {user.id}) | "
            f"Connection ID: {conn_id} | Javob bera oladimi: {connection.can_reply}"
        )
    else:
        business_connections.pop(conn_id, None)
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

    # Agar xabarni hisob egasi (o'zingiz) yozgan bo'lsa, unga javob qaytarmaymiz
    owner_id = business_connections.get(conn_id)
    if owner_id and sender.id == owner_id:
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

    # OpenAI orqali aqlli javob olish
    chat_key = f"biz_{conn_id}_{chat_id}"
    reply_text = await ai_service.get_reply(
        chat_key=chat_key,
        user_message=message.text,
        sender_name=sender.full_name
    )

    # Javobni yuborish
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=reply_text,
            business_connection_id=conn_id
        )
        logger.info(f"📤 Avtojavob yuborildi: {reply_text[:50]}...")
    except Exception as e:
        logger.error(f"Xabar yuborishda xatolik: {e}")


@dp.deleted_business_messages()
async def on_deleted_business_messages(event: BusinessMessagesDeleted):
    logger.info(f"Biznes xabarlar o'chirildi: {event.message_ids} in chat {event.chat.id}")


# ==========================================
# 2. ODDIY BOT BUYRUQLARI VA XABARLARI
# ==========================================

@dp.message(CommandStart())
async def cmd_start(message: Message):
    text = (
        f"👋 <b>Assalomu alaykum, {message.from_user.first_name}!</b>\n\n"
        "Men <b>Telegram Business & AI Avtojavob</b> botiman.\n\n"
        "⚡ <b>Meni Telegram profilingizga qanday ulash mumkin:</b>\n"
        "1️⃣ Telegram <b>Sozlamalar (Настройки)</b> bo'limiga kiring.\n"
        "2️⃣ <b>Telegram Business</b> bo'limini tanlang.\n"
        "3️⃣ <b>Chatbotlar (Чат-боты)</b> bandiga kiring.\n"
        f"4️⃣ Qidiruvga <code>@{ (await bot.get_me()).username }</code> deb yozing va botni ulang!\n\n"
        "Shundan so'ng, shaxsiy profilingizga kimdir yozsa, sun'iy intellekt sizning nomingizdan darhol avtomatik javob beradi!\n\n"
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
        "Qo'shimcha savollar bo'lsa murojaat qilishingiz mumkin."
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
