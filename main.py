import asyncio
import html
import io
import json
import logging
import os
import re
import sys
import time
from datetime import datetime
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

# Ma'lumotlarni saqlash fayli
DATA_FILE = "bot_data.json"

START_TIME = time.time()


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
        "user_names": {},
        "owner_statuses": {},
        "custom_prompts": {},
        "chat_bot_messages": {},
        "stats": {
            "total_messages": 0,
            "ai_replies": 0,
            "voice_transcriptions": 0,
            "leads_detected": 0
        }
    }


def save_data(data: dict):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ma'lumotlarni saqlashda xatolik: {e}")


bot_data = load_data()
if "stats" not in bot_data:
    bot_data["stats"] = {
        "total_messages": 0,
        "ai_replies": 0,
        "voice_transcriptions": 0,
        "leads_detected": 0
    }

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

ai_service = AIService(
    api_key=OPENAI_API_KEY,
    model=AI_MODEL,
    base_url=AI_BASE_URL,
    owner_name=OWNER_NAME_DEFAULT,
    system_prompt=SYSTEM_PROMPT
)

# Inline xabarlarni bog'lash kesh
notification_map = {}


# FSM holatlari
class FormStates(StatesGroup):
    waiting_for_reply = State()
    waiting_for_name = State()
    waiting_for_prompt = State()


# Yordamchi funksiyalar
def get_user_name(user_id: int, fallback: str = "Zayniddin") -> str:
    names = bot_data.setdefault("user_names", {})
    return names.get(str(user_id), fallback or OWNER_NAME_DEFAULT)


def set_user_name(user_id: int, name: str):
    names = bot_data.setdefault("user_names", {})
    names[str(user_id)] = name.strip()
    save_data(bot_data)


def get_user_status(user_id: int) -> str:
    statuses = bot_data.setdefault("owner_statuses", {})
    return statuses.get(str(user_id), "offline")


def set_user_status(user_id: int, status: str):
    statuses = bot_data.setdefault("owner_statuses", {})
    statuses[str(user_id)] = status
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
    """Telefon raqami yoki uchrashuv/aloqa talabini aniqlash."""
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


# Klaviaturalar
def get_settings_keyboard(user_id: int) -> InlineKeyboardMarkup:
    status = get_user_status(user_id)
    status_btn_text = "🟢 Onlayn (Avtojavob to'xtatilgan)" if status == "online" else "🔴 Oflayn (Avtojavob faol)"
    toggle_val = "set_offline" if status == "online" else "set_online"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=f"🔄 Holat: {status_btn_text}", callback_data=toggle_val)
            ],
            [
                InlineKeyboardButton(text="✏️ Ismni o'zgartirish", callback_data="btn_change_name"),
                InlineKeyboardButton(text="🎭 AI Uslubi", callback_data="btn_select_mode")
            ],
            [
                InlineKeyboardButton(text="📝 Shaxsiy Prompt", callback_data="btn_change_prompt"),
                InlineKeyboardButton(text="🧹 Xotirani tozalash", callback_data="btn_clear_history")
            ],
            [
                InlineKeyboardButton(text="📊 Statistika", callback_data="btn_show_stats"),
                InlineKeyboardButton(text="⚡ Bot Holati", callback_data="btn_check_status")
            ]
        ]
    )


def get_mode_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🎯 Standart (Do'stona)", callback_data="mode_standard"),
                InlineKeyboardButton(text="💼 Biznes & Savdo", callback_data="mode_business")
            ],
            [
                InlineKeyboardButton(text="⚡ Qisqa va lo'nda", callback_data="mode_concise"),
                InlineKeyboardButton(text="📚 Chuqur tahliliy", callback_data="mode_detailed")
            ],
            [
                InlineKeyboardButton(text="◀️ Orqaga", callback_data="btn_back_settings")
            ]
        ]
    )


