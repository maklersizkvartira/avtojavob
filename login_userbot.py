import asyncio
import os
from telethon import TelegramClient
from dotenv import load_dotenv

load_dotenv()

API_ID = os.getenv("USERBOT_API_ID") or 2040
API_HASH = os.getenv("USERBOT_API_HASH") or "b18441a1ff607e10a989891a5462e627"

try:
    API_ID = int(API_ID)
except ValueError:
    API_ID = 2040

SESSION_NAME = "userbot_session"

async def main():
    print("=" * 50)
    print("📞 TELEGRAM USERBOT AVTORIZATSIYA DASTURI")
    print("=" * 50)
    print("Ushbu dastur orqali Telegram profilingizni botga bir marta ulab olasiz.")
    print("Keyin bot belgilangan vaqtda sizga avtomatik qo'ng'iroq qila oladi!\n")

    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.connect()

    if await client.is_user_authorized():
        me = await client.get_me()
        print(f"✅ Akkaunt allaqachon ulangan: {me.first_name} (@{me.username})")
        print("Hech narsa qilish shart emas. Botni ishga tushirishingiz mumkin!")
        await client.disconnect()
        return

    phone = input("📱 Telefon raqamingizni kiriting (masalan: +998901234567): ").strip()
    result = await client.send_code_request(phone)
    print("\n📩 Tasdiqlash kodi Telegram ilovangizga yuborildi!")

    code = input("🔑 Telegramdan kelgan kodni kiriting: ").strip().replace(" ", "").replace("-", "")

    try:
        await client.sign_in(phone=phone, code=code, phone_code_hash=result.phone_code_hash)
    except Exception as e:
        err_str = str(e).lower()
        if "password" in err_str or "2fa" in err_str or "two-step" in err_str:
            pwd = input("🔐 Akkauntingizda 2FA parol o'rnatilgan. Parolni kiriting: ").strip()
            await client.sign_in(password=pwd)
        else:
            print(f"\n❌ Xatolik yuz berdi: {e}")
            await client.disconnect()
            return

    me = await client.get_me()
    print("\n" + "=" * 50)
    print(f"🎉 MUVAFFAQINLI ULANDI!")
    print(f"👤 Profil: {me.first_name} (@{me.username})")
    print(f"📁 Sessiya fayli saqlandi: {SESSION_NAME}.session")
    print("Endi bot sizga bemalol telefon qila oladi!")
    print("=" * 50)

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
