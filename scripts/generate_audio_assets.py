"""Generates valid 16-bit 44.1kHz PCM WAV audio files for all 3 languages."""

import math
import struct
import wave
from pathlib import Path

AUDIO_DIR = Path("data/audio")

# 12 official audio cues
AUDIO_FILES = {
    "seatbelt_unfastened.wav": 520.0,
    "cone_touch.wav": 440.0,
    "stop_line_violation.wav": 480.0,
    "hill_rollback.wav": 390.0,
    "speed_exceeded.wav": 600.0,
    "indicator_missed.wav": 500.0,
    "parking_out_of_bounds.wav": 460.0,
    "critical_collision.wav": 300.0,
    "exercise_sequence_broken.wav": 350.0,
    "test_start.wav": 587.0,
    "test_passed.wav": 880.0,
    "test_failed.wav": 260.0,
}

LANGUAGES = ["uz-Latn", "uz-Cyrl", "ru"]


def create_pcm_wav(file_path: Path, frequency: float, duration: float = 1.2, sample_rate: int = 44100) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    num_samples = int(duration * sample_rate)
    amplitude = 16000

    with wave.open(str(file_path), "wb") as wav:
        wav.setnchannels(1)  # Mono
        wav.setsampwidth(2)  # 16-bit PCM
        wav.setframerate(sample_rate)

        frames = bytearray()
        for i in range(num_samples):
            t = float(i) / sample_rate
            # Dual frequency harmonic tone
            val = int(amplitude * 0.7 * math.sin(2.0 * math.pi * frequency * t))
            val += int(amplitude * 0.3 * math.sin(2.0 * math.pi * (frequency * 1.5) * t))

            # Envelope fade-in and fade-out to prevent clicks
            if i < 1500:
                val = int(val * (i / 1500.0))
            elif i > num_samples - 1500:
                val = int(val * ((num_samples - i) / 1500.0))

            val = max(-32767, min(32767, val))
            frames.extend(struct.pack("<h", val))

        wav.writeframes(frames)


def main() -> None:
    for lang in LANGUAGES:
        lang_dir = AUDIO_DIR / lang
        lang_dir.mkdir(parents=True, exist_ok=True)
        for fname, freq in AUDIO_FILES.items():
            out_file = lang_dir / fname
            create_pcm_wav(out_file, freq)
            print(f"Generated: {out_file}")

    # Also generate comprehensive VOICE_SCRIPTS.md
    scripts_doc = """# 3-TILLI OVOZLI XABARLAR REYESTRI VA DIKTOR MATNLARI (VOICE_SCRIPTS.md)

100% Offline 4-Kamerali Avtomatlashtirilgan Imtihon Tizimi uchun rasmiy diktor matnlari.

## Texnik Format
- **Format**: WAV (PCM 16-bit)
- **Chastotalar**: 44.1 kHz, Mono
- **Joylashuv**:
  - `data/audio/uz-Latn/` (O'zbek lotin)
  - `data/audio/uz-Cyrl/` (Ўзбек кирилл)
  - `data/audio/ru/` (Русский)

---

## Rasmiy Diktor Matnlari Jadvali

| № | Fayl Nomi | Qoida Kodi | O'zbek (lotin) | Ўзбек (кирилл) | Русский |
|---|---|---|---|---|---|
| 1 | `seatbelt_unfastened.wav` | `SEATBELT_UNFASTENED` | "Diqqat! Xavfsizlik kamarini taqing." | "Диққат! Хавфсизлик камарини тақинг." | "Внимание! Пристегните ремень безопасности." |
| 2 | `cone_touch.wav` | `CONE_TOUCH` | "Diqqat! Belgilangan konusga tegdilar." | "Диққат! Белгиланган конусга тегдилар." | "Внимание! Зафиксировано касание конуса." |
| 3 | `stop_line_violation.wav` | `STOP_LINE_VIOLATION` | "Stop chizig'i qoidasi buzildi." | "Стоп чизиғи қоидаси бузилди." | "Внимание! Нарушено правило стоп-линии." |
| 4 | `hill_rollback.wav` | `HILL_ROLLBACK` | "Avtomobil estakadada orqaga sirg'aldi." | "Автомобиль эстакадада орқага сирғалди." | "Откат автомобиля назад на эстакаде." |
| 5 | `speed_exceeded.wav` | `SPEED_EXCEEDED` | "Tezlik oshirildi. Tezlikni pasaytiring." | "Тезлик оширилди. Тезликни пасайтиринг." | "Превышение скорости. Снизьте скорость движения." |
| 6 | `indicator_missed.wav` | `INDICATOR_MISSED` | "Burilish chirog'i yoqilmadi." | "Бурилиш чироғи ёқилмади." | "Не включен сигнал указателя поворота." |
| 7 | `parking_out_of_bounds.wav` | `PARKING_OUT_OF_BOUNDS` | "Avtomobil to'xtash chegarasidan chiqib ketdi." | "Автомобиль тўхташ чегарасидан чиқиб кетди." | "Автомобиль вышел за границы зоны парковки." |
| 8 | `critical_collision.wav` | `CRITICAL_COLLISION` | "Kritik qoidabuzarlik. Imtihon to'xtatildi." | "Критик қоидабузарлик. Имтиҳон тўхтатилди." | "Критическое нарушение. Экзамен остановлен." |
| 9 | `exercise_sequence_broken.wav` | `EXERCISE_SEQUENCE_BROKEN` | "Kritik xato. Mashqlar tartibi buzildi. Imtihon yakunlandi." | "Критик хато. Машқлар тартиби бузилди. Имтиҳон якунланди." | "Критическая ошибка. Нарушен порядок упражнений. Экзамен завершен." |
| 10 | `test_start.wav` | `SYSTEM` | "Imtihon boshlandi. Oq yo'l!" | "Имтиҳон бошланди. Оқ йўл!" | "Экзамен начался. В добрый путь!" |
| 11 | `test_passed.wav` | `SYSTEM` | "Tabriklaymiz! Siz imtihondan muvaffaqiyatli o'tdingiz." | "Табриклаймиз! Сиз имтиҳондан муваффақиятли ўтдингиз." | "Поздравляем! Вы успешно сдали экзамен." |
| 12 | `test_failed.wav` | `SYSTEM` | "Afsuski, siz imtihondan o'ta olmadingiz." | "Афсуски, сиз имтиҳондан ўта олмадингиз." | "К сожалению, вы не сдали экзамен." |
"""
    (AUDIO_DIR / "VOICE_SCRIPTS.md").write_text(scripts_doc, encoding="utf-8")
    print("VOICE_SCRIPTS.md generated successfully.")


if __name__ == "__main__":
    main()