# ==========================================
# 1. TELEGRAM BUSINESS VOQEALARI
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

        # Agar ism belgilanmagan bo'lsa
        if str(user_id) not in bot_data.get("user_names", {}):
            set_user_name(user_id, conn.user.first_name)

        owner_name = get_user_name(user_id, conn.user.first_name)
        try:
            await bot.send_message(
                chat_id=user_id,
                text=(
                    f"🎉 <b>Tabriklaymiz, {html.escape(owner_name)}!</b>\n\n"
                    "Telegram Business profilingiz botga muvaffaqiyatli ulandi!\n"
                    "Endi sizga mijozlar shaxsiy xabar yoki ovozli xabar yuborsa, bot sizning nomingizdan "
                    "aqlli AI orqali avtomatik javob bera oladi.\n\n"
                    "⚙️ <i>Boshqarish uchun /start buyrug'idan foydalaning.</i>"
                ),
                parse_mode="HTML",
                reply_markup=get_settings_keyboard(user_id)
            )
        except Exception as e:
            logger.warning(f"Foydalanuvchiga xabar yuborib bo'lmadi: {e}")
    else:
        if conn_id in connections:
            del connections[conn_id]
            save_data(bot_data)
        logger.info(f"❌ Telegram Business uzildi: conn_id={conn_id}")


@dp.business_message()
async def on_business_message(message: Message):
    conn_id = message.business_connection_id
    if not conn_id:
        return

    bot_data["stats"]["total_messages"] += 1

    connections = bot_data.get("connections", {})
    owner_user_id = connections.get(conn_id)

    sender = message.from_user
    client_chat_id = message.chat.id
    stored_key = f"{conn_id}_{client_chat_id}"

    # 1. AKKAUNT EGASI CHATGA YOZSA -> AVTO-TOZALASH
    if owner_user_id and sender.id == owner_user_id:
        logger.info(f"Akkaunt egasi ({sender.id}) chatga kirdi. Avtojavoblar tozalanadi.")
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

    # 2. AGAR EGASI ONLAYN BO'LSA VA AVTOJAVOB O'CHIRILGAN BO'LSA
    if owner_user_id:
        status = get_user_status(owner_user_id)
        if status == "online":
            return

    owner_name = get_user_name(owner_user_id, "Zayniddin") if owner_user_id else OWNER_NAME_DEFAULT

    # Matn yoki Ovozli xabarni aniqlash
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

    if not user_text:
        return

    chat_key = f"biz_{conn_id}_{client_chat_id}"
    await bot.send_chat_action(
        chat_id=client_chat_id,
        action=ChatAction.TYPING,
        business_connection_id=conn_id
    )

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

    # Akkaunt egasiga xabardor qilish
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
    """Foydalanuvchi botga ovozli xabar yuborganda."""
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
            await status_msg.edit_text("❌ Ovozni aniqlab bo'lmadi. Iltimos, qaytadan yozib ko'ring yoki matn ko'rinishida yuboring.")
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
    # Agar reply kutilayotgan holat bo'lsa
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

    # Bildirishnoma (adminlar uchun)
    targets = get_all_target_admins()
    if sender.id not in targets:
        username_str = f"@{sender.username}" if sender.username else f"ID: {sender.id}"
        notify_text = (
            "📩 <b>Botga yangi to'g'ridan-to'g'ri xabar keldi:</b>\n\n"
            f"👤 <b>Foydalanuvchi:</b> {html.escape(sender.full_name)} ({username_str})\n\n"
            f"💬 <b>Savol:</b>\n<blockquote>{html.escape(message.text)}</blockquote>\n\n"
            f"🤖 <b>AI javobi:</b>\n<blockquote>{html.escape(reply)}</blockquote>"
        )
        for admin_id in targets:
            try:
                await bot.send_message(chat_id=admin_id, text=notify_text, parse_mode="HTML")
            except Exception:
                pass


