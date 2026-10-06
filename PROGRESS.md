# LOYIHA BOSQICHLARI VA PROGRESS (PROGRESS.md)

Ushbu hujjat loyihaning har bir bosqichidagi bajarilgan ishlar, testlar holati, ochiq masalalar va keyingi qadamlarni aniq qayd etadi. Har bir yirik o'zgarishdan keyin yangilanadi.

---

## Holat Xulosasi (Current Status)
- **Hozirgi Bosqich**: Bosqich 5 yakunlandi -> Bosqich 6 ga o'tish tayyor.
- **Git Holati**: Bosqich 4 commit qilingan (`a098544`), Bosqich 5 kiritildi.
- **Mavjud Testlar**: 102 ta test yashil (100% PASS), 86%+ coverage.
- **Ruff & Mypy**: 0 xato (100% toza).
- **Lokalizatsiya**: 3 ta til (`uz-Latn`, `uz-Cyrl`, `ru`) 100% to'liq, dynamic language switcher, 0 ta unreviewed qator.

---

## Bosqichlar Rejasi va Bajarilish Holati

| Bosqich | Tavsif | Holat | Izoh |
|---|---|---|---|
| **Bosqich 0** | Tahlil, tarixiy ziddiyatlarni hal qilish, `SPEC.md`, `DECISIONS.md`, `ASSUMPTIONS.md`, `PROGRESS.md` | ✅ TUGALLANDI | Barcha 11 ta savol va i18n qarorlari asoslab yozildi (`e8afc63`). |
| **Bosqich 1** | Skelet, 3-tilli `rules.yaml`, pydantic sxemalar, DB migratsiyalar, `i18n_service` va `check_translations.py` | ✅ TUGALLANDI | 3 til kataloglari, ICU plural qoidalari, strict fallback, DB migratsiya 2, linter va testlar to'liq ishga tushdi (`c2d30d2`). |
| **Bosqich 2** | State machine (Dastur: UNLICENSED/SETUP/READY; Test: IDLE -> COMPLETED) va testlar | ✅ TUGALLANDI | 2 darajali state machine, ruxsat etilgan o'tishlar matritsasi, gating, audit logging va power-loss tiklash (`0c4f2dd`). |
| **Bosqich 3** | Camera service (Windows MF/DirectShow, RTSP, sim), pre-check, MockDetector, Vertikal Kesim (`--simulate`) | ✅ TUGALLANDI | DirectShow + buffer=1, 3-tilli til tugmalari (O'ZB/ЎЗБ/РУС), dinamik UI i18n yangilanishi, `--simulate` CLI va in-memory vertikal kesim testlari (`613e433`). |
| **Bosqich 4** | ByteTrack tracking, kalibrovka (bird's-eye, siljish), sensor fusion, exercise detector | ✅ TUGALLANDI | 2-bosqichli ByteTrack (past confidence'da ham ID saqlash, EMA smoothing), IPM Bird's-Eye View, Visual Odometry va Dead Reckoning fallback, 8 ta mashq ketma-ketligi va qoidalar bog'lanishi (`a098544`). |
| **Bosqich 5** | Rule engine, event manager (debounce/cooldown/dedup), scoring engine, kritik oqim, SUSPECT | ✅ TUGALLANDI | 9 ta qoida plagini, 1 xato = 1 event = 1 ovoz = 1 penalty kafolati, 3-tilli pasport getterlari, SUSPECT jarimasiz ajratish, kritik to'xtatish (102 ta test PASS). |
| **Bosqich 6** | Evidence recorder (ring buffer, SHA-256 zanjir), 3-tilli Audio service (.wav to'plami), storage manager | ⏳ BOSHLANMOQDA | 3 tilda to'liq audio tekshiruvi, NVMe ring bufer va audit. |
| **Bosqich 7** | QML UI: 3-maketli ekran klaviaturasi, til almashtirgich, 9 ta ekran, popup navbati, 3-tilli hisobotlar | ⏳ KUTILMOQDA | Matn kesilmasligi (clipping), tofu yo'qligi, shrift embed. |
| **Bosqich 8** | ONNX backend (CUDA, TensorRT, DirectML), o'qitish/export/baholash skriptlari, replay tizimi | ⏳ KUTILMOQDA | Mock vs Real ONNX, precision/recall benchmark. |
| **Bosqich 9** | Ed25519 offline aktivatsiya, tolerant Machine ID, soat himoyasi, Admin License Generator | ⏳ KUTILMOQDA | Asimmetrik kriptografiya, alohida admin vositasi. |
| **Bosqich 10** | Setup Wizard (apparat tekshiruvi, kamera yo'nalishi, kalibrovka ustasi, poligon zonalari, audio test) | ⏳ KUTILMOQDA | Birinchi ishga tushirishda 3 tilda interaktiv usta. |
| **Bosqich 11** | Watchdog, diagnostika zipi, yangilash/rollback, Nuitka build, Inno Setup 3 tilda (.isl) | ⏳ KUTILMOQDA | Windows installer, uz-Latn.isl, uz-Cyrl.isl, Russian.isl. |
| **Bosqich 12** | Yakuniy sifat: check_translations, ovoz to'plami testi, soak (2 soat), 3 til skrinshotlari, hujjatlar | ⏳ KUTILMOQDA | Demo ishga tushirish: uz-Latn, uz-Cyrl, ru. |

---

## Bajarilgan Ishlar (Bosqich 5)
- [x] Barcha 9 ta rasmiy qoida uchun `BaseRulePlugin` plaginlari to'liq yaratildi va `RuleEngine` ga ulandi (`SEATBELT_UNFASTENED`, `CONE_TOUCH`, `STOP_LINE_VIOLATION`, `HILL_ROLLBACK`, `SPEED_EXCEEDED`, `INDICATOR_MISSED`, `PARKING_OUT_OF_BOUNDS`, `CRITICAL_COLLISION`, `EXERCISE_SEQUENCE_BROKEN`).
- [x] `EventManager`: Debounce filtri (flicker tebranishlarida xato bermaslik), Cooldown mexanizmi va qat'iy de-duplication (20 kadr davomida bitta to'siqqa tegilganda AYNAN 1 ta hodisa va 1 ta jarima).
- [x] Har bir hodisaga 3 tildagi pasport qiymatlarini qaytaruvchi getterlar (`get_title(lang)`, `get_screen_text(lang)`, `get_voice_text(lang)`, `get_voice_file(lang)`) qo'shildi.
- [x] Precision kafolati: Ishonch darajasi past bo'lgan (`confidence < min_confidence`) yoki shubhali vaziyatlar avtomatik ravishda `SUSPECT` deb belgilanadi va AYNAN 0 jarima balli yoziladi, talaba asossiz jarimaga tortilmaydi.
- [x] `ScoringEngine`: 100 balldan boshlab jarimalarni ayirish, kritik xatolarda darhol testni yakunlash (`is_terminated = True`, `is_passing = False`).
- [x] 102/102 test yashil (100% PASS), 0 ruff xatosi, 0 mypy xatosi.

---

## Ochiq Masalalar va Keyingi Qadam (Bosqich 6)
- [ ] Bosqich 6: Evidence recorder (NVMe ring buffer, oldingi va keyingi 5 soniya, JPEG snapshots, MP4 klip, SHA-256 zanjir), 3-tilli Audio Service (`data/audio/uz-Latn/`, `data/audio/uz-Cyrl/`, `data/audio/ru/`), storage manager (avto-pruning, USB eksport).
