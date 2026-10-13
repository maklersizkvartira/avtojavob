# 🤖 AvtoJavob AI — Telegram Business & Shaxsiy Aqlli Yordamchi

Telegram Business hamda shaxsiy chatlar uchun sun'iy intellekt (AI) asosidagi ko'p funksiyali yordamchi bot.

---

## 🌟 Yangi Imkoniyatlar va Funksiyalar

1. **🎙️ Ovozli xabarlar (Voice Notes & Audio)**:
   - Foydalanuvchilar yoki mijozlar ovozli xabar yuborganda, bot **Whisper Large V3 Turbo** modeli orqali ovozni bir necha soniyada aniq matnga aylantiradi va AI orqali to'liq javob beradi.

2. **🧠 Kontekst Xotirasi**:
   - Suhbat davomida oldingi gaplarni eslab qoladi va mantiqiy bog'langan javoblarni taqdim etadi. Xotirani tozalash uchun `/clear` yoki `/reset` buyrug'i mavjud.

3. **🎭 4 Xil AI Javob Uslubi (/mode)**:
   - 🎯 **Standart**: Samimiy va tabiiy do'stona suhbat.
   - 💼 **Biznes & Savdo**: Rasmiy, mijozlar bilan savdo va kelishuvlar uchun yo'naltirilgan.
   - ⚡ **Qisqa va lo'nda**: Faqat eng kerakli ma'lumotlarni lo'nda bayon qilish.
   - 📚 **Chuqur tahliliy**: Savolni to'liq, batafsil va tahliliy yoritish.

4. **🚨 Aqlli Mijoz/Aloqa Aniqlash (Lead Detector)**:
   - Mijoz telefon raqami, qo'ng'iroq yoki uchrashuv so'raganida bot buni avtomatik aniqlab, akkaunt egasiga alohida diqqat bildirishnomasi bilan xabar beradi.

5. **⚡ Telegram Business Avtojavob & Avto-tozalash**:
   - Siz oflayn bo'lganingizda bot profilingiz nomidan mijozlarga muloyim javob beradi.
   - Siz chatga kirib o'zingiz yozganingizda, bot avval yozgan avtojavoblar mijoz chatidan avtomatik tozalanadi!

6. **🚂 Railway Cloud Tayyorligi**:
   - Web / Worker sifatida avtomatik ishlash uchun `PORT` orqali `/health` healthcheck serveri o'rnatilgan.

---

## 🛠 Buyruqlar

- `/start` — Interaktiv boshqaruv paneli va menyu
- `/status` — Server, bot va ulanishlar holatini tekshirish
- `/stats` — Xabarlar va AI javoblari statistikasi
- `/mode` — AI javob berish uslubini tanlash
- `/clear` yoki `/reset` — Chat xotirasini tozalash
- `/setname <Ism>` — Akkaunt egasi ismini belgilash
- `/prompt` — Shaxsiy biznes yo'riqnomasi

---

## 🚀 Ishga Tushirish

### Mahalliy muhitda:
```bash
.venv/bin/python main.py
```

### Railway platformasida:
Loyiha `railway.json`, `Procfile` va `Dockerfile` bilan to'liq jihozlangan. Railway loyihasiga `BOT_TOKEN` va boshqa o'zgaruvchilarni kiritish kifoya.