# ==========================================
# 3. BUYRUQLAR VA BOSHQARUV (COMMANDS)
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
    status = get_user_status(user.id)
    status_badge = "🟢 ONLAYN" if status == "online" else "🔴 OFLAYN (Avtojavob faol)"
    current_mode = ai_service.get_mode(f"direct_{message.chat.id}")

    text = (
        f"👑 <b>Assalomu alaykum, {html.escape(my_name)}!</b>\n\n"
        f"Men sizning <b>Aqlli Shaxsiy Yordamchingiz va Avtojavob AI Botiman</b>.\n\n"
        "✨ <b>Yangi Imkoniyatlar:</b>\n"
        "• 🎙️ <b>Ovozli xabarlar (Voice Notes)</b>: Ovozli xabarlarni avtomatik matnga aylantirib, tushunib javob qaytara olaman.\n"
        "• 🧠 <b>Kontekst xotirasi</b>: Suhbat jarayonini eslab qolaman.\n"
        "• 🎭 <b>AI Uslublari</b>: Standart, Biznes, Lo'nda yoki Chuqur tahliliy javob rejimlari.\n"
        "• ⚡ <b>Telegram Business avtojavob</b>: Profilingizga kelgan har qanday savolga sizning nomingizdan samimiy javob beraman.\n\n"
        f"👤 <b>Akkaunt / Brend egasi:</b> <b>{html.escape(my_name)}</b>\n"
        f"⚡ <b>Holatingiz:</b> <b>{status_badge}</b>\n"
        f"🎭 <b>AI Uslubi:</b> <b>{current_mode.upper()}</b>\n\n"
        "<i>Quyidagi tugmalar orqali barcha sozlamalarni qulay boshqaring:</i>"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=get_settings_keyboard(user.id))


@dp.message(Command("help"))
async def cmd_help(message: Message):
    help_text = (
        "💡 <b>Bot Buyruqlari va Yo'riqnoma:</b>\n\n"
        "• /start — Boshqaruv paneli va asosiy menyu\n"
        "• /status — Server va ulanishlar holatini tekshirish\n"
        "• /stats — Ishlatilish statistikasi\n"
        "• /mode — AI javob berish uslubini almashtirish\n"
        "• /clear yoki /reset — Suhbat xotirasini tozalash\n"
        "• /setname &lt;Ism&gt; — Akkaunt egasi ismini yangilash\n"
        "• /prompt — Shaxsiy biznes yo'riqnomasini ko'rish yoki yangilash\n\n"
        "🎙️ <i>Shuningdek, istalgan vaqtda ovozli xabar yuborishingiz mumkin!</i>"
    )
    await message.answer(help_text, parse_mode="HTML")


@dp.message(Command("clear"))
@dp.message(Command("reset"))
async def cmd_clear(message: Message):
    chat_key = f"direct_{message.chat.id}"
    ai_service.clear_history(chat_key)
    await message.answer("🧹 <b>Suhbat xotirasi tozalandi!</b> Yangi mavzuni boshlashingiz mumkin.", parse_mode="HTML")


@dp.message(Command("status"))
async def cmd_status(message: Message):
    me = await bot.get_me()
    user_id = message.from_user.id
    active_count = len(bot_data.get("connections", {}))
    status = get_user_status(user_id)
    status_badge = "🟢 ONLAYN" if status == "online" else "🔴 OFLAYN"
    current_name = get_user_name(user_id, message.from_user.first_name)
    uptime_sec = int(time.time() - START_TIME)
    uptime_str = f"{uptime_sec // 3600}s {(uptime_sec % 3600) // 60}d {uptime_sec % 60}son"

    status_text = (
        f"📊 <b>Bot va Server Holati:</b>\n\n"
        f"🤖 <b>Bot:</b> @{me.username} ({me.first_name})\n"
        f"👑 <b>Ega nomi:</b> <b>{html.escape(current_name)}</b>\n"
        f"⚡ <b>Holat:</b> <b>{status_badge}</b>\n"
        f"🔗 <b>Telegram Business:</b> <b>{active_count} ta faol ulanish</b>\n"
        f"⏱ <b>Ish vaqti:</b> <code>{uptime_str}</code>\n"
        f"🟢 <b>Server:</b> Online (Railway Cloud)"
    )
    await message.answer(status_text, parse_mode="HTML")


