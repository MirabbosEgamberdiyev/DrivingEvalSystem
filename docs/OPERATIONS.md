# EKSPLUATATSIYA VA NOSOZLIKLAR BO'YICHA YO'RIQNOMA (OPERATIONS.md)

Ushbu yo'riqnoma imtihon markazi inspektorlari va texnik operatorlar uchun kundalik ishlash tartibini belgilaydi.

---

## 1. Kundalik Ish Boshlash Tartibi
1. Avtomobil dvigatelini yoqing. Sanoat kompyuteri 15-20 soniyada yuklanadi va ekranda asosiy oyna (HOME) ochiladi.
2. Nomzodning pasport ma'lumotlarini kiriting va **[TIZIMNI TEKSHIRISH (PRE-CHECK)]** tugmasini bosing.
3. Barcha 15 ta ko'rsatkich (4 kamera, kalibrovka, AI, disk, sensorlar) YASHIL bo'lishini kuting.
4. Agar birorta komponent QIZIL bo'lsa, test boshlanishi bloklanadi. Ko'rsatilgan sababni bartaraf qilib, **[QAYTA TEKSHIRISH]** ni bosing.
5. Tayyor bo'lgach, nomzod avtomobilni start chizig'iga olib keladi va **[TESTNI BOSHLASH]** tugmasi bosiladi.

---

## 2. Favqulodda Nosozliklar va Bartaraf Qilish (Troubleshooting)

### A. Kamera Uzilib Qolishi (Camera Disconnect)
- **Alomat**: Pre-checkda `[FAIL] CAMERA_<NAME>_STREAM` xabari chiqadi yoki test paytida ogohlantirish beriladi.
- **Yechim**: Kamera kabelini (USB / GMSL2) mahkamlang. [QAYTA TEKSHIRISH] ni bosing.

### B. Kalibrovka Siljishi (Calibration Drift)
- **Alomat**: Pre-checkda `Kamera kalibrovka siljishi aniqlandi (>15px)` xabari chiqadi.
- **Yechim**: Kamera mahkamlagichi siljigan yoki bo'shashgan. Kamerani referens holatiga to'g'rilang yoki qayta kalibrovka qiling.

### C. Quvvat To'satdan Uzilishi (Akkumulyator uzilishi)
- **Xavfsizlik**: Har bir jarima va hodisa darhol SQLite WAL rejimida diskka commit qilingan.
- **Yechim**: Tizim qayta yoqilganda avtomatik ravishda yakunlanmagan sessiyani aniqlaydi va uni xavfsiz holda `INTERRUPTED` deb arxivlaydi. Hech qanday ma'lumot yo'qolmaydi.

### D. Diskda Bo'sh Joy Qolmasligi
- **Alomat**: `STORAGE_SPACE` pre-checkda qizil yonadi (<10 GB bo'sh joy).
- **Yechim**: USB fleshkani ulang va Sozlamalar bo'limidan eski sessiyalar dalillarini USB ga eksport qilib, tozalang.
