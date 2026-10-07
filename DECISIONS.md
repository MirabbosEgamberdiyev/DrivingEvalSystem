# ARXITEKTURA VA LOYIHA QARORLARI (DECISIONS.md)

Ushbu hujjat "Offline 4-Camera AI Driving Training & Evaluation System" mahsulotining barcha asosiy texnik, arxitekturaviy, xavfsizlik va ko'p tillilik qarorlarini, ularning sabablarini va muqobillarini tushuntiradi.

---

## 1. Operatsion Tizim va Tarqatish: Windows Asosiy, Linux Zaxira (v1 vs v4 Ziddiyati)

- **Kontekst**: Tizim v1 da NVIDIA Jetson / Ubuntu / systemd / SSD disk obrazi sifatida tasavvur qilingan. v4 da esa erkin tarqatiladigan, foydalanuvchi o'z kompyuteriga o'rnatadigan mahsulot talab qilindi.
- **Qaror**:
  - **Asosiy platforma**: Windows 10/11 x64. O'rnatuvchi Inno Setup + Nuitka orqali yagona `.exe` paket qilinadi.
  - **Avtostart va Xizmat**: Windows muhitida tizim `Windows Service` yoki `Task Scheduler` (On Logon) orqali avtomatik ishga tushiriladi.
  - **Kiosk rejimi**: Windows Shell cheklovlari (Win+D, Alt+Tab, Task Manager cheklovlari guruh siyosati/registry orqali) ixtiyoriy yoqiladi.
  - **Linux / Jetson**: Ikkinchi darajali platforma sifatida saqlanadi (`systemd` unit va `.deb` paketi keyingi bosqichda sinxronlanadi).

---

## 2. GPU Talablari va AI Inference Dvigateli

