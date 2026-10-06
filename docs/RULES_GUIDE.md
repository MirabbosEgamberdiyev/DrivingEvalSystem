# QOIDALAR VA BAHOLASH QO'LLANMASI (RULES_GUIDE.md)

Ushbu qo'llanma `config/rules.yaml` faylini boshqarish, rasmiy metodikaga moslashtirish va yangi qoidalar qo'shish tartibini tushuntiradi.

---

## 1. Yagona Manba (Single Source of Truth) Tamoyili
Dastur kodida hech qanday jarima ballari, qoidabuzarlik nomlari yoki ovoz matnlari qattiq kodlanmagan. Barcha komponentlar:
- Monitor (UI popuplari va jadvallar);
- Ovoz xizmati (AudioService);
- SQLite ma'lumotlar bazasi;
- PDF va CSV hisobotlari;
faqat va faqat `config/rules.yaml` faylidan o'qiydi.

---

## 2. Qoida Pasporti Strukturasi

Har bir qoida quyidagi parametrlarga ega:

```yaml
- code: "CONE_TOUCH"                       # Noyob identifikator
  title: "Yo'l belgilovchi konusga tegish" # Qisqa rasmiy nomi
  screen_text: "Konusga tegdingiz!"       # Monitorda chiqadigan matn
  voice_file: "cone_touch.wav"             # audio/uz/ ichidagi audio fayl
  voice_text: "Diqqat! Belgilangan konusga tegdilar." # TTS uchun matn
  penalty: 25                              # Jarima bali (butun son)
  critical: false                          # true bo'lsa test darhol TERMINATED bo'ladi
  debounce_frames: 5                       # Qoidani tasdiqlash uchun ketma-ket kadrlar soni
  cooldown_seconds: 5.0                    # Qayta jarima hisoblanmaslik vaqti (dublikat himoyasi)
  min_confidence: 0.80                     # Minimal AI ishonch chegarasi (past bo'lsa SUSPECT)
  exercise_binding: ["ZMEIKA", "TURN_90"]  # Qaysi mashqlarda faolligi ([] = barchasida)
```

---

## 3. Yangi Qoida Qo'shish Tartibi

Yangi qoida qo'shish uchun:
1. `config/rules.yaml` ga yangi element qo'shiladi.
2. Agar qoida yangi kompyuter ko'rish mantig'ini talab qilsa, `src/driving_eval/rules/plugins/` papkasida `BaseRulePlugin` dan meros oluvchi yangi plugin yaratiladi va `RuleEngine` da ro'yxatga olinadi.
3. Mos ovoz fayli `data/audio/uz/` papkasiga joylashtiriladi (yoki TTS zaxirasiga tayaniladi).
4. Dastur qayta ishga tushirilganda avtomatik ravishda SQLite bazasidagi `rules` jadvalini yangilaydi.
