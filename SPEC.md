# MAHSULOT SPETSIFIKATSIYASI (SPEC.md)
## Offline 4-Camera AI Driving Training & Evaluation System

---

## 1. Umumiy Ma'lumot va Maqsad

"Offline 4-Camera AI Driving Training & Evaluation System" — bu avtomaktablar, imtihon markazlari va haydovchilarni tayyorlash poligonlari uchun mo'ljallangan, 100% offline, mustaqil va tarqatiladigan dasturiy-apparat majmuasidir.

Dastur nomzodning real avtomobilda poligon mashqlarini bajarishini 4 ta kamera (FRONT, REAR, LEFT, RIGHT), GPS, IMU va OBD-II telemetriyasi orqali real vaqtda tahlil qiladi, qoidabuzarliklarni yuqori aniqlikda (precision-first) aniqlaydi, sensorli monitorda ko'rsatadi, 3 tilda ovozda o'qib beradi, jarima hisoblaydi, dalillarni kriptografik zanjirda saqlaydi va yakuniy bahoni (PASS/FAIL) chiqaradi.

---

## 2. Tizim Arxitekturasi

```mermaid
flowchart TD
    subgraph HARDWARE["Apparat Qatlami (Avtomobil)"]
        CAM["4x Kameralar (Front, Rear, Left, Right)"]
        SENS["Sensorlar (GPS / IMU / OBD-II)"]
        TOUCH["Sensorli Monitor (10-12' Touchscreen)"]
        AUDIO["Audio Tizim (Dinamik / Spiker)"]
        NVME["Lokal NVMe SSD"]
    end

    subgraph ENGINE["Core Backend (Python / C++ ONNX)"]
        CAM_SVC["Camera Service (Sinxronlash, Bandwidth)"]
        AI_ENG["AI Inference Engine (ONNX Runtime / CUDA / DirectML)"]
        TRACK["ByteTrack Tracker"]
        CALIB["Calibration & Bird's-Eye Transform"]
        FUSION["Sensor Fusion & Odometriya"]
        EX_DET["Mashq Detektori (Exercise Detector)"]
        RULE_ENG["Qoidalar Dvigateli (Rule Engine - rules.yaml)"]
        EVT_MGR["Event Manager (Debounce / Cooldown / Dedup)"]
        SCORE_ENG["Scoring Engine (PASS/FAIL, Suspect Isolation)"]
        EVID_REC["Evidence Recorder (Ring Buffer, SHA-256)"]
        AUD_SVC["Audio Service (Queue, Multi-lang WAV)"]
        I18N_SVC["I18n Service (uz-Latn, uz-Cyrl, ru, Plural)"]
        STATE_MCH["Exam State Machine (Strict Matrix)"]
        DB_REPO["SQLite WAL Repository & Hash Chain"]
    end

    subgraph UI_LAYER["Foydalanuvchi Interfeysi (PySide6 / QML)"]
        BRIDGE["BackendBridge (MockBridge / RealBridge)"]
        STACK["QML Navigation Stack"]
        THEME["Theme Singleton (WCAG AAA/AA)"]
        KEYBOARD["3-Maketli Ekran Klaviaturasi"]
        POPUP_QUEUE["Violation Popup Sequential Queue"]
        SCREENS["9 ta Ekran (Home, Precheck, Ready, HUD, Result, etc.)"]
    end

    subgraph SECURITY["Xavfsizlik va Litsenziyalash"]
        LIC_CHECK["Ed25519 Offline Litsenziya Tekshiruvi"]
        MACHINE_ID["Tolerant Machine ID Kvorumi"]
        TIME_GUARD["Anti-Clock-Tampering Guard"]
        DATA_ENC["Consent & Data Deletion Manager"]
    end

    CAM --> CAM_SVC
    SENS --> FUSION
    CAM_SVC --> AI_ENG
    AI_ENG --> TRACK
    TRACK --> FUSION
    CALIB --> FUSION
    FUSION --> EX_DET
    EX_DET --> RULE_ENG
    RULE_ENG --> EVT_MGR
    EVT_MGR --> SCORE_ENG
    EVT_MGR --> EVID_REC
    EVT_MGR --> AUD_SVC
    AUD_SVC --> AUDIO
    EVID_REC --> NVME
    SCORE_ENG --> DB_REPO
    STATE_MCH --> DB_REPO

    CORE --> BRIDGE
    BRIDGE --> STACK
    STACK --> SCREENS
    SCREENS --> TOUCH
```

---

## 3. Tizim Jarayonlari Xaritasi (State Machine)

