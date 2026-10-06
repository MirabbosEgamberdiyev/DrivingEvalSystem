# Standalone 4-Camera Offline AI Driving Training & Evaluation System

**Production darajasidagi 100% offline, standalone avtomatlashtirilgan haydash imtihoni va baholash platformasi.**

---

## 📌 Asosiy Xususiyatlar
- **100% OFFLINE**: Hech qanday internet, bulut, tashqi API yoki telemetriya chaqiruvlari mavjud emas.
- **STANDALONE**: 1 ta avtomobil = 1 ta sanoat kompyuteri = 1 ta dastur = 1 ta SQLite baza (WAL rejimida). Mashinalar faqat `config/car.yaml` va `config/calibration/` orqali farqlanadi.
- **QAT'IY STATE MACHINE**: Boolean bayroqlar taqiqlangan. Ruxsatsiz holat o'tishlari istisno beradi va SQLite `system_logs` ga yoziladi.
- **PRECISION USTUVOR (SUSPECT MEXANIZMI)**: Ishonchlilik darajasi yetarli bo'lmagan hodisalar jarimaga tortilmaydi, faqat inspektor ko'rishi uchun `SUSPECT` sifatida ajratiladi.
- **DEDUP & COOLDOWN**: 20 kadrli bitta xato aynan 1 ta hodisa, 1 ta jarima va 1 ta ovozli ogohlantirish beradi.
- **KRIPTOGRAFIK BUTUNLIK**: Barcha dalillar (JPG, MP4, JSON) va test natijalari SHA-256 xesh zanjiri (hash chaining) bilan himoyalangan.
- **MODULLAR & PLUGINLAR**: Har bir qoida alohida plugin. Barcha jarimalar, chegaralar va matnlar kodda emas, `config/rules.yaml` da (Single Source of Truth).

---

## 📂 Loyiha Tuzilmasi

```
driving_eval_system/
├── config/
│   ├── config.yaml               # Asosiy tizim konfiguratsiyasi (thresholdlar, sensorlar, storage)
│   ├── rules.yaml                # Rasmiy imtihon qoidalari pasporti (Single Source of Truth)
│   ├── car.yaml                  # Standalone mashina pasporti (car_id, o'lchamlar, vin)
│   └── calibration/              # 4 ta kameraning kalibrovkasi va referens fidutsiallari
│       ├── front_camera.json
│       ├── rear_camera.json
│       ├── left_camera.json
│       └── right_camera.json
├── src/driving_eval/
│   ├── core/                     # State Machine, Pydantic sxemalar, Istisnolar, Logging
│   ├── db/                       # SQLite WAL schema, Repository, Migratsiyalar, Hash zanjiri
│   ├── hardware/                 # MultiCameraService, SensorFusion, Calibration, Precheck
│   ├── ai/                       # ONNXDetector, TensorRT, MockDetector, ByteTracker, ExerciseDetector
│   ├── rules/                    # RuleEngine, EventManager (dedup), ScoringEngine, Plugins
│   ├── evidence/                 # EvidenceRecorder (ring buffer, before/event/after jpg, mp4), Storage
│   ├── audio/                    # AudioService (WAV queue, Piper TTS fallback)
│   ├── ui/                       # PySide6 Kiosk UI, HUD, Popups, Ekrani, i18n (O'zbek tili)
│   ├── reporting/                # Rasmiy PDF Bayonnoma va CSV eksport
│   ├── maintenance/              # Process Watchdog, Quvvat uzilishidan tiklash, USB Updater
│   └── app_runner.py             # CLI Entrypoint (--simulate, --kiosk, --check)
├── data/
│   ├── audio/uz/                 # WAV audio fayllar va VOICE_SCRIPTS.md
│   └── test_videos/              # Simulyatsiya videolari
├── ml_training/                  # CVAT annotatsiya spec, YOLO o'qitish, ONNX/TRT export, evaluation
├── systemd/                      # autoeval.service va Ubuntu LTS disk obrazi skripti
├── tests/
│   ├── unit/                     # State machine, rules, dedup, scoring, precheck, DB testlari
│   ├── integration/              # To'liq lifecycle, quvvat uzilishidan tiklash, 100% offline izolyatsiya
│   ├── replay/                   # Ground truth replay testi (Precision va Recall hisoboti)
│   └── performance/              # 1000 kadrli Soak test va Latency benchmark (<200 ms)
├── docs/                         # To'liq texnik hujjatlar to'plami
│   ├── ARCHITECTURE.md
│   ├── RULES_GUIDE.md
│   ├── CALIBRATION_GUIDE.md
│   ├── DEPLOYMENT.md
│   ├── OPERATIONS.md
│   ├── TESTING.md
│   ├── ASSUMPTIONS.md
│   └── HARDWARE_TODO.md
├── pyproject.toml
└── README.md
```

---

## 🚀 Ishga Tushirish

### 1. Muhitni Faollashtirish
```powershell
cd D:\My-project\driving_eval_system
.venv\Scripts\activate
```

### 2. Simulyatsiya Rejimida Ishga Tushirish
Mashina va real kameralarsiz sintetik video oqimi va telemetriya bilan butun tizimni sinab ko'rish:
```powershell
$env:PYTHONPATH = "src"
python -m driving_eval.app_runner --simulate
```

### 3. Diagnostika va Pre-Check Tekshiruvi
```powershell
$env:PYTHONPATH = "src"
python -m driving_eval.app_runner --check --simulate
```

### 4. Fullscreen Kiosk Rejimida Ishga Tushirish (Avtomobil uchun)
```powershell
$env:PYTHONPATH = "src"
python -m driving_eval.app_runner --kiosk
```

---

## 🧪 Sinovlar va Sifat Kafolati

```powershell
# Barcha 46 ta testni qamrov hisoboti bilan yurgizish (86% Coverage)
$env:PYTHONPATH = "src"
pytest --cov=driving_eval --cov-report=term-missing -v

# Replay Test (Ground Truth bo'yicha Precision/Recall jadvali)
pytest tests/replay/test_replay_ground_truth.py -s -v

# Latency Benchmark (<200 ms)
pytest tests/performance/test_latency_benchmark.py -s -v

# Linter va Type Checker
ruff check src tests
mypy src tests
```

---

## 📄 Hujjatlar
- [Arxitektura va Diagrammalar](docs/ARCHITECTURE.md)
- [Qoidalar va rules.yaml Qo'llanmasi](docs/RULES_GUIDE.md)
- [Kameralarni Kalibrovka Qilish](docs/CALIBRATION_GUIDE.md)
- [Joylashtirish va O'rnatish (Deployment)](docs/DEPLOYMENT.md)
- [Ekspluatatsiya va Nosozliklar Yo'riqnomasi](docs/OPERATIONS.md)
- [Sinov va Sifat Strategiyasi](docs/TESTING.md)
- [Qabul Qilingan Farazlar](docs/ASSUMPTIONS.md)
- [Apparat Ta'minoti Bo'yicha Vazifalar](docs/HARDWARE_TODO.md)
- [Ovozli Xabarlar va Diktor Matnlari](data/audio/uz/VOICE_SCRIPTS.md)
