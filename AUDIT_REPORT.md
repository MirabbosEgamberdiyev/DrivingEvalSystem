# XOLIS VA QAT'IY AUDIT HISOBOTI (AUDIT_REPORT.md)
**Hujjat sanasi:** 2026-10-07  
**Auditor:** Principal QA/Audit Muhandisi & Tizim Arxitektori  
**Audit maqsadi:** "DrivingEvalSystem" loyihasini 0 dan shubha bilan tekshirish, barcha da'volarni kod, test va vizual dalillar orqali tahlil qilish, kamchiliklarni tasniflash.

---

## 1. IJROIY XULOSA (EXECUTIVE SUMMARY)

Oldingi hisobotlarda loyiha *"100% DONE, 122/122 PASS, 85% coverage, production-ready"* deb e'lon qilingan. Biroq, mustaqil va shubhasiz audit o'tkazilganda ushbu da'volarning bir qismi **haqiqiy emasligi, sun'iy (MOCK) qiymatlar bilan to'ldirilgani yoki jiddiy xavfsizlik teshiklariga egaligi** aniqlandi.

Loyiha arxitekturasi va kod bazasi juda kuchli (PySide6 QML UI, ByteTrack, Sensor Fusion, SQLite WAL, RFC 8032 Ed25519, Inno Setup), biroq haqiqiy transport vositasiga o'rnatishdan oldin **zudlik bilan bartaraf etilishi shart bo'lgan 4 ta KRITIK, 4 ta YUQORI va 3 ta O'RTA darajadagi nuqsonlar** mavjud.

---

## 2. AUDIT STATUSLARINING TAQSIMOTI

Barcha tizimlar quyidagi 5 ta qat'iy standart bo'yicha baholandi:

| Holat | Ta'rif | Soni |
|---|---|---|
| **VERIFIED** | Dalil bilan to'liq ishlayotgani isbotlangan (kod + test + runtime) | 26 ta modul |
| **PARTIAL** | Qisman ishlaydi, UI yoki testda bo'shliqlar mavjud | 6 ta modul |
| **MOCK** | Soxta/qattiq yozilgan qiymatlar bilan ishlaydi, real manbaga ulanmagan | 5 ta modul |
| **MISSING** | Hujjatda aytilgan, lekin kodda yoki repo'da mavjud emas | 2 ta modul |
| **HARDWARE_REQUIRED** | Faqat real avtomobil va jismoniy datchiklar bilan tekshiriladi | 3 ta modul |

---

## 3. TOPILGAN ASOSIY NUQSONLAR VA XAVFSIZLIK MUAMMOLARI

### [SEC-01] CRITICAL: Admin Litsenziya Maxfiy Kaliti Git Repozitoriysiga Qattiq Yozilgan
- **Fayl:** `tools/admin_license_gen.py`, 19-qator.
- **Holat:** `CRITICAL SECURITY LEAK`.
- **Dalil:**
  ```python
  DEFAULT_VENDOR_PRIVATE_KEY_HEX = "bdd0b1a5fdd912b838c5cd6a6d08bc58caa1174c6f6a30df78cd157a1eb53869"
  ```
- **Xavf:** Repozitoriyga kirish huquqiga ega bo'lgan har qanday shaxs ushbu kalit yordamida cheksiz noqonuniy litsenziyalar yaratishi mumkin. RFC 8032 Ed25519 xavfsizlik arxitekturasi butunlay buzilgan.
- **Yechim:** Maxfiy kalit manba kodidan butunlay olib tashlanadi. Kalit faqat muhit o'zgaruvchisi (`DRIVING_EVAL_VENDOR_KEY`) yoki CLI parametri orqali qabul qilinadi. Kalit kompromat qilingan deb belgilanadi va yangilash protsedurasi yoziladi.

---

### [SEC-02] CRITICAL: Admin Ekranida Qattiq Yozilgan Backdoor PIN ("1234") Va Tuzsiz Xesh
- **Fayl:** `src/driving_eval/ui_qml/bridge/real_bridge.py`, 257-qator.
- **Holat:** `CRITICAL SECURITY FLAW`.
- **Dalil:**
  ```python
  if pin_hash == expected_hash or pin == "1234":
  ```
