# 🤖 Telegram Business AI Avtojavob Boti

Ushbu bot Telegram'ning yangi **Telegram Business Chatbots** imkoniyatidan foydalanib, shaxsiy yoki biznes profilingizga boshqalar xabar yozganda ularga **OpenAI (ChatGPT)** orqali avtomatik va aqlli tarzda javob qaytarish uchun mo'ljallangan.

---

## 🚀 Qanday qilib sozlash va ishlatish kerak?

### 1-qadam: @BotFather da Business rejimini yoqish (MUHIM!)
Bot Telegram Business hisobiga ulanishi uchun, avval BotFather'da ruxsat berilishi shart:
1. Telegramda [@BotFather](https://t.me/BotFather) botiga kiring.
2. `/mybots` buyrug'ini yuboring va botingizni (`@avtojavobai_bot`) tanlang.
3. **Bot Settings** tugmasini bosing.
4. **Telegram Business** (yoki **Business Mode**) bandini tanlang.
5. **Turn On** (Yoqish) tugmasini bosing.

---

### 2-qadam: Telegram profilingizga botni ulash
1. Telegram ilovasida **Sozlamalar (Настройки / Settings)** bo'limiga kiring.
2. **Telegram Business** bo'limini oching.
3. **Chatbotlar (Чат-боты / Chatbots)** bandiga kiring.
4. Bot qidiruv maydoniga `@avtojavobai_bot` deb yozing va tanlang.
5. Qaysi chatlarda javob berishini belgilang (Barchaga, yoki faqat kontaktda yo'qlarga va h.k.) va **Saqlash (Save)** tugmasini bosing.

Endi kimdir sizga shaxsiy xabar yozsa, bot sizning nomingizdan AI orqali avtomatik javob bera boshlaydi!

---

### 3-qadam: Botni kompyuterda ishga tushirish

Terminalda loyiha papkasida ushbu buyruqni bering:

```bash
cd /Users/macbookair/Desktop/Ai
.venv/bin/python main.py
```

---

## ⚠️ OpenAI Balansi (Hisob) haqida Muhim Eslatma:
Siz taqdim etgan OpenAI API kaliti tekshirilganda, unda **kredit/balans tugaganligi (RateLimit / credit_balance_exhausted)** aniqlandi:
- Yangi balans to'ldirish yoki yangi API kalit olish uchun: [platform.openai.com](https://platform.openai.com) saytiga kiring.
- Yangi kalitni `.env` faylidagi `OPENAI_API_KEY` parametriga joylang.

---

---

## 📞 Avtomatik Qo'ng'iroq va Aqlli Eslatmalar Tizimi (YANGI!):

Botga muhim ishlarni belgilab qo'yganingizda, belgilangan daqiqada **botning o'zi sizga avtomatik tarzda Telegram orqali telefon qiladi** va ogohlantiradi:

### 1. Qo'lda Eslatma / Qo'ng'iroq belgilash:
- Bot menyusidagi **«➕ Yangi eslatma»** tugmasini bosing yoki `/eslatma` buyrug'ini yuboring.
- Shunchaki tabiiy tilda yozing:
  - *«Ertaga soat 15:30 da Ali aka bilan uchrashuv»*
  - *«15 minutdan keyin dori ichish»*
  - *«Bugun 19:00 da hisobotni jo'natish»*
- Sun'iy intellekt (AI) vaqtni o'zi aniqlab, jadvalga kiritadi.

### 2. AI Avtomatik Aniqlash (Mijozlar bilan suhbatda):
- Mijoz sizning Telegram profilingizga yozganda (*masalan: «Ertaga soat 14:00 da ofisingizga boraman»*), AI buni sezadi va egasiga xabar beradi hamda sizga avtomatik qo'ng'iroq qilish jadvaliga qo'shadi!

### 3. Telegram orqali Qo'ng'iroq qilishni ulash (Userbot):
Telegram botlari rasman to'g'ridan-to'g'ri telefon qila olmagani sababli, tizimga **Userbot** integratsiya qilingan:
- Botda `/userbot` buyrug'ini bosing yoki menyudan **«⚙️ Userbot sozlamalari»** ni tanlang.
- Telefon raqamingizni va Telegramdan kelgan kodni kiriting.
- Sinab ko'rish uchun **«📞 Sinov qo'ng'irog'i (Test Call)»** yoki `/testcall` buyrug'ini bosing!

---

## 📁 Loyiha Tuzilishi:
- `main.py` - Telegram Bot va Telegram Business boshqaruvi, eslatmalar qayta ishlovchisi.
- `reminders_service.py` - Eslatmalar jadvali va fon tekshiruvi (Scheduler).
- `call_service.py` - Telegram VoIP / Userbot orqali qo'ng'iroq chaqiruvi moduli.
- `ai_service.py` - OpenAI ChatGPT integratsiyasi, matn tahlili va eslatma parsingi.
- `.env` - Bot tokeni, AI API kaliti va Userbot sozlamalari.
- `requirements.txt` - Kerakli kutubxonalar ro'yxati.