@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    stats = bot_data.get("stats", {})
    text = (
        "📈 <b>Bot Ish Faoliyati Statistikasi:</b>\n\n"
        f"📨 Jami qabul qilingan xabarlar: <b>{stats.get('total_messages', 0)} ta</b>\n"
        f"🤖 AI qaytargan javoblar: <b>{stats.get('ai_replies', 0)} ta</b>\n"
        f"🎙️ Ovozli xabarlar transkripsiyasi: <b>{stats.get('voice_transcriptions', 0)} ta</b>\n"
        f"🚨 Aniqlangan muhim mijozlar (Leads): <b>{stats.get('leads_detected', 0)} ta</b>\n"
        f"🔗 Faol Business akkauntlar: <b>{len(bot_data.get('connections', {}))} ta</b>"
    )
    await message.answer(text, parse_mode="HTML")


@dp.message(Command("mode"))
async def cmd_mode(message: Message):
    chat_key = f"direct_{message.chat.id}"
    cur_mode = ai_service.get_mode(chat_key)
    await message.answer(
        f"🎭 <b>AI Javob Uslubini Tanlang:</b>\n\nJoriy uslub: <b>{cur_mode.upper()}</b>",
        parse_mode="HTML",
        reply_markup=get_mode_keyboard()
    )


@dp.message(Command("setname"))
async def cmd_setname(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Iltimos, ism kiriting. Masalan:\n<code>/setname Zayniddin</code>", parse_mode="HTML")
        return
    new_name = args[1].strip()
    set_user_name(message.from_user.id, new_name)
    await message.answer(f"✅ Akkaunt egasi nomi muvaffaqiyatli saqlandi: <b>{html.escape(new_name)}</b>", parse_mode="HTML")


# ==========================================
# 4. CALLBACK QUERIES
# ==========================================

@dp.callback_query(F.data.in_(["set_online", "set_offline"]))
async def cb_toggle_status(call: CallbackQuery):
    user_id = call.from_user.id
    new_val = "online" if call.data == "set_online" else "offline"
    set_user_status(user_id, new_val)
    await call.message.edit_reply_markup(reply_markup=get_settings_keyboard(user_id))
    msg = "🟢 Siz ONLAYN holatiga o'tdingiz. Avtojavob to'xtatildi." if new_val == "online" else "🔴 Siz OFLAYN holatiga o'tdingiz. AI avtojavob faol!"
    await call.answer(msg, show_alert=True)


@dp.callback_query(F.data == "btn_select_mode")
async def cb_select_mode(call: CallbackQuery):
    await call.message.edit_text(
        "🎭 <b>AI Javob Uslubini Tanlang:</b>\n\n"
        "• <b>Standart:</b> Samimiy va tabiiy insondek suhbat.\n"
        "• <b>Biznes & Savdo:</b> Rasmiy, xushmuomala va mijozni jalb qilishga qaratilgan.\n"
        "• <b>Qisqa:</b> Faqat lo'nda va eng muhim ma'lumot.\n"
        "• <b>Chuqur:</b> Barcha tafsilotlarni keng tushuntiruvchi.",
        parse_mode="HTML",
        reply_markup=get_mode_keyboard()
    )
    await call.answer()


@dp.callback_query(F.data.startswith("mode_"))
async def cb_apply_mode(call: CallbackQuery):
    chosen_mode = call.data.replace("mode_", "")
    chat_key = f"direct_{call.message.chat.id}"
    ai_service.set_mode(chat_key, chosen_mode)
    await call.answer(f"✅ AI Uslubi o'zgartirildi: {chosen_mode.upper()}", show_alert=True)
    await call.message.edit_text(
        f"✅ <b>AI Uslubi: {chosen_mode.upper()}</b> ga o'zgartirildi!\nBoshqaruv menyusiga qaytish uchun tugmani bosing.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="◀️ Bosh Menyu", callback_data="btn_back_settings")]]
        )
    )