- **Xavf:** Har qanday foydalanuvchi "1234" kodini kiritib admin va sozlash ekraniga kira oladi. PIN xeshi tuzsiz (unsalted) SHA-256 orqali hisoblangan. Kirish urinishlari (muvaffaqiyatli yoki muvaffaqiyatsiz) audit logiga (`admin_audit_log`) yozilmaydi.
- **Yechim:** Backdoor "1234" sharti olib tashlanadi. Tuzli PBKDF2/SHA-256 xeshlash joriy qilinadi. Har bir admin kirish harakati SQLite bazasidagi `admin_audit_log` jadvaliga IP, vaqt va status bilan qayd etiladi.

---

### [CRYPTO-01] CRITICAL: Kriptografik Xesh Zanjirini Soxta Tekshirish (`verify_session_hash_integrity`)
- **Fayl:** `src/driving_eval/db/repository.py`, 427-qator.
- **Holat:** `MOCK / INTEGRITY BYPASS`.
- **Dalil:**
  ```python
  def verify_session_hash_integrity(self, session_id: str) -> bool:
      res = self.get_session(session_id)
      if not res or not res["hash_chain_root"]:
          return False
      return len(res["hash_chain_root"]) == 64  # <--- SOXTA TEKSHIRUV!
  ```
- **Xavf:** Funksiya hodisalar xesh zanjirini (SHA-256 chain) qayta hisoblab chiqmaydi! Agar tajovuzkor bazadagi qoidabuzarliklar yoki ballarni o'zgartirsa, uzunlik 64 bo'lgani uchun tekshiruv har doim `True` qaytaradi. Dalillar yaxlitligi kafolatlanmagan.
- **Yechim:** Funksiyada sessiyaning barcha `violation_events` qatorlarini xronologik tartibda o'qib, boshlang'ich hashdan boshlab zanjir qayta hisoblanadi va saqlangan `hash_chain_root` bilan taqqoslanadi.

---

### [AI-01] HIGH: ONNX Modeli va Runtime Muhitda Yo'q (AI Inference To'liq Mock)
- **Fayl:** `src/driving_eval/ai/onnx_detector.py`, `src/driving_eval/ui/app.py`.
- **Holat:** `MOCK / HARDWARE_REQUIRED`.
- **Dalil:**
  - Virtual muhitda `onnxruntime` paketi o'rnatilmagan (`ModuleNotFoundError`).
  - `data/models/` katalogida bitta ham `.onnx` model fayli yo'q (faqat README.md).
  - `app.py` ichida `RealBridge` har doim `MockDetector(healthy=True)` bilan ishga tushirilgan.
  - Sozlamalar ekranidagi AI telemetriyasi (18.2 ms, 45 FPS) qattiq yozilgan matndir.
- **Yechim:** `onnxruntime` o'rnatilishi hujjatlashtiriladi, model yuklash xatolarida xavfsiz va aniq [MOCK/SIMULATION] belgisi UI'da ko'rsatiladi.

---

### [DIAG-01] HIGH: Diagnostika va Sensor Telemetriyasi Qattiq Yozilgan (Mock Telemetry)
- **Fayl:** `src/driving_eval/ui_qml/bridge/real_bridge.py`, 337–348-qatorlar.
- **Holat:** `MOCK`.
- **Dalil:**
  ```python
  return {
      "cpu_usage_pct": 25.0,        # Qattiq yozilgan!
      "ram_usage_pct": 35.0,        # Qattiq yozilgan!
      "system_temp_c": 45.0,        # Qattiq yozilgan!
      "camera_latency_ms": 16.0,    # Qattiq yozilgan!
      "gps_fix": True,              # Qattiq yozilgan!
      "gps_satellites": 14,         # Qattiq yozilgan!
      "obd_rpm": 850,               # Qattiq yozilgan!
      "imu_pitch_deg": 0.5,         # Qattiq yozilgan!
      "disk_free_gb": round(free_gb, 1), # Faqat shu real!
  }
  ```
- **Xavf:** Foydalanuvchi sensorlar haqiqatda ishlayapti deb o'ylaydi, holbuki datchiklar uzilgan bo'lsa ham tizim doim yashil telemetriya ko'rsatadi.
- **Yechim:** CPU/RAM va harorat real tizim manbalaridan (psutil / ctypes) o'qiladi. Sensorlar ulanmagan bo'lsa, status `DISCONNECTED` va `0` ko'rsatiladi, simulyatsiya rejimida esa `[SIMULATION]` belgisi chiqadi.

---

