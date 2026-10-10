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

---

## 🤖 AI Avtojavob va Aqlli Shaxsiy Yordamchi

1. **Telegram Business orqali mijozlarga avtojavob:**
   - Kimdir sizning Telegram profilingizga yozsa, AI sizning nomingizdan muloyim va aniq javob beradi.
   - Bot yozgan javoblar haqida hisob egasiga darhol bildirishnoma yetkaziladi.
   - Chatga o'zingiz kirib yozsangiz, bot avvalgi avtojavoblarni avtomatik tozalaydi!

2. **Botga to'g'ridan-to'g'ri yozilganda:**
   - Odamlar botning o'ziga yozsa, bot AI orqali savollarga mustaqil va to'liq avtomatik javob beradi.

## 📁 Loyiha Tuzilishi:
- `main.py` - Telegram Bot va Telegram Business boshqaruvi.
- `ai_service.py` - OpenAI/Groq AI integratsiyasi, shaxsiy identiklik himoyasi va suhbat xotirasi.
- `.env` - Bot tokeni va AI API kaliti.
- `requirements.txt` - Kerakli kutubxonalar ro'yxati.

