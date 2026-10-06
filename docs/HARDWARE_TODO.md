# APPARAT TA'MINOTI (HARDWARE) DA SINAB KO'RILISHI KERAK BO'LGAN VAZIFALAR (HARDWARE_TODO.md)

Laboratoriya muhitida dasturiy ta'minot arxitekturasi, state machine, DB, AI interfeyslari, simulyatsiya va qoidalar to'liq sinovdan o'tkazildi. Real avtomobilga o'rnatishda jismoniy apparat (hardware) bo'yicha quyidagi vazifalar bajarilishi shart:

---

## 1. Kameralar va Optika
- [ ] **USB 3.0 Bandwidth tekshiruvi**: 4 ta USB kamerani bitta USB hub orqali ulamang! Har bir kamera alohida USB 3.0 xost-kontrolleriga (PCIe USB karta) ulanishi yoki GMSL2 orqali Jetson Orin platasiga ulanishi lozim.
- [ ] **Fisheye ob'yektiv kalibrovkasi**: Har bir kameraning aniq fokus masofasi va distorsiya koeffitsientlari shaxmat taxtasi bilan real avtomobilda qayta o'lchanishi kerak.
- [ ] **Tebranishga chidamlilik**: Kameralar kronshteynlari avtomobil silkinishlarida burchakni o'zgartirmasligi uchun qattiq metall qisqichlar bilan qotirilishi lozim.

---

## 2. Sensorlar va Bort Tarmoqlari
- [ ] **OBD-II CAN Shina Mosligi**: Turli avtomobillarda (Cobalt, Lacetti, Onix) kamar sensori va g'ildirak tezligi PID kodlari farq qilishi mumkin. Real avtomobilda CAN xabarlari logi olinishi va PID qiymatlari tekshirilishi kerak.
- [ ] **IMU Orientatsiyasi**: Akselerometr avtomobil o'qlariga (X: o'ng, Y: old, Z: yuqori) qat'iy parallel o'rnatilishi va estakada burchagi kalibrovka qilinishi kerak.
- [ ] **GPS Antenna Joylashuvi**: GNSS antenna avtomobil tomiga (metall sirt ustiga) magnitli asosda o'rnatilishi va binolar soyasida HDOP ko'rsatkichi tekshirilishi lozim.

---

## 3. Quvvat va Elektr Ta'minoti
- [ ] **Intellektual Quvvat Bloki (Automotive DC-DC UPS)**: Dvigatel o't oldirilganda (starter ishlaganda) 12V akkumulyatordagi kuchlanish 9V gacha tushib ketadi. Kompyuter o'chib qolmasligi uchun superkondensatorli yoki batareyali Automotive UPS o'rnatilishi shart.
- [ ] **Ignition Signal (ACC)**: Avtomobil o'chirilganda kompyuterga `SIGTERM` yuborib, tizimni xavfsiz o'chirish (clean shutdown) tizimi ulanishi kerak.

---

## 4. Sun'iy Intellekt Modeli (Model Weights)
- [ ] **Real Avtodrom Ma'lumotlarini Yig'ish**: Har xil ob-havo va kun vaqtlarida kamida 5,000 ta kadr yozib olish va CVAT da belgilash (`ml_training/dataset_spec.md` bo'yicha).
- [ ] **YOLOv8/v11 o'qitish va TensorRT export**: `train_yolo.py` va `export_onnx_trt.py` skriptlari orqali real og'irliklarni yaratish va Jetson Orin apparatida tezligini tekshirish.
