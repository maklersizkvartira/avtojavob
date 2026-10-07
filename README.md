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

## 📁 Loyiha Tuzilishi:
- `main.py` - Telegram Bot va Telegram Business updatelarini qabul qiluvchi asosiy dastur.
- `ai_service.py` - OpenAI ChatGPT integratsiyasi va suhbat tarixini (kontekst) saqlovchi modul.
- `.env` - Bot tokeni va OpenAI kaliti sozlamalari.
- `requirements.txt` - Kerakli kutubxonalar ro'yxati.