### A. Dastur Darajasidagi Holatlar
```mermaid
stateDiagram-v2
    [*] --> UNLICENSED
    UNLICENSED --> SETUP_REQUIRED: Litsenziya kodi tasdiqlandi (Ed25519)
    SETUP_REQUIRED --> READY: Setup Wizard muvaffaqiyatli yakunlandi
    READY --> UNLICENSED: Litsenziya muddati tugadi
```

### B. Imtihon Testi Darajasidagi Qat'iy Holatlar
```mermaid
stateDiagram-v2
    IDLE --> BOOT
    BOOT --> READY
    READY --> PRECHECK: Pre-check boshlandi
    PRECHECK --> CAMERA_CHECK: Kameralar tekshirildi
    CAMERA_CHECK --> SYSTEM_CHECK: AI, sensor, audio tekshirildi
    SYSTEM_CHECK --> TEST_READY: 12/12 komponent READY
    SYSTEM_CHECK --> PRECHECK: Xato bo'lsa (BLOCKED)
    TEST_READY --> TEST_ACTIVE: 'TESTNI BOSHLASH' bosildi
    TEST_ACTIVE --> FINISH_DETECTED: Finish zonasiga kirdi
    TEST_ACTIVE --> CRITICAL_VIOLATION: Kritik xato aniqlandi
    TEST_ACTIVE --> INTERRUPTED: Quvvat uzildi / kamera tushdi
    CRITICAL_VIOLATION --> TERMINATED: Test majburiy to'xtatildi
    TERMINATED --> RESULT_READY
    FINISH_DETECTED --> VEHICLE_STOPPED: Tezlik ~ 0 km/h
    VEHICLE_STOPPED --> FINALIZING: 'TESTNI YAKUNLASH' bosildi
    FINALIZING --> RESULT_READY: Ball va hash hisoblandi
    RESULT_READY --> COMPLETED: Natija ko'rsatildi
    COMPLETED --> READY: Asosiy ekranga qaytish
```

---

## 4. Qoidabuzarlik Konveyeri (Violation Pipeline)

```mermaid
sequenceDiagram
    participant Cam as Kamera Oqimi
    participant Det as AI Detector
    participant Trk as ByteTrack
    participant Rule as Rule Engine (rules.yaml)
    participant Evt as Event Manager
    participant HUD as QML HUD & Popup
    participant Aud as Audio Service
    participant Evid as Evidence Recorder
    participant DB as SQLite DB

    Cam->>Det: Yangi sinxronlashtirilgan kadrlar
    Det->>Trk: Bounding Box & Class (Konus, Chiziq)
    Trk->>Rule: Obyekt trayektoriyasi va ID
    Rule->>Rule: Kalibrovka bo'yicha masofa (metr), kontakt sharti
    Rule->>Evt: Candidate Event (N kadr davomida tasdiq)
    Evt->>Evt: Debounce & Cooldown tekshiruvi (Dedup)
    
    alt Tasdiqlangan (Confidence >= Threshold)
        Evt->>HUD: Popup ko'rsatish (Sessiya tilida, navbat bilan 3.5s)
        Evt->>Aud: Ovozli xabar (.wav navbatga qo'yish)
        Evt->>Evid: Ring buferdan before/event/after.jpg va event.mp4 kesish
        Evt->>DB: Qoidabuzarlik va jarimani darhol yozish
    else Shubhali (Confidence < Threshold)
        Evt->>DB: Status = SUSPECT (Jarima yozilmaydi)
        Evt->>Evid: Dalil saqlash (Inspektor tekshiruvi uchun)
    end
```

---

## 5. Ko'p Tillilik (i18n / l10n) Spetsifikatsiyasi

| Parametr | `uz-Latn` (Standart) | `uz-Cyrl` (Kirill) | `ru` (Rus) |
|---|---|---|---|
| **Alifbo** | Lotin (`oʻ`, `gʻ`, `sh`, `ch`) | Kirill (`ў`, `қ`, `ғ`, `ҳ`) | Rus kirill (`ё`, `ъ`, `ь`, `ы`, `э`) |
| **Matn uzunligi** | Bazaviy (100%) | ~100-105% | Kengaygan (+20-35%) |
| **Plural qoidalari** | 1 ta forma (N ball) | 1 ta forma (N балл) | 3 ta forma: 1 балл, 2 балла, 5 баллов |
| **Audio papkasi** | `data/audio/uz-Latn/` | `data/audio/uz-Cyrl/` | `data/audio/ru/` |
| **Ovoz formati** | 16-bit 44.1 kHz WAV | 16-bit 44.1 kHz WAV | 16-bit 44.1 kHz WAV |
| **Fallback tartibi** | XATO (Eng quyi asos) | `uz-Latn` -> XATO | `uz-Latn` -> XATO |
| **Installer (.isl)** | `uz-Latn.isl` | `uz-Cyrl.isl` | `Russian.isl` |
| **Klaviatura maketi** | QWERTY + `oʻ`, `gʻ` | ЙЦУКЕН + `ў`, `қ`, `ғ`, `ҳ` | ЙЦУКЕН (Standart) |

