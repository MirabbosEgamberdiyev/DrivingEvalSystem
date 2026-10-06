# SINOV VA SIFATNI TA'MINLASH STRATEGIYASI (TESTING.md)

Ushbu hujjat tizimning to'liq sinov qamrovi, metodologiyasi va sifat mezonlarini bayon qiladi.

---

## 1. Test Turlari va Strukturasi

| Test Toifasi | Papka | Sinov Maqsadi |
|---|---|---|
| **Unit Testlar** | `tests/unit/` | State machine ruxsat etilgan/taqiqlangan o'tishlari, qoidalar validatsiyasi, debouncing, scoring, hash zanjiri, konfiguratsiya sxemalari. |
| **Integration Testlar** | `tests/integration/` | To'liq lifecycle, kamera uzilishi, quvvat uzilishidan tiklash, 100% offline tarmoq izolyatsiyasi. |
| **Replay Testlar** | `tests/replay/` | Ground truth ssenariylarini qayta o'ynatish, har bir qoida bo'yicha Precision va Recall hisoblash. |
| **Performance Testlar** | `tests/performance/` | 1000+ kadrli Soak testi (xotira oqishini tekshirish), Latency benchmark (<200 ms). |

---

## 2. Testlarni Ishga Tushirish Buyruqlari

```bash
# 1. Barcha testlarni qamrov hisoboti bilan yurgizish
PYTHONPATH=src pytest --cov=driving_eval --cov-report=term-missing -v

# 2. Replay test va Precision/Recall jadvalini chiqarish
PYTHONPATH=src pytest tests/replay/test_replay_ground_truth.py -s -v

# 3. Latency benchmark natijalarini ko'rish
PYTHONPATH=src pytest tests/performance/test_latency_benchmark.py -s -v

# 4. Kod sifatini tekshirish (Ruff va Mypy)
ruff check src tests
mypy src tests
```

---

## 3. Sifat Mezonlari (Quality Gates)
- Test Coverage: `core/` va asosiy modullar uchun kamida 80% (joriy qamrov: **86%**).
- Replay Precision/Recall: Ground truth benchmarkida **100%** (1.00 Precision, 1.00 Recall).
- Latency P95: **< 200 ms** (joriy ko'rsatkich: **< 15 ms**).
- Linter & Type Checker: `ruff` va `mypy` 0 xato bilan toza.
