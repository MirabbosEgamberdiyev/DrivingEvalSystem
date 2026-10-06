# JOYLASHTIRISH VA O'RNATISH QO'LLANMASI (DEPLOYMENT.md)

Ushbu hujjat yangi imtihon avtomobiliga tizimni 0 dan o'rnatish, offline wheelhouse paketi, systemd avto-yuklanishi va USB yangilash tartibini belgilaydi.

---

## 1. Minimal Apparat Talablari
- **Kompyuter**: Sanoat darajasidagi mini-kompyuter (Intel Core i7 12-avlod yoki NVIDIA Jetson Orin Nano/NX).
- **Xotira**: 16 GB DDR4/DDR5 RAM.
- **Saqlash**: 256 GB NVMe SSD (kamida 50 GB bo'sh joy doimiy talab qilinadi).
- **Kameralar**: 4 ta sanoat USB 3.0 / GMSL2 global shutter kamerasi (1280x720 @ 30 FPS).
- **Sensorlar**: USB GNSS/GPS, USB 6-DOF IMU, OBD-II (ELM327 / STN1110 CAN adapter).

---

## 2. 100% Offline O'rnatish (Wheelhouse)
Avtomobil kompyuterida internet umuman bo'lmaydi. Barcha paketlar laboratoriyada oldindan wheelhouse formatida yig'iladi:

```bash
# Laboratoriya kompyuterida:
pip download -r requirements.txt -d ./wheelhouse

# Avtomobil kompyuterida (offline):
python3 -m venv /opt/driving_eval_system/.venv
/opt/driving_eval_system/.venv/bin/pip install --no-index --find-links=./wheelhouse -r requirements.txt
```

---

## 3. Systemd Kiosk Servisini Sozlash
Avtomobil o't oldirilganda tizim avtomatik ravishda kiosk rejimida ochilishi uchun:

```bash
sudo cp systemd/autoeval.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable autoeval.service
sudo systemctl start autoeval.service
```

---

## 4. USB Orqali Xavfsiz Yangilash (Updater & Rollback)
1. Dasturning yangi versiyasi `update_package.zip` ko'rinishida arxivlanadi va uning SHA-256 xeshi `update_manifest.json` ga yoziladi.
2. Flash-disk avtomobilning USB portiga ulanadi.
3. Tizim SHA-256 xeshni tekshiradi, joriy tizimning to'liq nusxasini `backups/` papkasiga saqlaydi va yangilanishni o'rnatadi.
4. Agar o'rnatishdan keyin Pre-check muvaffaqiyatsiz bo'lsa yoki xato yuz bersa, tizim avtomatik ravishda oldingi versiyaga **ROLLBACK** qiladi.
