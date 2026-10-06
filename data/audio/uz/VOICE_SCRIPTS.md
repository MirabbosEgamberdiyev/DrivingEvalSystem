# OVOZLI XABARLAR REYESTRI VA DIKTOR MATNLARI (audio/uz/VOICE_SCRIPTS.md)

Ushbu ro'yxat professional diktor studiyasida yozilishi kerak bo'lgan barcha rasmiy ovozli ogohlantirishlar matni va ularga mos fayl nomlarini o'z ichiga oladi.

## Texnik Format Talablari
- **Format**: WAV (PCM 16-bit)
- **Chastotalar**: 44.1 kHz yoki 22.05 kHz, Mono
- **Maksimal davomiyligi**: Har bir xabar 1.5 - 2.5 soniya oralig'ida (tez va tushunarli aytilishi shart)
- **Normalizatsiya**: -1.0 dB Peak, shovqinlardan tozalangan (Noise-gated)

---

## Ovoz Fayllari va Aniq Matnlar

| № | Fayl Nomi (`rules.yaml`) | Qoida Kodi | Rasmiy Diktor Matni (O'zbek tilida) | Tavsif |
|---|---|---|---|---|
| 1 | `seatbelt_unfastened.wav` | `SEATBELT_UNFASTENED` | "Diqqat! Xavfsizlik kamarini taqing." | Xavfsizlik kamari taqilmaganda |
| 2 | `cone_touch.wav` | `CONE_TOUCH` | "Diqqat! Belgilangan konusga tegdilar." | Konusga tegish qayd etilganda |
| 3 | `stop_line_violation.wav` | `STOP_LINE_VIOLATION` | "Stop chizig'i qoidasi buzildi." | To'xtash chizig'i bosilganda |
| 4 | `hill_rollback.wav` | `HILL_ROLLBACK` | "Avtomobil estakadada orqaga sirg'aldi." | Estakadada >20 sm orqaga ketganda |
| 5 | `speed_exceeded.wav` | `SPEED_EXCEEDED` | "Tezlik oshirildi. Tezlikni pasaytiring." | Avtodrom tezligi oshganda |
| 6 | `indicator_missed.wav` | `INDICATOR_MISSED` | "Burilish chirog'i yoqilmadi." | Burilish signali berilmaganda |
| 7 | `parking_out_of_bounds.wav` | `PARKING_OUT_OF_BOUNDS` | "Avtomobil to'xtash chegarasidan chiqib ketdi." | Parkovkada gabarit buzilganda |
| 8 | `critical_collision.wav` | `CRITICAL_COLLISION` | "Kritik qoidabuzarlik. Imtihon to'xtatildi." | To'siqqa to'qnashuv |
| 9 | `exercise_sequence_broken.wav` | `EXERCISE_SEQUENCE_BROKEN` | "Kritik xato. Mashqlar tartibi buzildi. Imtihon yakunlandi." | Mashq o'tkazib yuborilganda |
| 10 | `test_start.wav` | `SYSTEM` | "Imtihon boshlandi. Oq yo'l!" | Start bosilganda |
| 11 | `test_passed.wav` | `SYSTEM` | "Tabriklaymiz! Siz imtihondan muvaffaqiyatli o'tdingiz." | PASS natijada |
| 12 | `test_failed.wav` | `SYSTEM` | "Afsuski, siz imtihondan o'ta olmadingiz." | FAIL natijada |

---

## Offline Zaxira (Fallback)
Agar diskda biror `.wav` fayl topilmasa yoki buzilgan bo'lsa, tizim ovoz bloklanishiga yo'l qo'ymaydi va avtomatik ravishda **Piper Offline TTS** orqali `voice_text` ni sintez qilib eshittiradi.
