# TEXNIK VA OPERATSION TAXMINLAR (ASSUMPTIONS.md)

Ushbu hujjat loyihaning texnik, operatsion va biznes chegaralaridagi oqilona taxminlarni jamlaydi.

---

## 1. Apparat va Operatsion Muhit
1. **OS**: Asosiy foydalanuvchi tizimi — Windows 10 (Build 19041+) yoki Windows 11 x64.
2. **Kamera Ulanishi**: 4 ta kamera avtomobilning to'rt tomoniga (old, orqa, chap, o'ng) qat'iy mahkamlangan va burilmaydi. Kameralar tebranishga chidamli avtomobil korpusiga o'rnatilgan.
3. **USB va Quvvat**:
   - USB orqali ulanadigan kameralar uchun kamida 2 ta alohida USB Host Controller (PCIe USB kengaytirish kartasi yoki anakartdagi mustaqil kontrollerlar) mavjud yoki kameralar Ethernet PoE (RTSP) orqali ulangan.
   - Kompyuter avtomobilning 12V/24V tarmog'iga sifatli DC-DC stabilizator (UPS/akkumulyator zaxirasi) orqali ulangan.
4. **Sensorlar**:
   - GPS/GNSS qabul qiluvchi ochiq osmon ostida ishlaydi (kamida 8 ta yo'ldosh).
   - OBD-II adapteri standart ELM327 / STN1170 protokollarini (ISO 15765-4 CAN 500kbps) qo'llab-quvvatlaydi.

---

## 2. Poligon va Mashqlar
1. **Poligon Standarti**:
   - Mashq zonalari rasmiy avtomaktab yoki YPX imtihon poligonlari standartlariga mos keladi (start, estakada, zmeyka, 90 gradus burilish, parallel parkovka, orqaga harakat, stop chizig'i, finish).
   - Konuslar rangli (to'q sariq/oq tasmali), chiziqlar oq yoki sariq bo'yoq bilan chizilgan.
2. **Qoidalar Manbasi**:
   - Amaldagi jarima ballari va qoida nomlari rasmiy metodikaga mos keladigan namunaviy parametrlar asosida olingan (`TODO: rasmiy metodika bilan almashtirilsin` deb belgilangan).

---

## 3. Litsenziyalash va Xavfsizlik
1. **Offline Aktivatsiya**:
   - Har bir mijoz kompyuteri o'rnatishdan keyin ekranda ko'ringan `Machine ID` kodini (matn yoki QR shaklida) ma'murga yuboradi.
   - Ma'mur o'zining yopiq `Admin License Generator` dasturi orqali Ed25519 raqamli imzolangan litsenziya faylini generatsiya qilib beradi.
   - Dastur hech qachon internet orqali litsenziyani tekshirmaydi.
2. **Soat va Vaqt Xavfsizligi**:
   - Kompyuterning BIOS batareyasi ishchi holatda deb hisoblanadi.
   - Soatning orqaga surilishi DB dagi SHA-256 zanjiridagi oxirgi sessiya vaqti bilan tekshiriladi.

---

## 4. Ko'p Tillilik (i18n/l10n)
1. **Tillar Qamrovi**:
   - Tizim 3 ta tilni qo'llab-quvvatlaydi: `uz-Latn` (standart), `uz-Cyrl`, `ru`.
   - Foydalanuvchi birinchi marta kirganda tilni tanlaydi.
   - Rus tilidagi matnlar o'zbekchadan 20-35% uzunroq bo'lishi hisobga olingan.
2. **Ovozli Xabarlar**:
   - Har bir til uchun barcha qoidalar bo'yicha to'liq diktor ovozi (.wav) taqdim etiladi.
   - Sifatli offline TTS topilmagan taqdirda, audio yo'qligi pre-check diagnostikasida ko'rsatiladi va rasmiy imtihon bloklanadi.

---

## 5. Audit va Ishlab Chiqish Muhiti Cheklovlari
1. **AI ONNX Runtime va Modellar**:
   - Ishlab chiqish va sinov muhitida DirectML GPU yoki CUDA drayveri mavjud bo'lmaganda yoki ONNX runtime o'rnatilmaganda, tizim `MockDetector` orqali to'liq simulyatsiya rejimiga o'tadi va buni UI'da ochiq ko'rsatadi (`[SIMULATION]`).
   - Ishlab chiqarish (production) avtomobilida ONNX model fayllari (`data/models/yolov8_autodrome.onnx`) litsenziyalangan drayver bilan o'rnatiladi.
2. **Ovozli Fayllar (WAV)**:
   - Hozirgi repoda mavjud 36 ta WAV fayllari funksional sinovlar uchun sintetik audiodir. Haqiqiy diktor ovozlari avtomaktab metodikasi bo'yicha maxsus yozib olinib almashtiriladi (`VOICE_TODO.md`).
3. **Datchiklar va COM Portlar**:
   - Haqiqiy avtomobil bo'lmagan muhitda GPS/OBD portlari virtual/simulyatsiya rejimida tekshiriladi; bu holat `HARDWARE_REQUIRED` deb tasniflanadi.

