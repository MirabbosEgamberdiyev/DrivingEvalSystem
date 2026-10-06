# UX/UI ARXITEKTURA VA DIZAYN ME'YORLARI (ASSUMPTIONS_UI.md)

Ushbu hujjat "Standalone 4-Camera Offline AI Driving Training & Evaluation System" dasturining avtomobil ichidagi sensorli ekran (in-cabin touchscreen) UI qismi bo'yicha qabul qilingan arxitektura va ergonomik qarorlarni belgilaydi.

---

## 1. Sensorli Ekran va Ergonomika Talablari
1. **Ekran O'lchamlari va Masshtablash**:
   - Asosiy maqsadli o'lcham: **1280x800** (10-12 dyuymli avtomobil displeylari, 16:10 nisbat).
   - Moslashuvchan (responsive) qo'llab-quvvatlanadigan o'lchamlar: **1024x600** (7-10 dyuymli kompakt monitorlar) va **1920x1080** (Full HD yirik monitorlar).
   - Barcha o'lchamlar `Theme.qml` orqali boshqariladi, qattiq piksel qiymatlari (magic numbers) taqiqlangan.
2. **Tugmalar va Sensorli Aloqa**:
   - Avtomobil harakatlanayotganda va tebranayotganda haydovchi oson bosishi uchun minimal tugma o'lchami **96x72 px**, tugmalar oralig'i **>= 24 px**.
   - Tasodifiy ikki marta bosishdan himoya (debounce time: 300 ms).
   - Bosilganda vizual o'zgarish (highlight/ripple) va engil audio/vizual javob beriladi.
3. **Raqamli Klaviatura (PasswordPad)**:
   - Avtomobilda tashqi jismoniy klaviatura bo'lmaydi. Shu sababli Sozlamalar bo'limi uchun katta sensorli raqamli klaviatura (on-screen keypad) to'g'ridan-to'g'ri interfeysning o'ziga qurilgan.
   - Ketma-ket 3 marta noto'g'ri PIN kiritilsa, tizim 30 soniyaga vaqtincha bloklanadi.

---

## 2. Kontrast va Ko'rish Xavfsizligi (Safety & Contrast)
1. **WCAG AA va AAA Standartlari**:
   - To'g'ridan-to'g'ri quyosh nuri tushganda va tunda haydovchining ko'zini qamashtirmaydigan yuqori kontrastli qorong'u/neytral palitra (`#0F172A` Slate/Navy fon).
   - Matnlar va fon orasidagi kontrast nisbati kamida **7:1**.
2. **Rangning Yolg'iz Emasligi (Accessible Indicators)**:
   - Ranglar faqat qo'shimcha ma'lumot beradi: har doim **Ikonka + Matn + Rang** birgalikda qo'llaniladi (rang ajrata olmaydiganlar yoki quyosh nuri tufayli rang xiralashgan holatlar uchun).
3. **Typography**:
   - Asosiy matnlar: `>= 22 px`.
   - Sarlavhalar: `>= 36 px`.
   - TEST ACTIVE ekranidagi tezlik va vaqt: `>= 72 px` (haydovchi bir qarashda ko'ra oladigan o'lcham).

---

## 3. UI va Backend Chegarasi (Zero Business Logic in UI)
1. **BackendBridge Interfeysi**:
   - UI hech qachon jarima ballarini hisoblamaydi, PASS/FAIL qarorini qabul qilmaydi yoki testni tugatishga o'zicha ruxsat bermaydi.
   - UI faqat `BackendBridge` signallarini tinglaydi va foydalanuvchi buyruqlarini chaqiradi.
2. **Tugmalar Holati**:
   - Masalan, `[TESTNI YAKUNLASH]` tugmasining faolligi UI tomonidan emas, backend'dan keluvchi `finishReady(bool)` signali orqali boshqariladi.
3. **Aloqa Uzilishi va Tiklanishi (Resilience)**:
   - Agar backend bilan aloqa uzilsa, UI qulab tushmaydi ("Aloqa tiklanmoqda..." overlay ko'rsatiladi).
   - Aloqa tiklanganda UI backend'dan joriy holatni so'rab, o'sha paytdagi to'g'ri ekranga (masalan, TEST_ACTIVE) qaytadi. Test hisobi yo'qolmaydi.
4. **100% Offline va Lokal Resurslar**:
   - Hech qanday Google Fonts, CDN yoki internetdan yuklanadigan rasm/ikonka yo'q. Barcha resurslar (SVG vektorlar, i18n JSON fayli) repo ichida lokal saqlanadi.
