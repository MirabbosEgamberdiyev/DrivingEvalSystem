# KAMERALARNI KALIBROVKA QILISH QO'LLANMASI (CALIBRATION_GUIDE.md)

Ushbu qo'llanma 4 ta kamerani o'rnatish, optik buzilishlarni to'g'rilash (undistortion), pikseldan metrga o'tkazish (IPM) va referens siljishni tekshirish tartibini belgilaydi.

---

## 1. Kameralarni O'rnatish Standartlari
- **FRONT**: Old oyna orqasida yoki old radiator panjarasida, markazda, yer sathidan ~1.3m balandlikda.
- **REAR**: Orqa davlat raqami ustida, yer sathidan ~0.9m balandlikda.
- **LEFT**: Chap yon ko'zgu ostida, yerga 45 daraja burchak ostida.
- **RIGHT**: O'ng yon ko'zgu ostida, yerga 45 daraja burchak ostida.

---

## 2. Ichki Kalibrovka (Intrinsics & Undistortion)
1. 8x6 o'lchamli shaxmat taxtasi (Chessboard, 30mm kataklar) kameraning turli burchaklarida suratga olinadi (kamida 25 ta kadr).
2. `cv2.calibrateCamera` orqali kamera matritsasi ($K$) va distorsiya koeffitsientlari ($D = [k_1, k_2, p_1, p_2, k_3]$) aniqlanadi.
3. Natijalar `config/calibration/<kamera_nomi>_camera.json` fayliga yoziladi.

---

## 3. Homografiya va Qush Parvozi (Bird's-Eye View) Metrikasi
1. Avtomobil atrofidagi tekis asfaltga ma'lum masofada 4 ta metrik belgi (marker) qo'yiladi (masalan, $2.0 \times 2.0$ metr to'g'ri to'rtburchak).
2. Kadr piksellari $(u, v)$ va yer sathidagi haqiqiy metrlar $(X, Y)$ o'rtasidagi homografiya matritsasi ($H$) hisoblanadi:
   $$\begin{bmatrix} X \\ Y \\ 1 \end{bmatrix} \sim H \begin{bmatrix} u \\ v \\ 1 \end{bmatrix}$$
3. Ushbu matritsa orqali detektor aniqlagan konusning pastki markazi to'g'ridan-to'g'ri avtomobil bamperigacha bo'lgan metr masofasiga aylantiriladi.

---

## 4. Kalibrovka Siljishi (Drift Verification)
Har bir avtomobil tebranishlar va yo'l notekisliklari tufayli kameralarning siljishiga duch kelishi mumkin.
- Har bir kamerada avtomobil korpusining qo'zg'almas nuqtalari (masalan, kapot burchaklari, ko'zgu asosi) referens fidutsial sifatida saqlanadi (`reference_fiducials`).
- Tizim har bir Pre-check bosqichida ushbu nuqtalarni tekshiradi.
- Agar siljish chegaradan (`max_drift_threshold_px = 15.0px`) oshsa, Pre-check darhol test boshlanishini **BLOKLAYDI**.
