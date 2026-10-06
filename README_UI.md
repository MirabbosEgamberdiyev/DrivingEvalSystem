# Standalone 4-Camera Offline AI Driving Training & Evaluation System - UI/UX Architecture

Ushbu hujjat avtomobil ichidagi sensorli monitor uchun ishlab chiqilgan **Qt 6 / QML (PySide6)** interfeysining texnik arxitekturasi, dizayn tizimi, ekranlar va foydalanish bo'yicha to'liq qo'llanmasidir.

---

## 1. Asosiy Xususiyatlar va Cheklovlar

1. **100% OFFLINE & STANDALONE**:
   - Hech qanday tashqi CDN, onlayn shriftlar, telemetriya yoki tarmoq chaqiruvlari mavjud emas.
   - Barcha SVG ikonkalar (`src/driving_eval/ui_qml/assets/icons/`), matn kataloglari (`i18n/uz.json`) va shriftlar lokal joylashgan.
2. **QAT'IY CHEGARA (UI va Backend orasida)**:
   - UI qatlamida biznes mantiq umuman yo'q. U faqat `BackendBridge` signallarini tinglaydi va foydalanuvchi buyruqlarini chaqiradi.
   - Ikkita to'liq bridge implementatsiyasi:
     - `MockBridge`: deterministik skriptlangan stsenariylar (kamera xatosi va retry, ketma-ket 2 xato, kritik xato, PASS/FAIL, offline uzilish).
     - `RealBridge`: haqiqiy `ExamStateMachine`, `PrecheckService`, `DatabaseRepository` va `EvidenceRecorder` xizmatlariga bog'langan.
