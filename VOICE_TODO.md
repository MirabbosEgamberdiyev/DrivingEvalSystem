# OVOZLI XABARLAR YOZISH REJASI VA DIKTOR SKRIPTI (VOICE_TODO.md)

**Loyiha:** Offline 4-Camera AI Driving Training & Evaluation System  
**Holat:** Hozirgi `data/audio/*/*.wav` fayllari funksional testlar uchun sintetik ton (beep) hisoblanadi.  
**Vazifa:** Professional diktorlar yordamida quyidagi 12 ta ovozli xabarni 3 ta tilda (`uz-Latn`, `uz-Cyrl`, `ru`) yozib olish va integratsiya qilish.

---

## 1. TEXNIK TALABLAR (AUDIO SPECIFICATIONS)
- **Format:** WAV (Uncompressed PCM)
- **Kanal:** Mono (1.0)
- **Chastotalar kengligi:** 44,100 Hz yoki 48,000 Hz
- **Bit chuqurligi:** 16-bit PCM
- **Ovoz balandligi:** Integrated Loudness: -14 LUFS (True Peak: -1.0 dBTP)
- **Shovqin darajasi:** Noise floor < -60 dBFS
- **Davomiyligi:** Har bir jumla 1.5 – 3.0 soniya oralig'ida aniq, ravshan va xotirjam aytilishi shart.

---

## 2. 12 TA ASOSIY XABAR SKRIPTI (3 TILDA)

### 1. `test_start.wav` (Imtihon boshlanishi)
- **uz-Latn:** "Imtihon boshlandi. Harakatni boshlang."
- **uz-Cyrl:** "Имтиҳон бошланди. Ҳаракатни бошланг."
- **ru:** "Экзамен начался. Начните движение."

### 2. `seatbelt_unfastened.wav` (Xavfsizlik kamari)
- **uz-Latn:** "Xavfsizlik kamarini taqing."
- **uz-Cyrl:** "Хавфсизлик камарини тақинг."
- **ru:** "Пристегните ремень безопасности."

### 3. `cone_touch.wav` (Konusga tegish)
- **uz-Latn:** "Diqqat! Konusga tegildi. Jarima 25 ball."
- **uz-Cyrl:** "Диққат! Конусга тегилди. Жарима 25 балл."
- **ru:** "Внимание! Наезд на конус. Штраф 25 баллов."

### 4. `stop_line_violation.wav` (Stop-chizig'ini bosish)
- **uz-Latn:** "Stop chizig'i qoidasi buzildi. Jarima 20 ball."
- **uz-Cyrl:** "Стоп чизиғи қоидаси бузилди. Жарима 20 балл."
- **ru:** "Нарушение стоп-линии. Штраф 20 баллов."

### 5. `hill_rollback.wav` (Estakadada orqaga ketish)
- **uz-Latn:** "Estakadada orqaga ketish qayd etildi. Jarima 25 ball."
- **uz-Cyrl:** "Эстакадада орқага кетиш қайд этилди. Жарима 25 балл."
- **ru:** "Откат назад на эстакаде. Штраф 25 баллов."

### 6. `parking_out_of_bounds.wav` (Parkovka chizig'idan chiqish)
- **uz-Latn:** "Parkovka chegarasidan chiqildi. Jarima 25 ball."
- **uz-Cyrl:** "Парковка чегарасидан чиқилди. Жарима 25 балл."
- **ru:** "Выезд за границы парковки. Штраф 25 баллов."

### 7. `indicator_missed.wav` (Burilish chirog'i yoqilmadi)
- **uz-Latn:** "Burilish chirog'i yoqilmadi. Jarima 10 ball."
- **uz-Cyrl:** "Бурилиш чироғи ёқилмади. Жарима 10 балл."
- **ru:** "Указатель поворота не включен. Штраф 10 баллов."

### 8. `speed_exceeded.wav` (Tezlik oshirildi)
- **uz-Latn:** "Tezlik me'yordan oshirildi. Jarima 15 ball."
- **uz-Cyrl:** "Тезлик меъёрдан оширилди. Жарима 15 балл."
- **ru:** "Превышение скорости. Штраф 15 баллов."

### 9. `exercise_sequence_broken.wav` (Mashqlar ketma-ketligi buzildi)
- **uz-Latn:** "Mashqlar ketma-ketligi buzildi."
- **uz-Cyrl:** "Машқлар кетма-кетлиги бузилди."
- **ru:** "Нарушена последовательность упражнений."

### 10. `critical_collision.wav` (Kritik to'qnashuv / Xavfli holat)
- **uz-Latn:** "Kritik qoidabuzarlik! To'qnashuv xavfi. Imtihon to'xtatildi."
- **uz-Cyrl:** "Критик қоидабузарлик! Тўқнашув хавфи. Имтиҳон тўхтатилди."
- **ru:** "Критическое нарушение! Опасное сближение. Экзамен остановлен."

### 11. `test_passed.wav` (Imtihondan muvaffaqiyatli o'tildi)
- **uz-Latn:** "Tabriklaymiz! Siz imtihondan muvaffaqiyatli o'tdingiz."
- **uz-Cyrl:** "Табриклаймиз! Сиз имтиҳондан муваффақиятли ўтдингиз."
- **ru:** "Поздравляем! Вы успешно сдали экзамен."

### 12. `test_failed.wav` (Imtihondan yiqildi)
- **uz-Latn:** "Afsuski, imtihon topshirilmadi. Ball yetarli emas."
- **uz-Cyrl:** "Афсуски, имтиҳон топширилмади. Балл етарли эмас."
- **ru:** "К сожалению, экзамен не сдан. Недостаточно баллов."

---

## 3. FAYL PAPKALARI JOYLASHTIRILISHI
Yozilgan fayllar quyidagi kataloglarga joylashtiriladi:
- `data/audio/uz-Latn/<file_name>.wav`
- `data/audio/uz-Cyrl/<file_name>.wav`
- `data/audio/ru/<file_name>.wav`