@dp.callback_query(F.data == "btn_back_settings")
async def cb_back_settings(call: CallbackQuery):
    user_id = call.from_user.id
    my_name = get_user_name(user_id, call.from_user.first_name)
    status = get_user_status(user_id)
    status_badge = "🟢 ONLAYN" if status == "online" else "🔴 OFLAYN (Avtojavob faol)"

    await call.message.edit_text(
        f"👑 <b>Boshqaruv Paneli: {html.escape(my_name)}</b>\n\n"
        f"⚡ Holat: <b>{status_badge}</b>\n\n"
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
        "📈 <b>Bot Statistikasi:</b>\n\n"
        f"📨 Jami xabarlar: <b>{stats.get('total_messages', 0)} ta</b>\n"
        f"🤖 AI javoblar: <b>{stats.get('ai_replies', 0)} ta</b>\n"
        f"🎙️ Ovozli xabarlar: <b>{stats.get('voice_transcriptions', 0)} ta</b>\n"
        f"🚨 Muhim mijozlar: <b>{stats.get('leads_detected', 0)} ta</b>\n"
        f"🔗 Ulanishlar: <b>{len(bot_data.get('connections', {}))} ta</b>"
    )
    await call.message.reply(text, parse_mode="HTML")
    await call.answer()


@dp.callback_query(F.data == "btn_check_status")
async def cb_check_status(call: CallbackQuery):
    me = await bot.get_me()
    uptime_sec = int(time.time() - START_TIME)
    uptime_str = f"{uptime_sec // 3600}s {(uptime_sec % 3600) // 60}d {uptime_sec % 60}son"
    text = (
        f"🟢 <b>Server va Bot Faol:</b>\n\n"
        f"🤖 Bot: @{me.username}\n"
        f"⏱ Ish vaqti: <code>{uptime_str}</code>\n"
        f"🌐 Railway Cloud: Connected"
    )
    await call.message.reply(text, parse_mode="HTML")
    await call.answer()


@dp.callback_query(F.data.startswith("rep_"))
async def cb_reply_customer(call: CallbackQuery, state: FSMContext):
    client_chat_id = call.data.replace("rep_", "")
    msg_id = call.message.message_id
    info = notification_map.get(msg_id)
    if not info:
        await call.answer("Mijoz ma'lumotlari yangilangan, bevosita profilingiz orqali yozing.", show_alert=True)
        return

    await state.set_state(FormStates.waiting_for_reply)
    await state.update_data(
        conn_id=info["conn_id"],
        client_chat_id=info["client_chat_id"],
        client_name=info["client_name"]
    )

    await call.message.reply(
        f"✍️ <b>{html.escape(info['client_name'])}</b>ga yuboriladigan xabaringizni yozing:\n\n"
        "<i>(Ushbu xabar mijozning chatiga bot orqali darhol yetkaziladi)</i>",
        parse_mode="HTML"
    )
    await call.answer()


# ==========================================
# 5. RAILWAY UCHUN HEALTHCHECK HTTP SERVER
# ==========================================

async def healthcheck_handler(request):
    uptime_sec = int(time.time() - START_TIME)
    return web.json_response({
        "status": "ok",
        "bot": "AvtoJavob AI",
        "uptime_seconds": uptime_sec,
        "connections": len(bot_data.get("connections", {})),
        "total_messages": bot_data.get("stats", {}).get("total_messages", 0)
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
# 6. ASOSIY ISHGA TUSHIRISH
# ==========================================

async def main():
    me = await bot.get_me()
    logger.info(f"Bot ishga tushdi: @{me.username} ({me.first_name})")
    print(f"\n==========================================")
    print(f"🤖 Bot muvaffaqiyatli ishga tushdi: @{me.username}")
    print(f"🎙️ Ovozli xabarlar va Whisper AI: FAOL")
    print(f"⚡ Ko'p funksiyali AI Avtojavob tizimi: TAYYOR")
    print(f"==========================================\n")

    # Railway uchun HTTP healthcheck serverini parallel ishga tushiramiz
    asyncio.create_task(start_http_server())

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")
