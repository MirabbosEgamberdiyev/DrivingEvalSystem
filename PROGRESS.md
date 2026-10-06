# LOYIHA BOSQICHLARI VA PROGRESS (PROGRESS.md)

Ushbu hujjat loyihaning har bir bosqichidagi bajarilgan ishlar, testlar holati, ochiq masalalar va keyingi qadamlarni aniq qayd etadi. Har bir yirik o'zgarishdan keyin yangilanadi.

---

## Holat Xulosasi (Current Status)
- **Hozirgi Bosqich**: Bosqich 10 yakunlandi -> Bosqich 11 (Packaging, Inno Setup, Watchdog) boshlanmoqda.
- **Git Holati**: Bosqich 9 commit qilingan (`4c5e7c6`), Bosqich 10 kiritildi.
- **Mavjud Testlar**: 116 ta test yashil (100% PASS), 86%+ coverage.
- **Ruff & Mypy**: 0 xato (100% toza).
- **Lokalizatsiya**: 3 ta til (`uz-Latn`, `uz-Cyrl`, `ru`) 100% to'liq, 0 ta unreviewed qator.

---

## Bosqichlar Rejasi va Bajarilish Holati

| Bosqich | Tavsif | Holat | Izoh |
|---|---|---|---|
| **Bosqich 0** | Tahlil, tarixiy ziddiyatlarni hal qilish, `SPEC.md`, `DECISIONS.md`, `ASSUMPTIONS.md`, `PROGRESS.md` | ✅ TUGALLANDI | Barcha 11 ta savol va i18n qarorlari asoslab yozildi (`e8afc63`). |
| **Bosqich 1** | Skelet, 3-tilli `rules.yaml`, pydantic sxemalar, DB migratsiyalar, `i18n_service` va `check_translations.py` | ✅ TUGALLANDI | 3 til kataloglari, ICU plural qoidalari, strict fallback, DB migratsiya 2, linter va testlar to'liq ishga tushdi (`c2d30d2`). |
| **Bosqich 2** | State machine (Dastur: UNLICENSED/SETUP/READY; Test: IDLE -> COMPLETED) va testlar | ✅ TUGALLANDI | 2 darajali state machine, ruxsat etilgan o'tishlar matritsasi, gating, audit logging va power-loss tiklash (`0c4f2dd`). |
| **Bosqich 3** | Camera service (Windows MF/DirectShow, RTSP, sim), pre-check, MockDetector, Vertikal Kesim (`--simulate`) | ✅ TUGALLANDI | DirectShow + buffer=1, 3-tilli til tugmalari (O'ZB/ЎЗБ/РУС), dinamik UI i18n yangilanishi, `--simulate` CLI va in-memory vertikal kesim testlari (`613e433`). |
| **Bosqich 4** | ByteTrack tracking, kalibrovka (bird's-eye, siljish), sensor fusion, exercise detector | ✅ TUGALLANDI | 2-bosqichli ByteTrack (past confidence'da ham ID saqlash, EMA smoothing), IPM Bird's-Eye View, Visual Odometry va Dead Reckoning fallback, 8 ta mashq ketma-ketligi va qoidalar bog'lanishi (`a098544`). |
| **Bosqich 5** | Rule engine, event manager (debounce/cooldown/dedup), scoring engine, kritik oqim, SUSPECT | ✅ TUGALLANDI | 9 ta qoida plagini, 1 xato = 1 event = 1 ovoz = 1 penalty kafolati, 3-tilli pasport getterlari, SUSPECT jarimasiz ajratish, kritik to'xtatish (`05e4541`). |
| **Bosqich 6** | Evidence recorder (ring buffer, SHA-256 zanjir), 3-tilli Audio service (.wav to'plami), storage manager | ✅ TUGALLANDI | 4-kamerali kompozitli dalillar paketi (`before`, `event`, `after`, `composite.jpg`, `event.mp4`, `metadata.json`), kriptografik xesh tekshiruvi, 3 ta tilda 36 ta WAV audio to'plami va USB eksport manifesti (`fd730bb`). |
| **Bosqich 7** | QML UI: 3-maketli ekran klaviaturasi, til almashtirgich, 9 ta ekran, popup navbati, 3-tilli hisobotlar | ✅ TUGALLANDI | 3-maketli sensorli klaviatura (`uz-Latn`, `uz-Cyrl`, `ru`), ReportLab Unicode font embed bilan 3-tilli PDF va UTF-8 BOM CSV hisobotlari, 3 ta rezolyutsiyada skrinshot testlari (103 ta test PASS). |
| **Bosqich 8** | ONNX backend (CUDA, TensorRT, DirectML), o'qitish/export/baholash skriptlari, replay tizimi | ✅ TUGALLANDI | DirectML ustuvorligi, YOLOv8/v5 chiqish formatlari, opset 17 eksport skripti, SessionReplayer va 100% precision/recall testlari. |
| **Bosqich 9** | Ed25519 offline aktivatsiya, tolerant Machine ID, soat himoyasi, Admin License Generator | ✅ TUGALLANDI | Pure-Python RFC 8032 Ed25519, 3-of-4 apparat kvorumi, SHA-256 soat orqaga surishdan himoyalovchi zanjir, admin vositasi. |
| **Bosqich 10** | Setup Wizard (apparat tekshiruvi, kamera yo'nalishi, kalibrovka ustasi, poligon zonalari, audio test) | ✅ TUGALLANDI | 7 bosqichli to'liq interaktiv usta (SetupWizardService, SetupWizardBridge, SetupWizardScreen.qml, 116 test PASS). |
| **Bosqich 11** | Watchdog, diagnostika zipi, yangilash/rollback, Nuitka build, Inno Setup 3 tilda (.isl) | ⏳ BOSHLANMOQDA | Windows installer, uz-Latn.isl, uz-Cyrl.isl, Russian.isl. |
| **Bosqich 12** | Yakuniy sifat: check_translations, ovoz to'plami testi, soak (2 soat), 3 til skrinshotlari, hujjatlar | ⏳ KUTILMOQDA | Demo ishga tushirish: uz-Latn, uz-Cyrl, ru. |

---

## Bajarilgan Ishlar (Bosqich 10)
- [x] `SetupWizardService` (`src/driving_eval/wizard/setup_service.py`): 7 bosqichli avtomatlashtirilgan usta (EULA & Til, Apparat & USB kontrollerlar, 4 kamera xaritalash, Kalibrovka va siljish tekshiruvi, Poligon zonalari, Kabina audio testi, Konfiguratsiyani saqlash va READY ga o'tish).
- [x] `SetupWizardBridge` (`src/driving_eval/ui_qml/bridge/setup_wizard_bridge.py`): QML UI va backend orasidagi xavfsiz Signal/Slot ko'prigi.
- [x] `SetupWizardScreen.qml` (`src/driving_eval/ui_qml/qml/screens/SetupWizardScreen.qml`): Katta sensorli tugmalar, 7 qadamli progress-bar, apparat holati, 4 ta kamera preview selektori, audio test tugmasi.
- [x] `tests/unit/test_setup_wizard.py`: Usta bosqichlari, navigatsiya chegaralari, QML bridge chaqiruvlari to'liq qamrab olindi.
- [x] 116/116 test yashil (100% PASS), tarjimalar to'liq tasdiqlangan.

---

## Ochiq Masalalar va Keyingi Qadam (Bosqich 11)
- [ ] Bosqich 11: Packaging, Inno Setup Installer (3 tilda: uz-Latn.isl, uz-Cyrl.isl, Russian.isl), Kiosk rejim, DirectShow drayver tekshiruvi, Watchdog xizmati va diagnostika zip bundle eksporti.