- **Kontekst**: Foydalanuvchilar har xil kompyuterlarga ega (NVIDIA RTX, GTX, AMD Radeon, Intel Iris Xe yoki faqat CPU).
- **Qaror**:
  - **Inference Dvigateli**: ONNX Runtime (C++ / Python API).
  - **Ijro Provayderlari (Execution Providers)** ustuvorlik tartibi:
    1. `CUDAExecutionProvider` / `TensorRTExecutionProvider` (NVIDIA RTX/GTX, eng yuqori FPS va eng past latency: <15 ms).
    2. `DirectMLExecutionProvider` (Windows DirectX 12 orqali AMD, Intel GPU va noutbuklar uchun).
    3. `CPUExecutionProvider` (Faqat sinov va favqulodda rejim, FPS < 10 bo'lsa aniq ogohlantirish beriladi).
  - **Minimal Apparat Talablari**:
    - CPU: 6-yadro (Intel Core i5 10-avlod / AMD Ryzen 5 3600 yoki yuqori).
    - RAM: 16 GB DDR4/DDR5.
    - GPU: NVIDIA GTX 1660 Ti / RTX 3050 (4 GB VRAM) yoki DirectML qo'llab-quvvatlovchi 6 GB VRAM GPU.
    - Disk: NVMe SSD (kamida 50 GB bo'sh joy).
  - **Gating**: Agar pre-check vaqtida GPU aniqlanmasa yoki inference kechikishi $\ge 100$ ms bo'lsa, `ASSESSMENT` (rasmiy imtihon) rejimi boshlanishi **BLOKLANADI**. `TRAINING` rejimida esa past FPS haqida katta ogohlantirish bilan ruxsat etiladi.

---

## 3. Kameralar va USB Bandwidth Bottleneck Muammosi

- **Kontekst**: 4 ta USB kamerani (1920x1080 @ 30 FPS) bitta USB 2.0 yoki hatto USB 3.0 host kontrolleriga ulaganda, kontrollerning izoxron (isochronous) o'tkazuvchanligi to'lib qoladi va kameralar o'chib qoladi.
- **Qaror**:
  1. **USB Host Controllerlarni tekshirish**: Setup Wizard va Pre-check paytida Windows SetupAPI / WMI orqali har bir kameraning qaysi USB Controller (Root Hub) ga ulangani tahlil qilinadi. Barcha 4 kamera bitta host controllerga ulangan bo'lsa, ogohlantirish va turli kontrollerlarga ulash bo'yicha vizual ko'rsatma beriladi.
  2. **MJPEG / Pastroq Resolution Siqish**: Kameralar xom YUY2 emas, apparatli MJPEG rejimida ochiladi (o'tkazuvchanlik 10 barobargacha kamayadi).
  3. **IP / RTSP Kameralar**: Standart Ethernet orqali ishlovchi PoE RTSP kameralar (masalan Hikvision, Dahua) to'liq qo'llab-quvvatlanadi (avtomobil routeri/switch orqali).
  4. **Setup Wizard Bandwidth Testi**: Wizard barcha 4 kamerani 10 soniya davomida bir vaqtda 30 FPS da o'qib, kadr yo'qolishini (dropped frames) o'lchaydi. Kadr tushishi >5% bo'lsa, ogohlantiradi.
  5. **Sinalgan Kameralar Ro'yxati (`config/tested_cameras.yaml`)**:
     - "TASDIQLANGAN (Certified)" va "SINALMAGAN (Unverified)" holatlari ajratiladi.

---

## 4. 360 Tayyor Panoramik Tizimlarni Rad Etish

- **Kontekst**: Bozorda avtomobil uchun tayyor 360 gradusli kamerani bitta video qilib beruvchi arzon bloklar bor.
- **Qaror**:
  - Tayyor 360 bloklar qat'iyan man etiladi, chunki:
    1. Ular xom kadr sifatini yo'qotadi va buzib (distortion) ko'rsatadi.
    2. Obyektni aniqlash (konus, piyoda, chiziq) alohida frontal va yon kameralarning to'liq pikselli o'lchamini talab qiladi.
    3. Mashina ichida mustaqil kalibrovka (intrinsic/extrinsic) qilib bo'lmaydi.
  - Tizim faqat 4 ta alohida xom oqimli kameradan foydalanadi va zarurat bo'lganda bird's-eye ko'rinishni dasturning o'zi mustaqil hisoblaydi.

---

## 5. Sensorlar (GPS, OBD-II, IMU): Required vs Optional va Fallback

- **Kontekst**: Ba'zi avtomobillarda OBD-II porti nostandart yoki GPS signali poligon binolari orasida zaif bo'lishi mumkin.
- **Qaror**:
  - Konfiguratsiyada har bir sensor aniq belgilanadi:
    - `sensors.gps.required: bool`
    - `sensors.imu.required: bool`
    - `sensors.obd.required: bool`
  - **Zaxira (Fallback)**: Agar optional sensor mavjud bo'lmasa, **Vizual Odometriya (Visual Odometry)** va kameralar orqali tezlik hamda harakat hisoblanadi.
  - **UI da ko'rsatish**: HUD ekranda "ODOMETRY: VISUAL ESTIMATE (PAST ANIKLIK)" ko'rsatiladi.
  - **Gating**: Agar `required: true` qilingan sensor uzilsa, test boshlanishi darhol bloklanadi.

---

## 6. Litsenziyalash va Aktivatsiya (Offline Xavfsizlik va Python Cheklovlari)

- **Halol Xulosa (Brutal Honesty)**: Python dasturini Nuitka yoki pyinstaller bilan yig'ganda ham, o'ta tajribali teskari muhandis (reverse engineer) RAM yoki dekompilyatsiya orqali kodni ochishi mumkin.
- **Amaliy Ko'p Qatlamli Himoya**:
  1. **Asimmetrik Kriptografiya (Ed25519)**:
     - Litsenziya kodi faqat muallifning maxfiy kaliti bilan imzolanadi. Dasturda faqat ochiq kalit (public key) joylashgan.
     - Soxta litsenziya kodi yasash matematik jihatdan imkonsiz ($2^{255}-19$).
  2. **Tolerant Machine ID (Apparat bog'lash)**:
     - CPU ID, Motherboard UUID, Primary NVMe Disk Serial, GPU PCI ID dan hash olinadi.
     - Bitta komponent o'zgarganda (masalan yangi videokarta qo'yilganda) litsenziya darhol kuyib ketmaydi: 4 tadan kamida 3 tasi mos kelsa yaroqli deb hisoblanadi (kvorum).
  3. **Vaqtni orqaga qaytarishdan himoya (Anti-Clock-Tampering)**:
     - Har bir test sessiyasi va audit yozuvining oxirgi ko'rilgan vaqti DB da SHA-256 zanjirida saqlanadi. Agar tizim soati orqaga surilsa, litsenziya tekshiruvi xato beradi va bloklanadi.
  4. **Nuitka Binary Compilation**:
     - Python kod C++ ga o'girilib, strip qilingan mashina kodi (`.exe`) sifatida kompilyatsiya qilinadi.
  5. **Admin License Generator**:
     - Foydalanuvchilarga berilmaydigan, faqat loyiha egasida bo'ladigan alohida dastur.

---

## 7. Poligon Standartlari va Kalibrovka

- **Qaror**:
  - AI modellari faqat standart o'lchamdagi belgilarga (yo'l chiziqlari kengligi 10-15 sm, konuslar balandligi 50-75 sm, to'xtash chizig'i 40 sm) o'rgatiladi.
  - Setup Wizard'da poligon mashqlari zonalarini belgilash (GPS bounding box yoki vizual markerlar) amalga oshiriladi.
  - Hujjatlarda va EULA da aniq yoziladi: "Tizim faqat tasdiqlangan va sertifikatlangan poligon chizmalarida 100% aniqlikni kafolatlaydi".

---

## 8. Rasmiy Imtihon vs O'quv Rejimlari (TRAINING vs ASSESSMENT)

- **Qaror**:
  - **ASSESSMENT (Rasmiy Imtihon)**:
    - Barcha majburiy komponentlar, 4 kamera, GPU, audio to'plami 100% talab qilinadi.
    - Shubhali (SUSPECT) hodisalar alohida inspektor tekshiruviga yuboriladi.
    - Qoida pasporti faqat tasdiqlangan rasmiy metodikaga mos kelishi shart.
  - **TRAINING (O'quv Mashg'uloti)**:
    - Studentga darhol xatoni tushuntirish va o'rgatish yoqilgan.
    - Sensorlar bo'yicha yumshoqroq cheklovlar.
  - Hozirgi qoidalar rasmiy metodika kelguncha "NAMUNA (TODO: rasmiy metodika bilan almashtirilsin)" deb belgilanadi. O'zimizdan rasmiy nom to'qilmaydi.

---

## 9. Shaxsiy Ma'lumotlar va Maxfiylik

- **Qaror**:
  - Dastur ishga tushganda nomzod va instruktor uchun rozilik (Consent/EULA) ekrani chiqadi.
  - Haydovchilik nomzodining pasport/F.I.SH ma'lumotlari faqat mahalliy SQLite DB da saqlanadi.
  - Sozlamalarda "Sessiya ma'lumotlarini tozalash / Anonimlashtirish" funksiyasi bo'ladi.
  - Diagnostika zip arxivlariga shaxsiy ma'lumotlar (F.I.SH, fotosuratlar) kiritilmaydi, faqat tizim loglari kiritiladi.

---

## 10. Windows Code Signing va SmartScreen

- **Qaror**:
  - `build_installer.py` skriptida `signtool.exe` chaqiruvi tayyorlab qo'yiladi.
  - Agar signing sertifikati (`.pfx`) bo'lmasa, skript o'rnatuvchini imzosiz yig'adi va aniq ogohlantirish beradi: "Tizim o'rnatuvchisi imzolandi yoki test sertifikat bilan chiqdi. Windows SmartScreen paydo bo'lganda 'Run anyway' bosilishi kerak".

---

## 11. Ko'p Tillilik (i18n/l10n) Bo'yicha Qat'iy Qarorlar

### a) BCP-47 Til Kodlari va Zanjir
- **Kodlar**: `uz-Latn`, `uz-Cyrl`, `ru`.
- **Fallback zanjiri**:
  - `uz-Cyrl` -> `uz-Latn` -> XATO (Dev rejimida exception, Release buildda to'xtash).
  - `ru` -> `uz-Latn` -> XATO.
- **Jimgina boshqa tilga o'tib ketish (Silent Fallback) TAQIQLANGAN**: Agar biror tilda kalit yetishmasa, `check_translations.py` buildni to'xtatadi.

### b) Rus Tili Matnlari Kengayishi (+20-35%)
- Rus tili matnlari o'zbek lotiniga qaraganda ancha uzun.
- UI Layout qoidasi: Hech qanday qat'iy (fixed) pikselli matn qutilari bo'lmaydi. Barcha komponentlar `implicitWidth` va dinamik wrapping bilan ishlaydi. 3 tildagi eng uzun matnlar bo'yicha avtomatik test o'tkaziladi.

### c) Ko'plik Shakllari (Pluralization)
- Rus tilida 3 ta ko'plik shakli mavjud (`one`, `few`, `many`):
  - 1 балл (one)
  - 2, 3, 4 балла (few)
  - 5, 6... баллов (many)
- O'zbek tilida: son bilan ot doimo birlikda keladi ("1 ball", "5 ball").
- Kodda hech qachon "N ball(lar)" yoki "N балл(-ов)" kabi qo'pol qochirmalar bo'lmaydi. `plural(count, form)` funksiyasi CLDR plural qoidalari asosida ishlaydi.

### d) Ovozli Xabar Arxitekturasi (Segment vs To'liq Jumla)
- **Qaror**: **To'liq jumla fayli (Full Phrase)** yondashuvi tanlandi!
  - *Sabab*: Segmentlardan yig'ilganda (masalan "Chiziq bosish" + "o'n" + "ball") intonatsiya robotik bo'lib qoladi va rus tilida kelishik/jins/ko'plik mosligi buziladi ("двадцать" vs "двадцать один балл" vs "двадцать две секунды").
  - Har bir qoidabuzarlik uchun: `audio/{lang}/{code}.wav` to'liq ifodalangan jumla bo'ladi (masalan "Stop chizig'ida to'xtamadingiz. Yigirma ball jarima.").
  - Diktor uchun to'liq matnlar ro'yxati avtomatik ravishda `audio_scripts_{lang}.txt` fayliga chiqariladi.

### e) Offline TTS Zaxirasi
- O'zbek kirill va lotin tillari uchun yuqori sifatli, tabiiy offline ONNX/TTS modellari (ayniqsa mobil/embedded qurilmalarda) yetarli darajada ravon emas.
- Shuning uchun **tizim sifatli oldindan yozilgan `.wav` fayllariga tayanadi**.
- Agar biror `.wav` fayl diskda yetishmasa: Tizim ekran xabari + maxsus audio ogohlantirish chimesi beradi va pre-check buni "Ovoz to'plami to'liq emas" deb qayd etadi.
- ASSESSMENT rejimida ovoz to'plami 100% to'liq bo'lmasa, imtihon boshlanishi **BLOKLANADI**.

### f) Lotin <-> Kirill Transliteratsiyasi
- Rasmiy metodika va ovoz matnlari uchun avtomatik transliteratsiya faqat qoralama (`draft`) vositasi sifatida ishlatiladi.
- Avtomatik transliteratsiya qilingan har bir yozuv `reviewed: false` va `NEEDS_REVIEW` deb belgilanadi. Faqat mutaxassis ko'rib chiqqach, `reviewed: true` qilinadi.

### g) Tarjima Holati va Validatsiya
- Har bir tarjima yozuvi quyidagi tuzilishga ega:
  ```json
  "key": {
    "text": "Matn",
    "reviewed": true,
    "reviewer": "linguist_uz",
    "updated_at": "2026-10-06"
  }
  ```
- `check_translations.py` skripti:
  1. 3 tildagi barcha kalitlar tengligini;
  2. Barcha parametrlar mosligini (`{0}`, `{code}`);
  3. `reviewed: false` yoki `TODO` yozuvlar sonini tekshiradi.

### h) Foydalanuvchi Ma'lumotlari (Nomzod Ismi)
- Foydalanuvchi kiritgan ma'lumotlar o'zgartirilmaydi va majburiy transliteratsiya qilinmaydi.
- Qidiruv tizimi esa har ikkala alifboga nisbatan tolerant ishlaydi (lotincha qidiruv kirillcha kiritilgan nomni topadi).

### i) Ekran Klaviaturasi
- Sensorli monitor uchun 3 ta maket:
  1. `uz-Latn`: standart lotin + `oʻ`, `gʻ`, `sh`, `ch`.
  2. `uz-Cyrl`: to'liq o'zbek kirill alifbosi + `ў`, `қ`, `ғ`, `ҳ`.
  3. `ru`: to'liq rus alifbosi (`ё`, `ъ`, `ь`, `ы`, `э`).
- Dastur tili o'zgarganda klaviatura maketi avtomatik moslashadi, foydalanuvchi xohlagan paytda maketni qo'lda ham almashtira oladi.

### j) Shriftlar va Glif Qamrovi
- Barcha lotin, kirill va maxsus o'zbek gliflarini o'z ichiga olgan lokal TTF/OTF shrift repo ichiga joylashtiriladi.
- PDF hisobotlarga ham ushbu shrift to'liq embed qilinadi. Glif yetishmasligi (tofu/□) avtomatlashtirilgan test bilan tekshiriladi.

### k) Sana, Vaqt va Qoida Kodlari
- Qoida kodlari (`CONE_TOUCH`, `STOP_LINE_FAIL`, `SEATBELT_OFF`) tildan qat'iy nazar tildan neytral (universal ID) bo'lib qoladi.
- DB va dalil metadatasida faqat ushbu universal kodlar saqlanadi.
- Sanalar va raqamlar locale bo'yicha formatlanadi (`DD.MM.YYYY` vs `YYYY-MM-DD`).

### l) Til Tanlash va Sessiyaga Muhrlash
- Birinchi ishga tushirishda aktivatsiyadan oldin foydalanuvchidan til so'raladi.
- Har bir ekranda (TEST_ACTIVE dan tashqari) til almashtirish tugmasi mavjud.
- Nomzod imtihonni boshlaganda (`startTest`), joriy tanlangan til test sessiyasiga yoziladi (`test_sessions.language`).
- TEST_ACTIVE paytida til o'zgartirish qat'iyan man etiladi.
- Natija va dalillar aynan sessiya tilida shakllantiriladi, lekin keyinchalik boshqa tilda qayta eksport qilish imkoniyati saqlanadi.

### m) Inno Setup O'rnatuvchisi
- O'rnatuvchi 3 tilda ishlaydi:
  - `ru`: Inno Setup standart `Russian.isl`.
  - `uz-Latn`: maxsus yozilgan `UzbekLatin.isl`.
  - `uz-Cyrl`: maxsus yozilgan `UzbekCyrillic.isl`.
- EULA va litsenziya matni ham 3 tilda taqdim etiladi.

---

## 12. Audit Natijalari Bo'yicha Qabul Qilingan Xavfsizlik va Arxitektura Qarorlari

1. **Vendor Ed25519 Maxfiy Kaliti Xavfsizligi (SEC-01)**:
   - Dastur kodida yoki git repo ichida maxfiy xususiy kalitlarni (private keys) saqlash mutlaqo taqiqlanadi.
   - `admin_license_gen.py` endi kalitni faqat `DRIVING_EVAL_VENDOR_KEY` muhit o'zgaruvchisidan yoki `--private-key` CLI argumentidan oladi. Repoda qolgan eski kalit bekor qilingan (compromised) deb hisoblanadi.

2. **Admin Autentifikatsiyasi va Audit Jurnali (SEC-02)**:
   - "1234" kabi har qanday backdoor yoki default bypass kodlari olib tashlanadi.
   - Admin PIN xeshlari tuzlangan (salted) PBKDF2-HMAC-SHA256 orqali tekshiriladi.
   - Har bir kirish urinishi (muvaffaqiyatli va muvaffaqiyatsiz) SQLite bazasidagi `admin_audit_log` jadvaliga yoziladi.

3. **Haqiqiy Kriptografik Xesh Zanjiri Tekshiruvi (CRYPTO-01)**:
   - `verify_session_hash_integrity` faqat xesh uzunligini tekshirish bilan cheklanmaydi. U sessiyaning barcha qoidabuzarliklarini xronologik tartibda o'qib, boshlang'ich hashdan zanjirni to'liq qayta hisoblaydi va saqlangan ildiz xeshi (`hash_chain_root`) bilan taqqoslaydi. Bazada bitta qator o'zgartirilsa ham zanjir xatosi aniqlanadi.

4. **Diagnostika Telemetriyasida Soxtalikni Cheklash (DIAG-01)**:
   - Tizim parametrlari (CPU, RAM, Disk) operatsion tizimdan real vaqtda olinadi.
   - Jismoniy sensorlar (GPS, OBD-II, IMU) ulanmagan holatda soxta doimiy sonlar ko'rsatish taqiqlanadi. Sensor uzilgan bo'lsa `DISCONNECTED`, simulyatsiya yoqilgan bo'lsa ekranda `[SIMULATION]` belgisi aniq ko'rsatiladi.

5. **Nomzod Shaxsiy Ma'lumotlarini Himoyalash (PII-01)**:
   - Touchscreen monitor barcha avtomobil yo'lovchilari uchun ko'rinadigan bo'lgani sababli, pasport raqamlari qisman niqoblanadi (`AA****567`). Inspektor rejimi uchun PIN tekshiruvi joriy etiladi.

---

Ushbu qarorlar loyihaning butun arxitekturasi va barcha bosqichlari uchun asos hisoblanadi.