### [CALIB-01] HIGH: BEV Kalibrovka Siljishi (Drift) Mock Qiymat
- **Fayl:** `src/driving_eval/wizard/setup_service.py`, 284–291-qatorlar; `SettingsScreen.qml`, 646-qator.
- **Holat:** `MOCK`.
- **Dalil:** Drift qiymatlari qattiq `1.8 cm` va `2.4 cm` deb belgilangan. QML ichida `"2.1 sm"` va `"98.4%"` matnlari o'zgarmas qilib yozilgan.
- **Yechim:** Dinamik hisoblangan yoki datchik holatiga asoslangan haqiqiy drift hisobi ko'rsatiladi.

---

### [PII-01] HIGH: Nomzod Shaxsiy Ma'lumotlari (Passport) Himoyalanmagan
- **Fayl:** `src/driving_eval/ui_qml/qml/screens/HomeScreen.qml`.
- **Holat:** `PARTIAL / PRIVACY FLAW`.
- **Dalil:** Bosh ekranda avtomobilda o'tirgan har qanday odam "Inspektor" yoki "Natijalar" tugmasini bosib, nomzodning to'liq pasport raqamini ko'rishi mumkin.
- **Yechim:** Pasport raqamini qisman niqoblash (`AA****567`) va inspektor bo'limiga kirish uchun PIN kod so'rash joriy etiladi.

---

### [AUDIO-01] MEDIUM: Ovozli WAV Fayllari Haqiqiy Diktor Ovozi Emas
- **Fayl:** `data/audio/uz-Latn/`, `data/audio/uz-Cyrl/`, `data/audio/ru/`.
- **Holat:** `MOCK / NEEDS_HUMAN_REVIEW`.
- **Dalil:** Barcha 36 ta `.wav` fayllari baytma-bayt bir xil (105,884 bayt) sun'iy generatsiya qilingan bitta chastotali signal (sinusoida).
- **Yechim:** Hujjatlarda bu holat ochiq tan olinadi (`VOICE_TODO.md` tuziladi) va professional diktor yozuvlari uchun skript tayyorlanadi.

---

### [I18N-01] MEDIUM: Tarjimalarning "reviewed: True" Holati Sun'iy O'rnatilgan
- **Fayl:** `data/translations/*.yaml`.
- **Holat:** `NEEDS_HUMAN_REVIEW`.
- **Dalil:** `check_translations.py` skriptida barcha 292 ta kalit avtomatlashtirilgan tarzda `reviewed: True` va `reviewer: metodist_uz` qilib belgilangan, haqiqiy tilshunos ekspert ko'rigidan o'tmagan.
- **Yechim:** `TRANSLATION_REVIEW.md` faylida ko'rikdan o'tmagan kalitlar alohida ko'rsatiladi.

---

### [I18N-02] MEDIUM: QML Ichida Qattiq Yozilgan Matnlar (Tarjimaga Ulanmagan)
- **Fayl:** `SettingsScreen.qml`, `SetupWizardScreen.qml`, `EvidenceScreen.qml`.
- **Holat:** `PARTIAL`.
- **Dalil:** Sozlamalar va usta ekranlarida 40 dan ortiq yozuvlar `Theme.tr()` orqali emas, o'zbek tilida qattiq yozilgan.
- **Yechim:** Barcha qattiq matnlar `Theme.tr(...)` funksiyasiga ulanadi va 3 ta til katalogiga kiritiladi.

---

### [TEST-01] MEDIUM: Test To'plamida Mutatsiya Zaifliklari va Sayoz Tekshiruvlar
- **Fayl:** `tests/unit/test_rule_engine_and_scoring.py`, `tests/ui/test_button_states.py`.
- **Holat:** `PARTIAL`.
- **Dalil:** Mutatsiya testida `ScoringEngine.is_passing` metodi har doim `False` qaytarganda ham `test_rule_engine_and_scoring.py` yashil o'tdi, chunki ijobiy o'tish sharti (`assert is_passing is True`) tekshirilmagan edi.
- **Yechim:** Yangi qat'iy mutatsiya testlari va o'tish shartlari tekshiruvi qo'shiladi.

---

## 4. TIZIMLARNING TO'LIQ AUDIT JADVALI

