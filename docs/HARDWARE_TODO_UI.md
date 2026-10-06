# REAL SENSORLI DISPLEYDA SINAB KO'RILISHI KERAK BO'LGAN VAZIFALAR (HARDWARE_TODO_UI.md)

Laboratoriya va emulyatsiya sharoitida UI to'liq sinovdan o'tkazildi. Real avtomobil salonidagi sensorli monitorda (in-cabin touchscreen display) quyidagi apparat jihatlari tekshirilishi lozim:

---

## 1. Sensorli Ekran (Touch Panel) Kalibrovkasi va Sezuvchanligi
- [ ] **Sensor turi**: Kapasitiv (Capacitive) yoki rezistiv (Resistive) sensorli panel turini aniqlash. Rezistiv ekranda bosim kuchini, kapasitiv ekranda esa qo'lqop kiygan holatdagi sezgirlikni tekshirish.
- [ ] **Ko'p nuqtali teginish (Multi-touch) va kaft himoyasi (Palm Rejection)**: Haydovchi monitorni ushlaganda yoki barmoqlari tasodifan tekkanda noto'g'ri buyruq ketmasligi uchun xinput / evdev drayverida barmoq o'lchamini sozlash.
- [ ] **Tebranish (Vibration) sharoitida bosish**: Avtomobil notekis yo'lda harakatlanayotganda 96x72 px tugmalarni bir urinishda bosish qulayligini amalda tekshirish.

---

## 2. Optik Ko'rinuvchanlik va Yorug'lik
- [ ] **Quyosh nuri (Sunlight Readability)**: Tushki quyosh old oynadan to'g'ridan-to'g'ri monitorga tushganda matnlar va ranglar o'qilishini baholash (kamida 800-1000 nits yorqinlikdagi sanoat paneli tavsiya etiladi).
- [ ] **Tungi rejim**: Tunda haydovchining ko'ziga qattiq yorug'lik tushmasligi uchun displey yorqinligini avtomatik (yoki qo'lda) pasaytirish (Backlight PWM nazorati).

---

## 3. GPU Dvigateli va Kiosk Rejimi (Linux / Embedded)
- [ ] **Grafik Backend (EGLFS vs XCB)**: Ubuntu yoki Yocto Linux tizimida Qt Quick renderlashini sinash. EGLFS (to'g'ridan-to'g'ri KMS/DRM orqali) xorg yuklamasdan 60 FPS silliqlik beradi.
- [ ] **Ekran uyqusi (Screen Blanking / DPMS) ni o'chirish**: `xset s off -dpms` yoki systemd orqali ekran hech qachon qorayib qolmasligini ta'minlash.
- [ ] **Kursor ko'rinmasligi**: Sensorli rejimda sichqoncha strelkasi ko'rinmasligi uchun `QT_QPA_EGLFS_HIDECURSOR=1` parametrini qo'llash.
