# ASOSIY FARAZLAR VA LOYIHA ME'YORLARI (ASSUMPTIONS.md)

Ushbu hujjat "Standalone 4-Camera Offline AI Driving Training & Evaluation System" bo'yicha qabul qilingan arxitektura va texnik farazlarni belgilaydi.

## 1. 100% Offline va Standalone Muhit
- Dastur mutlaqo internetga chiqmaydi. Runtime davomida hech qanday tashqi HTTP/HTTPS/WebSocket yoki telemetriya chaqiruvlari mavjud emas.
- Barcha bog'liqliklar (wheel'lar, modellar, shriftlar, TTS ovoz modeli) mahalliy diskda saqlanadi.
- 1 ta avtomobil = 1 ta sanoat mini-kompyuteri (Intel i7/i9 yoki Jetson Orin) + 1 ta SQLite ma'lumotlar bazasi (WAL rejimida) + 1 ta NVMe SSD.
- Avtomobillar o'rtasida tarmoq sinxronizatsiyasi yo'q. Mashinalar faqat `config/car.yaml` dagi `car_id` va `config/calibration/` papkasidagi kalibrovka parametrlari orqali farqlanadi.

## 2. Imtihon Metodikasi va Qoidalar (rules.yaml)
- Rasmiy metodika tasdiqlangunga qadar namunaviy qoidalar kodi, ballari va matnlari o'rnatildi.
- Barcha qoidalar `config/rules.yaml` faylida markazlashgan va yagona manba (Single Source of Truth) hisoblanadi.
- Har bir qoidaning pasportida:
  - `code`: Qoida kodi (masalan, `SEATBELT_UNFASTENED`, `CONE_TOUCH`, `STOP_LINE_VIOLATION`, `CRITICAL_COLLISION`, `SPEED_EXCEEDED`, `HILL_ROLLBACK`, `INDICATOR_MISSED`, `PARKING_OUT_OF_BOUNDS`)
  - `title`: Qisqa nomi
  - `screen_text`: Monitorda chiqadigan matn
  - `voice_file`: audio/uz/ ichidagi audio fayl nomi (.wav)
  - `voice_text`: Ovozli o'qiladigan matn
  - `penalty`: Jarima bali (butun son)
  - `critical`: bool (True bo'lsa test darhol to'xtatiladi)
  - `exercise_binding`: Qaysi mashq(lar)da amal qilishi (bo'sh bo'lsa barcha mashqlarda)
- TODO: Rasmiy metodika va standart reglament taqdim etilganda, kodga tegmasdan faqat `rules.yaml` yangilanadi.

## 3. Scoring (Baholash) va Jarimalar
- Boshlang'ich ball: `start_score = 100` (config orqali o'zgartiriladi).
- PASS sharti: `final_score >= pass_score` (standart: 80) VA `critical_violations_count == 0`.
- Agar bironta `critical == True` qoidabuzarlik tasdiqlansa, test darhol `CRITICAL_VIOLATION` -> `TERMINATED` holatiga o'tadi va natija qat'iy **FAIL** bo'ladi.
- Precision tamoyili: AI detektori yoki sensor ishonchlilik darajasi `min_confidence` dan past bo'lsa yoki ketma-ket tasdiqlovchi kadrlar yetarli bo'lmasa, jarima hisoblanmaydi! Hodisa `SUSPECT` holatida qayd etiladi va inspektor ko'rishi uchun ajratiladi.

## 4. Dedup va Cooldown (Dublikatga Qarshi Himoya)
- Bitta uzluksiz xato (masalan, haydovchi 20 kadr davomida konusga tegib turishi yoki to'xtash chizig'ida 5 soniya turishi) aynan bitta hodisa sifatida baholanadi.
- Event holat mashinasi: `CANDIDATE` -> `CONFIRMED` -> `COOLDOWN`.
- Har bir qoida uchun `debounce_frames` (tasdiqlash uchun ketma-ket kadrlar soni) va `cooldown_seconds` (bir xil qoida qayta takrorlanguncha kutish vaqti) `rules.yaml` va `config.yaml` da belgilangan.

## 5. Uskunalar va Ma'lumot Oqimlari
- 4 ta kamera: `FRONT` (old), `REAR` (orqa), `LEFT` (chap ko'zgu/bort), `RIGHT` (o'ng ko'zgu/bort).
- Sensorlar: GPS/GNSS (koordinata, geotezlik), IMU (akselerometr, giroskop, orqaga sirg'alish/qiya burilish burchaklari), OBD-II (dvigatel aylanishi, g'ildirak tezligi, kamar holati, qo'l tormozi).
- Simulyatsiya rejimida (`--simulate`): video fayllar va soxta telemetriya generatori orqali to'liq tizim laboratoriya kompyuterida 100% ishlaydi.

## 6. Xavfsizlik va Kiosk Rejimi
- UI PySide6 (Qt) asosida kiosk rejimida ochiladi (Fullscreen, WindowStaysOnTopHint, Alt+Tab / Alt+F4 bloklangan).
- Sozlamalar va administrator bo'limi SHA-256 bilan heshlangan parol orqali himoyalanadi.
- Barcha dalillar (rasm, video) va test natijalari SHA-256 xesh zanjiri (hash chaining) bilan himoyalangan bo'lib, SQLite bazasidagi yozuvlarni tashqaridan qo'lda o'zgartirib bo'lmaydi.