| Tizim / Modul | Talab | Amaldagi Holat | Xulosa |
|---|---|---|---|
| **App State Machine** | 3 holat: UNLICENSED, SETUP_REQUIRED, READY | DB log, qat'iy o'tishlar, xatoliklar tekshirilgan | **VERIFIED** |
| **Exam State Machine** | 6 holat: IDLE, PRECHECK, ACTIVE, SUSPECT, COMPLETED, ABORTED | Power-loss tiklash, gating, tranzitsiyalar tekshirilgan | **VERIFIED** |
| **SQLite Baza** | WAL mode, migratsiyalar, foreign keys | SQLite 3 WAL, 3 ta migratsiya to'liq ishlaydi | **VERIFIED** |
| **Hash Chain Integrity** | SHA-256 zanjir orqali soxtalashtirishni aniqlash | `len() == 64` tekshirmoqda, zanjir qayta hisoblanmaydi | **MOCK / CRITICAL** |
| **Ed25519 Litsenziya** | Pure Python RFC 8032 raqamli imzo | Matematik imzo tekshirish to'liq ishlaydi | **VERIFIED** |
| **Vendor Private Key** | Maxfiy kalit xavfsizligi | `admin_license_gen.py` da plaintext ochiq turibdi | **CRITICAL LEAK** |
| **Admin Autentifikatsiya** | Xavfsiz PIN va audit log | "1234" backdoor mavjud, tuzsiz xesh | **CRITICAL FLAW** |
| **ByteTrack Tracking** | 2-bosqichli kuzatuv, IoU, EMA tekislash | Kalman/EMA, ID saqlash, testlar yashil | **VERIFIED** |
| **Sensor Fusion** | IMU + GPS + OBD + Visual Odometry | Dead reckoning, estakada rollback to'liq ishlaydi | **VERIFIED** |
| **ONNX Detector** | GPU/DirectML/CPU obyekt deteksiyasi | Model (.onnx) yo'q, onnxruntime o'rnatilmagan | **MOCK** |
| **Diagnostika Telemetriya**| Real CPU, RAM, Harorat, GPS, OBD ko'rsatkichlari | Qattiq yozilgan doimiy sonlar (25%, 35%, 45C) | **MOCK** |
| **Qoidalar Dvigateli** | 9 qoida plagini, debounce, cooldown | 20 kadr -> 1 hodisa, jarimasiz SUSPECT ishlaydi | **VERIFIED** |
| **Dalillar Tizimi** | Ring buffer, composite JPEG, metadata JSON | 4 kamera kadrlari birlashishi, xesh zanjiri | **VERIFIED** |
| **Audio Xizmati** | 3 tilda diktor ovozi (.wav) | Barcha 36 ta fayl 105KB li bir xil signal (ton) | **MOCK** |
| **Lokalizatsiya (i18n)** | uz-Latn, uz-Cyrl, ru to'liq paritet | QML da 40+ qattiq matnlar, ekspert ko'rigi yo'q | **PARTIAL** |
| **Ekran Klaviatura** | 3-maketli sensorli klaviatura | Lotin, Kirill, Rus maketlari to'liq ishlaydi | **VERIFIED** |
| **PDF & CSV Hisobot** | ReportLab Unicode shrift, UTF-8 BOM CSV | O'zbek lotin, kirill va rus tillarida to'liq | **VERIFIED** |
| **Inno Setup & Nuitka** | Windows installer, 3-tilli o'rnatuvchi | .isl fayllari, build scriptlari mavjud | **PARTIAL** (ISCC kerak) |

---

## 5. TUZATISH REJASI (ACTION PLAN)

Audit xulosasiga binoan, kod bazasini quyidagi tartibda to'g'rilashga kirishiladi:
1. **SEC-01**: `admin_license_gen.py` dan maxfiy kalitni olib tashlash va xavfsiz parametr/muhit o'zgaruvchisiga o'tkazish.
2. **SEC-02**: `real_bridge.py` dagi "1234" backdoor PIN ni olib tashlash, xavfsiz tuzli xesh va `admin_audit_log` yozuvini kiritish.
3. **CRYPTO-01**: `verify_session_hash_integrity` funksiyasida haqiqiy SHA-256 zanjirini rekursiv/ketma-ket hisoblab tekshirish algoritmini yozish va unga test qo'shish.
4. **DIAG-01**: Diagnostikada real tizim (CPU/RAM/Disk) ko'rsatkichlarini olish, sensorlar yo'qligida aniq `DISCONNECTED` yoki `[SIMULATION]` ko'rsatish.
5. **PII-01**: Nomzod pasport raqamini niqoblash (`AA****567`) va inspektor ekraniga PIN talab qilish.
6. **I18N-02**: QML fayllaridagi barcha qattiq yozilgan matnlarni `Theme.tr()` ga ulash va kataloglarga kiritish.
7. **TEST-01**: `test_rule_engine_and_scoring.py` va `test_button_states.py` testlariga mutatsiyalarga chidamli mustahkam tekshiruvlar qo'shish.
8. **AUDIO-01**: `VOICE_TODO.md` yo'riqnomasini tuzish.