---

## 6. Risklar Reestri (Risk Register)

| Risk ID | Xavf Tavsifi | Ehtimollik | Ta'siri | Yumshatish Chorasi (Mitigation) |
|---|---|---|---|---|
| **R-01** | 4 ta USB kamera bitta host controllerga ulanib, bandwidth yetmasligi | Yuqori | Kritik | Setup Wizard'da controllerlar topologiyasini tekshirish, MJPEG apparatli siqish, pre-check bandwidth testi. |
| **R-02** | GPU bo'lmagan zaif kompyuterda AI kechikishi $\ge 150$ ms bo'lishi | O'rta | Yuqori | ONNX DirectML/CUDA talabi, pre-check paytida benchmark, past FPS da ASSESSMENT imtihonini bloklash. |
| **R-03** | Quyosh nuri tushganda yoki qorong'ida chiziq/konus ko'rinmasligi | O'rta | Yuqori | Shubhali holatda SUSPECT qilib jarima olmaslik, HDR kameralar va yoritgich talabi (HARDWARE_TODO). |
| **R-04** | Rus tili matnlari uzunligi sababli UI da matn kesilishi (clipping) | O'rta | O'rta | Moslashuvchan QML layout, `implicitWidth`, 3 tilda barcha ekranlar skrinshot avto-testi. |
| **R-05** | Tizim soati orqaga surilib litsenziya muddatini aldashga urinish | O'rta | Yuqori | SQLite DB da SHA-256 zanjirli so'nggi vaqt muhrini saqlash va teskari vaqtni aniqlash. |
| **R-06** | Test vaqtida avtomobil akkumulyatori o'chib qolishi (quvvat uzilishi) | Yuqori | Kritik | SQLite WAL darhol commit, har hodisadan keyin flush, boot vaqtida `SAFE_INTERRUPT` tiklash. |
| **R-07** | O'zbek kirill tarjimasida mexanik xatolar | O'rta | O'rta | Rasmiy qoidalar uchun avto-transliteratsiyani bloklash, `reviewed: false` ro'yxati (TRANSLATION_REVIEW). |

---

## 7. Nima Kafolatlanadi va Nima Kafolatlanmaydi

### Nima Kafolatlanadi:
1. **100% Offline Ishlash**: Tizim hech qachon internetga ulanmaydi, barcha kutubxonalar, modellar va resurslar lokal.
2. **Kriptografik Ma'lumot Butunligi**: Har bir sessiya va uning dalillari (rasmlar, video) SHA-256 xesh zanjiri bilan himoyalangan, DB o'zgartirilsa darhol fosh bo'ladi.
3. **Deterministik Jarima Hisobi**: Bitta xato kadrlar davomida 20 marta ko'rinsa ham, faqat 1 ta hodisa, 1 ta ovoz va 1 ta jarima bo'ladi.
4. **Adolat (Precision Ustuvor)**: Tasdiqlanmagan yoki noaniq vaziyatda nomzoddan HECH QACHON jarima olinmaydi (faqat SUSPECT yoziladi).
5. **3 Til To'liqligi**: Ekranda ko'rinadigan barcha matnlar, xabarlar va hisobotlar tanlangan tilda bo'ladi.

### Nima Kafolatlanmaydi:
1. **Nostandart Poligonda Aniqlik**: Agar chiziqlar o'chib ketgan, konuslar nostandart rang/o'lchamda bo'lsa yoki yorug'lik yetarli bo'lmasa, AI modelining 100% aniqligi kafolatlanmaydi.
2. **Zaif / Noto'g'ri Apparat**: 4 ta kamerani USB 2.0 bitta hub orqali ulaganda yoki GPU yo'q kompyuterda kadrlar tushib qolishiga kafolat berilmaydi (Wizard buni oldindan bloklaydi).
3. **Hujumchilarga Qarshi Mutlaq Dasturiy Himoya**: Nuitka bilan kompilyatsiya qilingan Python ilovasi malakali teskari muhandisga qarshi 100% buzilmas bo'lishi mumkin emas (lekin oddiy nusxalashdan to'liq himoyalangan).
