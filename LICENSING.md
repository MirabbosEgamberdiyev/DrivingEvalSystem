# 🔐 Kriptografik Litsenziyalash va Kalitlar Xavfsizligi Yo'riqnomasi (LICENSING.md)

Ushbu hujjat **DrivingEvalSystem** offline avtomatlashtirilgan haydash imtihon tizimining kriptografik litsenziyalash arxitekturasi, kompromat kalitni almashtirish va yangi litsenziyalar berish tartibini belgilaydi.

---

## 1. Litsenziyalash Arxitekturasi

Tizim **100% internetga ulanmasdan (to'liq offline)** ishlaydi. Noqonuniy nusxalash va soxtalashtirishdan himoyalanish quyidagi 4 bosqichli kriptografik himoya orqali ta'minlangan:

1. **Ed25519 Asimmetrik Raqamli Imzo:**
   - Har bir litsenziya tokeni faqat vakolatli imtihon markazi (Vendor) ning maxfiy kaliti orqali imzolanadi.
   - Dastur ichiga faqat 32-baytli Ochiq Kalit (`MASTER_PUBLIC_KEY_HEX`) joylashtirilgan.
   - Raqamli imzo o'zgartirilsa yoki bitta bayt buzilsa, dastur darhol `INVALID_SIGNATURE` xatosini beradi va ishga tushishni bloklaydi.

2. **Apparat Kvorumi (3/4 Hardware Tolerance):**
   - Litsenziya avtomobil bort kompyuterining 4 ta apparat identifikatoriga (Ona plata, Protsessor, Qattiq disk, Tarmoq kartasi MAC) bog'lanadi.
   - Kompyuterda disk yoki tarmoq kartasi almashtirilsa, 3/4 kvorum bilan litsenziya faol qoladi.
   - Kompyuter butunlay boshqa mashinaga ko'chirilsa, `MACHINE_MISMATCH` bilan bloklanadi.

3. **Avtomobil Bog'lanishi (Vehicle Car ID):**
   - Litsenziya tokeni avtomobilning unikal identifikatoriga (`car_id`, masalan `CAR-UZ-01`) bog'lanadi.

4. **Tizim Soatini Orqaga Surishdan Himoya (Anti-Clock-Tampering):**
   - SQLite ma'lumotlar bazasida har bir operatsiya vaqti SHA-256 xesh zanjiri (`clock_timeline`) orqali saqlanadi.
   - Windows soati orqaga surilsa, tizim manipulyatsiyani aniqlab, `CLOCK_ROLLBACK` statusi bilan litsenziyani muzlatadi.

---

## 2. Xavfsizlik Hodisasi va Kompromat Kalit Bekor Qilinishi (Revocation)

> [!CAUTION]
> **ESKI DEV KALITI KOMPROMAT QILINGAN:**
> Dastlabki ishlab chiqish jarayonida `bdd0b1a5fdd912b838c5cd6a6d08bc58caa1174c6f6a30df78cd157a1eb53869` maxfiy kaliti test vositasida qoldirilgan. Ushbu kalit ommaviy commit tarixida ko'ringanligi sababli **BEKOR QILINGAN (REVOKED)**.

### Oqibatlar:
1. Eski dev kaliti bilan imzolangan barcha test litsenziyalari **haqiqiy emas** deb hisoblanadi.
2. Dastur kodidagi ochiq kalit yangi xavfsiz Vendor Ochiq Kalitiga almashtirildi:
   - **Yangi Vendor Ochiq Kaliti (Embedded Public Key):**
     ```text
     172334160c7edc8c7c3d800147137c6290690357691ee80cf5c76416498ffb30
     ```
3. Endi eski kalit bilan imzolangan tokenlar yangi dasturda `INVALID_SIGNATURE` xatosi bilan rad etiladi.

---

## 3. Yangi Vendor Kalitlar Juftligini Yaratish Tartibi

Yangi maxfiy kalit **hech qachon** Git repozitoriyasiga qo'shilmasligi va faqat parollangan xavfsiz faylda saqlanishi kerak.

### Yangi kalit juftligini yaratish:
Administrator quyidagi buyruqni repodan tashqaridagi xavfsiz muhitda yoki USB tashuvchida ishga tushiradi:

```bash
python tools/admin_license_gen.py --generate-keypair --save-encrypted "D:/SecureKeys/vendor_private.pem" --passphrase "MurakkabMaxfiyParol2026!"
```

**Natija:**
- Ekranda yangi **Public Key Hex** ko'rsatiladi (ushbu qiymat `license_manager.py` dagi `MASTER_PUBLIC_KEY_HEX` ga yoziladi).
- Maxfiy kalit AES-256 (PKCS#8) bilan shifrlangan holda `vendor_private.pem` fayliga saqlanadi.

---

## 4. Real Avtomobilga Litsenziya Berish va Qayta Berish (Re-Issuance)

Eski litsenziyalarni yangisiga almashtirish yoki yangi avtomobilni faollashtirish:

### 1-qadam: Avtomobil apparat barmoq izini olish
Avtomobil kompyuterida dasturni ishga tushirib yoki CLI orqali barmoq izini eksport qiling:
```bash
python -c "from driving_eval.licensing.machine_id import get_current_machine_fingerprint; import json; print(json.dumps(get_current_machine_fingerprint().to_dict()))" > machine_hw.json
```

### 2-qadam: Administrator tomonidan litsenziya tokenini generatsiya qilish
Administrator o'z kompyuterida (shifrlangan kalit va parol yordamida):
```bash
python tools/admin_license_gen.py \
    --car-id "CAR-UZ-01" \
    --expires "2028-12-31" \
    --tier "FULL" \
    --machine-json machine_hw.json \
    --private-key "D:/SecureKeys/vendor_private.pem" \
    --passphrase "MurakkabMaxfiyParol2026!" \
    --output license.key
```

### 3-qadam: Avtomobilga o'rnatish
Hosil bo'lgan `license.key` faylini avtomobildagi dasturning `config/license.key` joylashuviga ko'chiring yoki dasturning **Setup Wizard / Litsenziya** ekranida token matnini kiriting.

---

## 5. Litsenziya Tokeni Formati

Token formati:
```text
DRV-LIC-<Base64URL(Payload_Uzunligi + JSON_Payload + 64_Baytli_Ed25519_Imzo)>
```

Token tarkibidagi ma'lumotlar:
```json
{
  "car_id": "CAR-UZ-01",
  "machine_fingerprint": {
    "board": "hash...",
    "cpu": "hash...",
    "disk": "hash...",
    "mac": "hash..."
  },
  "issued_at": "2026-10-07T10:00:00Z",
  "expires_at": "2028-12-31",
  "tier": "FULL",
  "features": ["4_cameras", "all_exercises", "pdf_reports"]
}
```
