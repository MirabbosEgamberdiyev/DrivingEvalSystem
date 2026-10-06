# LOYIHA BOSQICHLARI VA PROGRESS (PROGRESS.md)

Ushbu hujjat loyihaning har bir bosqichidagi bajarilgan ishlar, testlar holati, ochiq masalalar va keyingi qadamlarni aniq qayd etadi. Har bir yirik o'zgarishdan keyin yangilanadi.

---

## Holat Xulosasi (Current Status)
- **Hozirgi Bosqich**: Bosqich 1 yakunlandi -> Bosqich 2 ga o'tish tayyor.
- **Git Holati**: Bosqich 0 commit qilingan (`e8afc63`), Bosqich 1 o'zgarishlari kiritildi.
- **Mavjud Testlar**: 72 ta test yashil (100% PASS), 84% test coverage.
- **Ruff & Mypy**: 0 xato (100% toza, 80 ta fayl tekshirildi).
- **Lokalizatsiya**: 3 ta til (`uz-Latn`, `uz-Cyrl`, `ru`) 100% to'liq, ICU plural qo'llab-quvvatlangan, 100% key parity, 0 ta unreviewed qator.

---

## Bosqichlar Rejasi va Bajarilish Holati

| Bosqich | Tavsif | Holat | Izoh |
|---|---|---|---|
| **Bosqich 0** | Tahlil, tarixiy ziddiyatlarni hal qilish, `SPEC.md`, `DECISIONS.md`, `ASSUMPTIONS.md`, `PROGRESS.md` | ✅ TUGALLANDI | Barcha 11 ta savol va i18n qarorlari asoslab yozildi (`e8afc63`). |
| **Bosqich 1** | Skelet, 3-tilli `rules.yaml`, pydantic sxemalar, DB migratsiyalar, `i18n_service` va `check_translations.py` | ✅ TUGALLANDI | 3 til kataloglari, ICU plural qoidalari, strict fallback, DB migratsiya 2, linter va testlar to'liq ishga tushdi. |
| **Bosqich 2** | State machine (Dastur: UNLICENSED/SETUP/READY; Test: IDLE -> COMPLETED) va testlar | ⏳ BOSHLANMOQDA | 2 darajali state machine, ruxsat etilgan o'tishlar matritsasi va power-loss tiklash. |
| **Bosqich 3** | Camera service (Windows MF/DirectShow, RTSP, sim), pre-check, MockDetector, Vertikal Kesim (`--simulate`) | ⏳ KUTILMOQDA | Til tanlash -> Home -> Precheck -> Test -> Finish vertikal kesimi. |
| **Bosqich 4** | ByteTrack tracking, kalibrovka (bird's-eye, siljish), sensor fusion, exercise detector | ⏳ KUTILMOQDA | Visual odometry fallback, 8 ta mashq detektori. |
| **Bosqich 5** | Rule engine, event manager (debounce/cooldown/dedup), scoring engine, kritik oqim, SUSPECT | ⏳ KUTILMOQDA | 1 xato = 1 event, 1 ovoz, 1 penalty kafolati. |
| **Bosqich 6** | Evidence recorder (ring buffer, SHA-256 zanjir), 3-tilli Audio service (.wav to'plami), storage manager | ⏳ KUTILMOQDA | 3 tilda to'liq audio tekshiruvi va audit. |
| **Bosqich 7** | QML UI: 3-maketli ekran klaviaturasi, til almashtirgich, 9 ta ekran, popup navbati, 3-tilli hisobotlar | ⏳ KUTILMOQDA | Matn kesilmasligi (clipping), tofu yo'qligi, shrift embed. |
| **Bosqich 8** | ONNX backend (CUDA, TensorRT, DirectML), o'qitish/export/baholash skriptlari, replay tizimi | ⏳ KUTILMOQDA | Mock vs Real ONNX, precision/recall benchmark. |
| **Bosqich 9** | Ed25519 offline aktivatsiya, tolerant Machine ID, soat himoyasi, Admin License Generator | ⏳ KUTILMOQDA | Asimmetrik kriptografiya, alohida admin vositasi. |
| **Bosqich 10** | Setup Wizard (apparat tekshiruvi, kamera yo'nalishi, kalibrovka ustasi, poligon zonalari, audio test) | ⏳ KUTILMOQDA | Birinchi ishga tushirishda 3 tilda interaktiv usta. |
| **Bosqich 11** | Watchdog, diagnostika zipi, yangilash/rollback, Nuitka build, Inno Setup 3 tilda (.isl) | ⏳ KUTILMOQDA | Windows installer, uz-Latn.isl, uz-Cyrl.isl, Russian.isl. |
| **Bosqich 12** | Yakuniy sifat: check_translations, ovoz to'plami testi, soak (2 soat), 3 til skrinshotlari, hujjatlar | ⏳ KUTILMOQDA | Demo ishga tushirish: uz-Latn, uz-Cyrl, ru. |

---

## Bajarilgan Ishlar (Bosqich 1)
- [x] `config/rules.yaml`: Barcha 9 ta qoidaga 3 ta tilda to'liq pasportlar yozildi (`uz-Latn`, `uz-Cyrl`, `ru`).
- [x] `src/driving_eval/core/config_schema.py`: `RuleTranslation`, multilingual `RuleItem` (`get_title(lang)`, `get_screen_text(lang)`, `get_voice_text(lang)`, `get_voice_file(lang)`), `supported_languages: ["uz-Latn", "uz-Cyrl", "ru"]` qo'shildi.
- [x] `src/driving_eval/i18n/catalogs/`: `uz-Latn.json`, `uz-Cyrl.json`, `ru.json` to'liq 100% key parity bilan tuzildi.
- [x] `src/driving_eval/i18n/service.py`: `I18nService` yaratildi, ICU plural qoidalari (ruscha: one, few, many; o'zbekcha: other), qat'iy fallback zanjiri, til almashtirish signali, tezlik/raqam/sana formatlash.
- [x] `src/driving_eval/i18n/check_translations.py`: CLI linter va `TRANSLATION_REVIEW.md` generatori yaratildi.
- [x] DB Schema va Migratsiya 2: `test_sessions` jadvaliga `mode` (`TRAINING`/`ASSESSMENT`) va `language` ustunlari qo'shildi; `license_state`, `consent_log`, `app_settings` jadvallari yaratildi; `DatabaseRepository` kengaytirildi.
- [x] Unit testlar: `tests/unit/test_i18n.py` da 9 ta yangi test qo'shildi, jami 72 ta test 100% yashil o'tdi.

---

## Ochiq Masalalar va Keyingi Qadam (Bosqich 2)
- [ ] Bosqich 2: Ikki darajali qat'iy State Machine (Application State Machine + Exam State Machine).
- [ ] Application darajasidagi holatlar: `UNLICENSED`, `SETUP_REQUIRED`, `READY`.
- [ ] Exam darajasidagi holatlar: `IDLE`, `BOOT`, `READY`, `PRECHECK`, `CAMERA_CHECK`, `SYSTEM_CHECK`, `TEST_READY`, `TEST_ACTIVE`, `FINISH_DETECTED`, `VEHICLE_STOPPED`, `FINALIZING`, `RESULT_READY`, `COMPLETED`, `CRITICAL_VIOLATION`, `TERMINATED`, `INTERRUPTED`.
- [ ] Quvvat uzilganda (power loss) tiklash va tranzaksiya yaxlitligi testlari.
