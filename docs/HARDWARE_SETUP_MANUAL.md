# Avtomobilga O'rnatish va Apparat Qismlari Qo'llanmasi (Hardware Setup Manual)

Ushbu qo'llanma imtihon avtomobillariga 4 kamerali avtomatlashtirilgan sun'iy intellekt tizimini professional o'rnatish, simlarni tortish, quvvat manbai va kalibrovka qilish bo'yicha texnik ko'rsatmalarni o'z ichiga oladi.

---

## 1. Tizimning Apparat Arxitekturasi

```
 +-------------------------------------------------------------------+
 |                        AVTOMOBIL AKKUMULYATORI (12V)              |
 +-------------------------------------------------------------------+
                                   |
                     [ 12V Avtomobil Himoya Saqlagichi ]
                                   |
         [ Avtomobil Stabilizatori (DC-DC 12V -> 19V / M4-ATX) ]
           (Starter aylanganda kuchlanish 8V ga tushishidan himoya)
                                   |
 +-------------------------------------------------------------------+
 |             SANOAT KOMPYUTERI (Intel i5/i7, 16GB RAM, SSD)        |
 |                                                                   |
 |  USB Port 1 (Karta 1) -----> FRONT Kamera (Old bamper / Oyna)     |
 |  USB Port 2 (Karta 1) -----> REAR Kamera (Orqa bamper / Bagaj)    |
 |  USB Port 3 (Karta 2) -----> LEFT Kamera (Chap ko'zgu osti)       |
 |  USB Port 4 (Karta 2) -----> RIGHT Kamera (O'ng ko'zgu osti)      |
 |  USB Port 5 (COM3)    -----> GPS Qabul qiluvchi (U-blox USB)      |
 |  OBD-II Port (COM4)   -----> ELM327 Diagnostika Adapteri          |
 |  HDMI / Type-C        -----> 10-12" Sensorli Monitor (1280x800)   |
 |  3.5mm Audio AUX      -----> Avtomobil Ichki Dinamigi             |
 +-------------------------------------------------------------------+
```

---

## 2. 4 ta Kamerani Joylashtirish va Burchaklari

| Kamera | Joylashuv O'rni | Tavsiya etilgan FOV | Qiyalik Burchagi | Asosiy Vazifasi |
|---|---|---|---|---|
| **FRONT** | Old oynaning markazi (salonda) yoki old radiator panjarasi | $110^\circ - 120^\circ$ | Gorizontdan $15^\circ$ pastga | Oldingi chiziqlar, svetofor, piyodalar, masofa va visual odometry |
| **REAR** | Orqa davlat raqami tepasi yoki yukxona qopqog'i | $130^\circ - 140^\circ$ | Gorizontdan $25^\circ$ pastga | Orqaga harakat, garajga kirish, orqa to'xtash chizig'i |
| **LEFT** | Chap yon ko'zgu (orqa ko'rish oynasi) osti | $90^\circ - 100^\circ$ | $45^\circ$ pastga (yerga) | Zmeyka mashqi, chap g'ildirak chiziqni bosishi, konuslar oralig'i |
| **RIGHT** | O'ng yon ko'zgu osti | $90^\circ - 100^\circ$ | $45^\circ$ pastga (yerga) | Parallel parkovka, o'ng bort masofasi, chetki chiziqlar |

> **MUHIM QOIDA**: Kameralar mahkam qotirilishi kerak (vibratsiyaga chidamli metall kronshteyn). Avtomobil silkinganda kamera burchagi o'zgarsa, kalibrovka siljishi (drift) xatosi yuzaga keladi.

---

## 3. USB O'tkazish Qobiliyati (Bandwidth) Muammosi va Yechimi

4 ta kamera bir vaqtda 1920x1080 rezolyutsiyada 30 FPS bilan ishlaganda, har bir kamera soniyasiga katta hajmdagi xom ma'lumot uzatadi.
- Agar barcha 4 kamera bitta umumiy USB 2.0 yoki bitta USB 3.0 kontrolleriga ulansa, Windows DirectShow drayveri `device bandwidth exceeded` xatosini beradi va kadrlar tushib qoladi.
- **Yechim**:
  1. Kompyuterga **PCIe to 4-Port Dedicated Controller** platasi o'rnatiladi (har bir port uchun alohida Renesas / NEC chipi).
  2. Yoki kameralar dasturda apparatli **MJPEG** siqilgan oqim rejimiga o'tkaziladi (`config/config.yaml`).

Kameralar ulanishini tekshirish uchun:
```powershell
python tools/camera_discovery.py
```

---

## 4. Quvvat Manbai va Zanjir Xavfsizligi

1. **Starter aylanishidagi kuchlanish tushishi (Crank Voltage Drop)**:
   - Dvigatel o't oldirilayotganda avtomobil akkumulyatorining kuchlanishi 12.6V dan 8.0-9.0V gacha tushib ketadi. Oddiy kompyuter quvvat bloklari bu paytda kompyuterni o'chirib qo'yadi.
   - **Yechim**: Avtomobillar uchun maxsus keng diapazonli (6V-30V) stabilizator (masalan, **M4-ATX** yoki **DCDC-USB 200W**) ishlatiladi.
2. **Kechiktirilgan o'chirish (Shutdown Delay)**:
   - Avtomobil dvigateli o'chirilganda, kompyuter darhol uzilib qolmasligi uchun stabilizator 60 soniya davomida quvvat berib turadi va dastur ma'lumotlar bazasini xavfsiz yopishga ulguradi.

---

## 5. Homografiya va Bird's-Eye View Kalibrovkasi

Kameralar o'rnatilgach, ularning tasvirini yer tekisligiga to'g'ri o'girish uchun kalibrovka o'tkaziladi:

1. Avtomobilni tekis asfalt maydonga qo'ying.
2. Avtomobil bamperidan oldinga 4 ta o'lchov belgisini qo'ying:
   - Chap old: $-1.5$ metr chap, $5.0$ metr oldinga
   - O'ng old: $+1.5$ metr o'ng, $5.0$ metr oldinga
   - O'ng yaqin: $+1.5$ metr o'ng, $1.5$ metr oldinga
   - Chap yaqin: $-1.5$ metr chap, $1.5$ metr oldinga
3. Kalibrovka dasturini ishga tushiring:
   ```powershell
   python tools/auto_calibrate_cameras.py --camera FRONT
   python tools/auto_calibrate_cameras.py --camera REAR
   python tools/auto_calibrate_cameras.py --camera LEFT
   python tools/auto_calibrate_cameras.py --camera RIGHT
   ```
4. Dastur avtomatik ravishda homografiya matritsasini hisoblab, `config/calibration/` papkasiga saqlaydi.

---

## 6. Sensorli Monitor va Kiosk Rejimi

- Monitor haydovchi o'rindig'idan bemalol qo'l yetadigan masofada (markaziy konsol yoki torpeda ustida) mustahkam o'rnatiladi.
- Quyosh nuri to'g'ridan-to'g'ri tushganda ham aniq ko'rinishi uchun mot (anti-glare) plyonka yoki quyoshdan himoyalovchi soyabon (visor) tavsiya etiladi.
- Dasturni Kiosk rejimida ishga tushirish:
  ```powershell
  D:\My-project\driving_eval_system\dist\DrivingEvalSystem\Avtomobil_Kiosk_Rejimi.bat
  ```
