# LOYIHA BOSQICHLARI VA PROGRESS (PROGRESS.md)

Ushbu hujjat loyihaning har bir bosqichidagi bajarilgan ishlar, testlar holati, ochiq masalalar va keyingi qadamlarni aniq qayd etadi. Har bir yirik o'zgarishdan keyin yangilanadi.

---

## Holat Xulosasi (Current Status)
- **Hozirgi Bosqich**: Bosqich 4 yakunlandi -> Bosqich 5 ga o'tish tayyor.
- **Git Holati**: Bosqich 3 commit qilingan (`613e433`), Bosqich 4 kiritildi.
- **Mavjud Testlar**: 98 ta test yashil (100% PASS), 85%+ coverage.
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
| **Bosqich 4** | ByteTrack tracking, kalibrovka (bird's-eye, siljish), sensor fusion, exercise detector | ✅ TUGALLANDI | 2-bosqichli ByteTrack (past confidence'da ham ID saqlash, EMA smoothing), IPM Bird's-Eye View, Visual Odometry va Dead Reckoning fallback, 8 ta mashq ketma-ketligi va qoidalar bog'lanishi (98 ta test PASS). |
| **Bosqich 5** | Rule engine, event manager (debounce/cooldown/dedup), scoring engine, kritik oqim, SUSPECT | ⏳ BOSHLANMOQDA | 1 xato = 1 event, 1 ovoz, 1 penalty kafolati. |
| **Bosqich 6** | Evidence recorder (ring buffer, SHA-256 zanjir), 3-tilli Audio service (.wav to'plami), storage manager | ⏳ KUTILMOQDA | 3 tilda to'liq audio tekshiruvi va audit. |
| **Bosqich 7** | QML UI: 3-maketli ekran klaviaturasi, til almashtirgich, 9 ta ekran, popup navbati, 3-tilli hisobotlar | ⏳ KUTILMOQDA | Matn kesilmasligi (clipping), tofu yo'qligi, shrift embed. |
| **Bosqich 8** | ONNX backend (CUDA, TensorRT, DirectML), o'qitish/export/baholash skriptlari, replay tizimi | ⏳ KUTILMOQDA | Mock vs Real ONNX, precision/recall benchmark. |
| **Bosqich 9** | Ed25519 offline aktivatsiya, tolerant Machine ID, soat himoyasi, Admin License Generator | ⏳ KUTILMOQDA | Asimmetrik kriptografiya, alohida admin vositasi. |
| **Bosqich 10** | Setup Wizard (apparat tekshiruvi, kamera yo'nalishi, kalibrovka ustasi, poligon zonalari, audio test) | ⏳ KUTILMOQDA | Birinchi ishga tushirishda 3 tilda interaktiv usta. |
| **Bosqich 11** | Watchdog, diagnostika zipi, yangilash/rollback, Nuitka build, Inno Setup 3 tilda (.isl) | ⏳ KUTILMOQDA | Windows installer, uz-Latn.isl, uz-Cyrl.isl, Russian.isl. |
| **Bosqich 12** | Yakuniy sifat: check_translations, ovoz to'plami testi, soak (2 soat), 3 til skrinshotlari, hujjatlar | ⏳ KUTILMOQDA | Demo ishga tushirish: uz-Latn, uz-Cyrl, ru. |

---

## Bajarilgan Ishlar (Bosqich 4)
- [x] Haqiqiy 2-bosqichli ByteTrack algoritmi (`SimpleByteTracker`, `MultiCameraTracker`): yuqori va past confidence moslashtirish, to'siq/loyqa paytida ID almashmasligi, EMA tebranish tekislash (`smooth_alpha`), `TENTATIVE` -> `CONFIRMED` track lifecycle.
- [x] Kalibrovka xizmati kengaytirildi (`CalibrationService`, `MultiCameraCalibration`): Bird's-Eye View (IPM) yaratish, yer tekisligi bilan piksellar orasida to'g'ri va teskari proyeksiyalar (`pixel_to_ground_plane`, `ground_to_pixel`), avtomashinadan chiziqqacha bo'lgan real masofa (`point_to_line_distance_ground`), avtomatlashtirilgan fiducial siljish detektori.
- [x] Sensor Fusion va Dead Reckoning (`SensorFusionService`, `VisualOdometryEstimator`): Lucas-Kanade optik oqimi orqali Visual Odometry, GPS uzilib qolganda avtonom Dead Reckoning orqali tezlik va koordinata hisoblash, to'xtashni ko'p datchikli tasdiqlash (`confirm_vehicle_stopped`), estakadada orqaga sirpanishni aniqlash (`is_rollback_exceeded`).
- [x] 8 ta avtodrom mashqi (`ExerciseDetector`): `START`, `ESTAKADA`, `ZMEIKA`, `TURN_90`, `PARALLEL_PARKING`, `GARAGE_REVERSE`, `STOP`, `FINISH`. O'tkazib yuborishni aniqlash (`SKIPPED`), kirish yo'nalishi burchagini tekshirish (`check_heading`), mashqqa xos qoidalarni faollashtirish (`is_rule_active_for_current_exercise`) va `FINISH` da to'xtash sharti bilan yakunlash ruxsati.
- [x] 98/98 test yashil (100% PASS), 0 ruff xatosi, 0 mypy xatosi.

---

## Ochiq Masalalar va Keyingi Qadam (Bosqich 5)
- [ ] Bosqich 5: Rule Engine plugins, Event Manager (debounce, cooldown, de-duplication, 1 xato = 1 event = 1 ovoz = 1 penalty kafolati), SUSPECT ajratish (jarimasiz), kritik qoidabuzarlik darhol yakunlash oqimi.
