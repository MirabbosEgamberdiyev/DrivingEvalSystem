# LOYIHA BOSQICHLARI VA PROGRESS (PROGRESS.md)

Ushbu hujjat loyihaning har bir bosqichidagi bajarilgan ishlar, testlar holati, ochiq masalalar va keyingi qadamlarni aniq qayd etadi. Har bir yirik o'zgarishdan keyin yangilanadi.

---

## Holat Xulosasi (Current Status)
- **Hozirgi Bosqich**: Bosqich 2 yakunlandi -> Bosqich 3 ga o'tish tayyor.
- **Git Holati**: Bosqich 1 commit qilingan (`c2d30d2`), Bosqich 2 kiritildi.
- **Mavjud Testlar**: 80 ta test yashil (100% PASS), 84% coverage.
- **Ruff & Mypy**: 0 xato (100% toza, 80 ta fayl tekshirildi).
- **Lokalizatsiya**: 3 ta til (`uz-Latn`, `uz-Cyrl`, `ru`) 100% to'liq, ICU plural qo'llab-quvvatlangan, 100% key parity, 0 ta unreviewed qator.

---

## Bosqichlar Rejasi va Bajarilish Holati

| Bosqich | Tavsif | Holat | Izoh |
|---|---|---|---|
| **Bosqich 0** | Tahlil, tarixiy ziddiyatlarni hal qilish, `SPEC.md`, `DECISIONS.md`, `ASSUMPTIONS.md`, `PROGRESS.md` | ✅ TUGALLANDI | Barcha 11 ta savol va i18n qarorlari asoslab yozildi (`e8afc63`). |
| **Bosqich 1** | Skelet, 3-tilli `rules.yaml`, pydantic sxemalar, DB migratsiyalar, `i18n_service` va `check_translations.py` | ✅ TUGALLANDI | 3 til kataloglari, ICU plural qoidalari, strict fallback, DB migratsiya 2, linter va testlar to'liq ishga tushdi (`c2d30d2`). |
| **Bosqich 2** | State machine (Dastur: UNLICENSED/SETUP/READY; Test: IDLE -> COMPLETED) va testlar | ✅ TUGALLANDI | 2 darajali state machine, ruxsat etilgan o'tishlar matritsasi, gating, audit logging va power-loss tiklash. |
| **Bosqich 3** | Camera service (Windows MF/DirectShow, RTSP, sim), pre-check, MockDetector, Vertikal Kesim (`--simulate`) | ⏳ BOSHLANMOQDA | Til tanlash -> Home -> Precheck -> Test -> Finish vertikal kesimi. |
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

## Bajarilgan Ishlar (Bosqich 2)
- [x] `ApplicationStateMachine` yaratildi: `UNLICENSED`, `SETUP_REQUIRED`, `READY` holatlari va o'tishlar tekshiruvi.
- [x] `ExamStateMachine` kengaytirildi: `app_state_machine` bilan bog'landi, `READY` bo'lmaguncha imtihon boshlanishi qat'iy bloklandi.
- [x] Ruxsat etilgan va taqiqlangan o'tishlar matritsasi to'liq testlandi (parametrlashtirilgan testlar).
- [x] Quvvat uzilganda xavfsiz holatga o'tish (`INTERRUPTED`) va `SessionRecoveryService` integratsiyasi sinovdan o'tkazildi.
- [x] Barcha o'tishlar va xatolar SQLite `system_logs` ga avtomatik yozilishi audit qilindi.
- [x] 80/80 test yashil (100% PASS), 0 ruff, 0 mypy.

---

## Ochiq Masalalar va Keyingi Qadam (Bosqich 3)
- [ ] Bosqich 3: Camera service (Windows DirectShow / Media Foundation, RTSP, simulyatsiya), 12 ta komponent pre-check tekshiruvi, MockDetector, va `--simulate` vertikal kesimi.
