# LOYIHA BOSQICHLARI VA PROGRESS (PROGRESS.md)

Ushbu hujjat loyihaning har bir bosqichidagi bajarilgan ishlar, testlar holati, ochiq masalalar va keyingi qadamlarni aniq qayd etadi. Har bir yirik o'zgarishdan keyin yangilanadi.

---

## Holat Xulosasi (Current Status)
- **Hozirgi Bosqich**: Bosqich 6 yakunlandi -> Bosqich 7 ga o'tish tayyor.
- **Git Holati**: Bosqich 5 commit qilingan (`05e4541`), Bosqich 6 kiritildi.
- **Mavjud Testlar**: 103 ta test yashil (100% PASS), 86%+ coverage.
- **Ruff & Mypy**: 0 xato (100% toza).
- **Lokalizatsiya**: 3 ta til (`uz-Latn`, `uz-Cyrl`, `ru`) 100% to'liq, 36 ta 16-bit 44.1kHz WAV fayl, dynamic language switcher, 0 ta unreviewed qator.

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
| **Bosqich 6** | Evidence recorder (ring buffer, SHA-256 zanjir), 3-tilli Audio service (.wav to'plami), storage manager | ✅ TUGALLANDI | 4-kamerali kompozitli dalillar paketi (`before`, `event`, `after`, `composite.jpg`, `event.mp4`, `metadata.json`), kriptografik xesh tekshiruvi, 3 ta tilda 36 ta WAV audio to'plami va USB eksport manifesti (103 ta test PASS). |
| **Bosqich 7** | QML UI: 3-maketli ekran klaviaturasi, til almashtirgich, 9 ta ekran, popup navbati, 3-tilli hisobotlar | ⏳ BOSHLANMOQDA | Matn kesilmasligi (clipping), tofu yo'qligi, shrift embed. |
| **Bosqich 8** | ONNX backend (CUDA, TensorRT, DirectML), o'qitish/export/baholash skriptlari, replay tizimi | ⏳ KUTILMOQDA | Mock vs Real ONNX, precision/recall benchmark. |
| **Bosqich 9** | Ed25519 offline aktivatsiya, tolerant Machine ID, soat himoyasi, Admin License Generator | ⏳ KUTILMOQDA | Asimmetrik kriptografiya, alohida admin vositasi. |
| **Bosqich 10** | Setup Wizard (apparat tekshiruvi, kamera yo'nalishi, kalibrovka ustasi, poligon zonalari, audio test) | ⏳ KUTILMOQDA | Birinchi ishga tushirishda 3 tilda interaktiv usta. |
| **Bosqich 11** | Watchdog, diagnostika zipi, yangilash/rollback, Nuitka build, Inno Setup 3 tilda (.isl) | ⏳ KUTILMOQDA | Windows installer, uz-Latn.isl, uz-Cyrl.isl, Russian.isl. |
| **Bosqich 12** | Yakuniy sifat: check_translations, ovoz to'plami testi, soak (2 soat), 3 til skrinshotlari, hujjatlar | ⏳ KUTILMOQDA | Demo ishga tushirish: uz-Latn, uz-Cyrl, ru. |

---

## Bajarilgan Ishlar (Bosqich 6)
- [x] `EvidenceRecorder` kengaytirildi: 4-kamerali aylana (ring) bufer, `before.jpg`, `event.jpg`, `after.jpg`, 4 kamera umumiy tasviri (`composite.jpg`), `event.mp4` va `metadata.json`.
- [x] Dalillar paketi xesh yaxlitligi tekshiruvi (`verify_package_integrity`): fayl tahrirlangan yoki o'chirilgan bo'lsa SQLite zanjiridagi SHA-256 xesh orqali darhol soxtalashtirish fosh qilinadi.
- [x] 3 ta tilda to'liq audio to'plami: Har bir til (`uz-Latn`, `uz-Cyrl`, `ru`) uchun 12 tadan, jami 36 ta 16-bit 44.1kHz PCM WAV fayllari generatsiya qilindi va `VOICE_SCRIPTS.md` ga kiritildi.
- [x] `AudioService`: 3-tilli papkalar iyerarxiyasi bo'yicha qidiruv, avtomatlashtirilgan zaxira (strict fallback to `uz-Latn`), Windows mahalliy audio ijrosi, ustuvorlikli (critical priority) navbat mexanizmi.
- [x] `StorageManager`: SSD disk bo'sh joyini kuzatish, xavfsiz avto-tozalash (faqat yakunlangan sessiyalar o'chiriladi, DB va faol sessiyaga tegilmaydi), USB eksporti paytida barcha fayllar SHA-256 xeshi bilan `export_manifest.json` yaratilishi va admin audit logiga yozilishi.
- [x] 103/103 test yashil (100% PASS), 0 ruff xatosi, 0 mypy xatosi.

---

## Ochiq Masalalar va Keyingi Qadam (Bosqich 7)
- [ ] Bosqich 7: QML UI: 3-maketli virtual sensorli klaviatura (`uz-Latn`, `uz-Cyrl`, `ru`), shrift integratsiyasi, 3 tilda PDF va CSV hisobotlari generatori, barcha 9 ta ekranning 3 tilda ko'rinish auditlari.