3. **SENSORLI MONITOR ERGONOMIKASI**:
   - Asosiy o'lcham: **1280x800** (10-12" monitor).
   - Moslashuvchan qo'llab-quvvatlash: **1024x600** (7-10") va **1920x1080** (15" Full HD).
   - Minimal tugma o'lchami: $\ge 96 \times 72$ px (tebranayotgan mashinada bexato bosish uchun).
   - Tasodifiy ko'p marta bosishdan himoya (350 ms debounce).
   - WCAG AAA / AA kontrast darajalari (quyosh nuri tushganda ham aniq ko'rinadigan yuqori kontrast).

---

## 2. Dizayn Tizimi (`Theme.qml`)

Barcha vizual parametrlar `src/driving_eval/ui_qml/qml/Theme.qml` singletonida markazlashtirilgan:
- **Ranglar**:
  - Orqa fon: `#0B0F19` (chuqur qorong'i)
  - Sirtlar: `#151B28`, `#1F293D`
  - Muvaffaqiyat (Pass / Ready): `#16A34A`
  - Qoidabuzarlik (Error / Fail): `#DC2626`
  - Shubhali (Suspect / Checking): `#D97706`
  - Kritik xato: `#991B1B` (urgent dark red)
- **Shriftlar**:
  - Matn tanasi (Body): $\ge 22$ px (kichik yozuvlar taqiqlangan)
  - Sarlavhalar: $28 - 36$ px
  - HUD Tezlik va Vaqt: $\ge 72$ px (76 px display)
  - O'zbek tili harflari to'liq qo'llab-quvvatlanadi (`oʻ`, `gʻ`, `sh`, `ch`).

---

## 3. Ekranlar va Ishlash Mantiqi

Dastur 9 ta alohida ekranga ega:
1. **HOME EKRANI (`HomeScreen.qml`)**:
   - Tizim nomi, Mashina ID, Qoidalar versiyasi.
   - Agar precheck o'tmagan bo'lsa: `TESTNI BOSHLASH` nofaol, `TIZIMNI TEKSHIRISH` faol.
   - O'ng yuqori burchakda PIN bilan himoyalangan Sozlamalar tugmasi.
2. **PRE-CHECK EKRANI (`PrecheckScreen.qml`)**:
   - 12 ta majburiy komponent holati (4 kamera, drift, AI engine, GPS, IMU, OBD-II, NVMe SSD, SQLite DB, Audio).
   - Agar birortasi nosoz bo'lsa: `TEST START BLOCKED` qizil banneri, aniq sabab va `QAYTA TEKSHIRISH` tugmasi.
3. **SYSTEM READY EKRANI (`SystemReadyScreen.qml`)**:
   - Barcha tizimlar yashil ✅.
   - Ovozli xabar sinxronligi: "Barcha tizimlar tayyor. Harakatni boshlashingiz mumkin."
   - `TESTNI BOSHLASH` tugmasi.
4. **ACTIVE TEST EKRANI (`ActiveTestScreen.qml`)**:
   - **Minimalist HUD**:
     - Yuqorida: "TEST JARAYONDA" va real vaqt hisoblagichi `MM:SS`.
     - O'rtada: Katta tezlik (`18 km/h`) va Joriy mashq nomi (`ZMEIKA`, `ESTAKADA`).
     - Pastda: Jami jarima va Xatolar soni.
   - **Gated Finish Button**:
     - Haydash vaqtida hech qanday chalg'ituvchi tugma yo'q.
     - Faqat mashina finish zonasida to'xtaganda (`finishReady == true`) `TESTNI YAKUNLASH` tugmasi faollashadi.
5. **VIOLATION POPUP (`ViolationPopup.qml`)**:
   - HUD ustiga semi-transparent qatlam sifatida chiqadi.
   - Ketma-ket kelgan qoidabuzarliklar navbat (queue) orqali ketma-ket 3.5 soniyadan ko'rsatiladi (ustma-ust tushmaydi).
   - Kritik xatoda to'q qizil zudlik bilan testni to'xtatish rejimi.
6. **YAKUNIY NATIJA EKRANI (`ResultScreen.qml`)**:
   - Katta PASS (yashil) yoki FAIL (qizil) banneri.
   - Yakuniy ball, ayrilgan jarima, xatolar soni, vaqt.
   - SHA-256 kriptografik tamper-proof xesh.
   - `QOIDABUZARLIKLAR RO'YXATI`, `USB GA EKSPORT`, `ASOSIY EKRAN` tugmalari.
7. **QOIDABUZARLIKLAR RO'YXATI (`ViolationsListScreen.qml`)**:
   - 1-bo'lim: Tasdiqlangan jarimalar (balldan ayrilgan).
   - 2-bo'lim: Shubhali (SUSPECT) hodisalar (inspektor ko'rishi uchun ajratilgan, balldan olinmagan).
   - Har bir hodisada `Dalil` (Evidence) tugmasi.
8. **EVIDENCE KO'RUVCHI (`EvidenceScreen.qml`)**:
   - 4 ta ko'rinish: `before.jpg`, `event.jpg`, `after.jpg`, `event.mp4`.
   - Hodisa metama'lumotlari: vaqt, mashq, tezlik, ishonchlilik foizi.
   - USB ga nusxalash imkoniyati.
9. **SOZLAMALAR EKRANI (`SettingsScreen.qml`)**:
   - Touch PIN pad (4 xonali ekran klaviaturasi).
   - 3 marta noto'g'ri PIN kiritilganda 30 soniyalik xavfsizlik blokirovkasi (`lockout`).
   - Uskunalar holati, `system_logs` audit jurnali, butun bazani USB ga eksport qilish.
10. **OFFLINE UZILISH OVERLAYI (`Main.qml`)**:
    - Agar mahalliy backend daemon uzilsa, ekran darhol `ALOQA TIKLANMOQDA...` rejimiga o'tadi va barcha hisoblar saqlab qolinadi.

---

## 4. Dasturni Ishga Tushirish

### Simulyatsiya Rejimida (Namoyish uchun)
```bash
python -m app --simulate --windowed
```

### Muayyan Stsenariylar bilan Ishga Tushirish
1. **Ikki xato ketma-ket kelishi (Popup navbati testi)**:
   ```bash
   python -m app --simulate --scenario double_violation --windowed
   ```
2. **Kamera nosozligi va qayta tiklash testi**:
   ```bash
   python -m app --simulate --scenario camera_fail --windowed
   ```
3. **Kritik qoidabuzarlik testi**:
   ```bash
   python -m app --simulate --scenario critical_fail --windowed
   ```

### Avtomobil Kiosk Rejimida (Fullscreen)
```bash
python -m app --kiosk
```

### Ekran O'lchamini Belgilash
```bash
python -m app --simulate --windowed --resolution 1024x600
python -m app --simulate --windowed --resolution 1280x800
python -m app --simulate --windowed --resolution 1920x1080
```

---

## 5. Testlar va Skrinshotlar

- Barcha testlarni ishga tushirish:
  ```bash
  pytest tests/ui -v
  ```
- 3 ta rezolyutsiyada generatsiya qilingan skrinshotlar `screenshots/` papkasida saqlangan:
  - `01_home_1024x600.png`, `01_home_1280x800.png`, `01_home_1920x1080.png`
  - `02_precheck_*`
  - `03_system_ready_*`
  - `04_active_test_*`
  - `05_violation_popup_*`
  - `05_result_*`
  - `06_violations_list_*`
  - `07_evidence_*`
  - `08_settings_*`
