# MA'LUMOTLAR YIG'ISH VA CVAT ANNOTATSIYA QO'LLANMASI (DATASET SPECIFICATION)

Ushbu qo'llanma avtodrom imtihon tizimi uchun sun'iy intellekt (YOLO) modellarini o'qitishda ma'lumotlar to'plash va belgilash (annotation) standartlarini belgilaydi.

---

## 1. Kameralar Konfiguratsiyasi va Yozib Olish Talablari
- **Kameralar soni**: 4 ta (FRONT, REAR, LEFT, RIGHT).
- **Ruxsat (Resolution)**: 1280x720 (720p) yoki 1920x1080 (1080p).
- **Kadrlar chastotasi (FPS)**: 30 FPS.
- **Ob-havo va yorug'lik sharoitlari**:
  - Qiyom quyosh (to'g'ridan-to'g'ri nurlar va qattiq soyalar);
  - Bulutli kun;
  - Tong / kechki g'ira-shira;
  - Sun'iy projektorlar yorug'ligi (kechki imtihonlar uchun);
  - Ho'l asfalt va yomg'ir tomchilari.

---

## 2. Obyekt Sinflari (Classes) Ro'yxati

| Class ID | Nomi | Tavsifi va Qoidalari |
|---|---|---|
| `0` | `cone` | Qizil/oq yoki to'q sariq yo'l konusi. Butun korpusi kiritiladi. |
| `1` | `stop_line` | Oq rangli ko'ndalang to'xtash chizig'i. |
| `2` | `solid_line` | Yo'l cheti yoki mashq hududini belgilovchi sidirg'a (uzluksiz) chiziq. |
| `3` | `dashed_line` | Bo'laklarni ajratuvchi uzuq-uzuq chiziq. |
| `4` | `vehicle` | Avtodromdagi boshqa o'quv avtomobillari yoki to'siq transportlari. |
| `5` | `pedestrian` | Avtodrom hududidagi instruktor, talaba yoki nazoratchi piyodalar. |
| `6` | `barrier` | Metall to'siq, estakada panjarasi, beton to'siqlar. |
| `7` | `curb` | Yo'l chetidagi beton bort (bordyur). |

---

## 3. CVAT da Annotatsiya Qoidalari (Annotation Guidelines)
1. **Bounding Box chegaralari**:
   - Quti obyekt konturiga juda zich yopishishi kerak (bo'sh piksel ortiqcha bo'lmasin).
   - Qisman to'silgan obyektlar (occlusion): Agar obyektning 30% dan ko'prog'i ko'rinib tursa, ko'rinadigan va taxmin qilinadigan butun qismi qutiga olinadi.
   - Konusning poydevori (ground contact point) aniq belgilanishi shart, chunki masofa uning pastki markazidan o'lchanadi.
2. **Kamera ko'zgulari va borti**:
   - Avtomobilning o'z kapoti yoki ko'zgusi obyekt deb belgilanmaydi (ular kalibrovka uchun referens belgi hisoblanadi).
3. **Eksport formati**:
   - CVAT dan **YOLO 1.1 (normalized xywh)** formatida eksport qilinadi.
   - Ma'lumotlar `train` (70%), `val` (20%), `test` (10%) qismlarga tasodifiy ajratiladi.
