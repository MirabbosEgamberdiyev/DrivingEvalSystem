# TIZIM ARXITEKTURASI (ARCHITECTURE.md)

Ushbu hujjat "Standalone 4-Camera Offline AI Driving Training & Evaluation System" tizimining to'liq arxitekturasini, jarayonlararo aloqasini, ma'lumotlar oqimini va xavfsizlik modelini bayon qiladi.

---

## 1. Umumiy Konseptsiya va Tamoyillar
1. **100% Offline va Standalone**: Tizim hech qanday internetga, bulutli serverga yoki telemetriyaga bog'liq emas. 1 ta avtomobil = 1 ta sanoat kompyuteri = 1 ta SQLite baza.
2. **Qat'iy Holat Mashinasi (Strict State Machine)**: Barcha bosqichlar qat'iy tekshiriladi, ruxsatsiz o'tishlar istisno (exception) beradi.
3. **Multi-process Isolation**: AI inferens va kamera xizmati alohida, PySide6 Kiosk foydalanuvchi interfeysi alohida ishlaydi. Ular Watchdog orqali nazorat qilinadi.

---

## 2. Tizim Arxitekturasi Diagrammasi

```mermaid
flowchart TD
    subgraph SENSORS ["Uskunalar va Sensorlar Oqimi"]
        CAM1["FRONT Kamera"]
        CAM2["REAR Kamera"]
        CAM3["LEFT Kamera"]
        CAM4["RIGHT Kamera"]
        GPS["GPS / GNSS Qabul qiluvchi"]
        IMU["IMU Akselerometr / Giroskop"]
        OBD["OBD-II Telemetriya (CAN)"]
    end

    subgraph INGESTION ["Uskunalar Qatlami (Hardware Layer)"]
        CS["MultiCameraService<br/>(Monotonic Sync & Health)"]
        SF["SensorFusionService<br/>(Tezlik, Qiyalik, Kamar)"]
        CALIB["CalibrationService<br/>(Undistort, Homography, Drift)"]
    end

    subgraph AI_LAYER ["Sun'iy Intellekt va Kuzatuv (AI Layer)"]
        DET["BaseDetector<br/>(ONNX Runtime / TensorRT / Mock)"]
        TRK["SimpleByteTracker<br/>(Barqaror Track ID lar)"]
        EXD["ExerciseDetector<br/>(Geofence & Ketma-ketlik)"]
    end

    subgraph RULE_CORE ["Qoidalar va Hodisalar (Core Rule Engine)"]
        RE["RuleEngine<br/>(Plugin Arxitektura)"]
        EM["EventManager<br/>(Debounce, Cooldown, Dedup)"]
        SC["ScoringEngine<br/>(Start 100, PASS/FAIL, SUSPECT)"]
    end

    subgraph OUTPUTS ["Chiqish va Xavfsizlik Qatlami"]
        UI["PySide6 Kiosk UI<br/>(HUD, Popup, Natija)"]
        AUD["AudioService<br/>(WAV Navbati + Piper TTS)"]
        EVID["EvidenceRecorder<br/>(Ring Buffer, JPG, MP4, SHA-256)"]
        DB[(SQLite WAL Baza<br/>Hash Chaining & Migratsiyalar)]
        REP["Hisobot Generator<br/>(PDF & CSV)"]
    end

    CAM1 & CAM2 & CAM3 & CAM4 --> CS
    GPS & IMU & OBD --> SF
    CS & CALIB --> DET
    DET --> TRK
    TRK & SF & EXD --> RE
    RE --> EM
    EM -->|CONFIRMED / SUSPECT| SC
    EM -->|Hodisa| UI
    EM -->|Ovoz Navbati| AUD
    EM -->|Dalil Yozish| EVID
    SC & EVID --> DB
    DB --> REP
```

---

## 3. Imtihonning Qat'iy Holat Mashinasi (Exam State Machine)

Tizimda `boolean` bayroqlar (flag) orqali holat saqlash qat'iyan taqiqlangan. Barcha o'tishlar `ALLOWED_TRANSITIONS` matritsasi bo'yicha ruxsat etiladi:

```mermaid
stateDiagram-v2
    [*] --> IDLE
    IDLE --> BOOT: Tizim yoqilishi
    BOOT --> READY: Baza va sozlamalar yuklandi
    READY --> PRECHECK: Pre-check so'rovi
    PRECHECK --> CAMERA_CHECK: 4 kamera stream & sync
    CAMERA_CHECK --> SYSTEM_CHECK: AI, DB, Storage, Sensorlar
    SYSTEM_CHECK --> TEST_READY: Barcha 15 tekshiruv YASHIL
    TEST_READY --> TEST_ACTIVE: Nomzod [TESTNI BOSHLASH] ni bosdi

    TEST_ACTIVE --> FINISH_DETECTED: Mashina finish zonasiga kirdi
    FINISH_DETECTED --> VEHICLE_STOPPED: Tezlik 0 km/h (Mashina to'xtadi)
    VEHICLE_STOPPED --> FINALIZING: Dalillar yopilmoqda
    FINALIZING --> RESULT_READY: Natija hisoblandi
    RESULT_READY --> COMPLETED: Bayonnoma tayyor
    COMPLETED --> READY: Keyingi talaba uchun tayyor

    TEST_ACTIVE --> CRITICAL_VIOLATION: Kritik qoidabuzarlik aniqlandi!
    CRITICAL_VIOLATION --> TERMINATED: Test darhol to'xtatildi
    TERMINATED --> RESULT_READY: FAIL natijasi

    TEST_ACTIVE --> INTERRUPTED: Quvvat uzilishi
    INTERRUPTED --> READY: Boot paytida xavfsiz tiklash
```

---

## 4. Qoidabuzarlik Konveyeri (Violation Pipeline)

Har bir kadr uchun tekshiruv konveyeri quyidagi zanjir bo'yicha amalga oshadi:

```mermaid
sequenceDiagram
    participant Cam as Kameralar (30 FPS)
    participant Det as Detektor (ONNX / Mock)
    participant Trk as ByteTracker
    participant RE as Rule Engine & Plugins
    participant EM as Event Manager
    participant DB as SQLite WAL
    participant Evid as Evidence Recorder
    participant Aud as Audio Queue
    participant UI as Kiosk UI Overlay

    Cam->>Det: Sinxron kadrlar paketi
    Det->>Trk: BoundingBox lar ro'yxati
    Trk->>RE: Barqaror Track ID berilgan obyektlar
    RE->>RE: Metrik masofa va qoida shartlarini tekshirish
    RE->>EM: Qoidabuzarlik nomzodi (CANDIDATE)
    
    alt Ketma-ket N kadr tasdiqlandi (Debounce) va Ishonch >= Min
        EM->>EM: CONFIRMED holatiga o'tish + Cooldown boshlash
        par Parallel Ijro
            EM->>DB: Tranzaksiyani yozish + SHA-256 zanjirini yangilash
            EM->>Evid: before.jpg, event.jpg, after.jpg, event.mp4 saqlash
            EM->>Aud: Ovoz navbatiga qo'shish (.wav / TTS)
            EM->>UI: 3.5 soniyalik non-blocking popup ko'rsatish
        end
    else Ishonch yetarli emas (Confidence < Min)
        EM->>EM: SUSPECT deb belgilash (Jarima = 0)
        EM->>DB: Inspektor ko'rishi uchun SUSPECT yozish
    end
```

---

## 5. Kriptografik Xesh Zanjiri (Hash Chaining)
Ma'lumotlar bazasidagi har bir sessiya `session_hash` zanjiriga ega:
$$H_0 = \text{SHA256}(\text{SESSION\_START} + \text{ID} + \text{Time})$$
$$H_k = \text{SHA256}(H_{k-1} + \text{VIOLATION} + \text{RuleCode} + \text{Confidence} + \text{Time})$$
$$H_{\text{final}} = \text{SHA256}(H_{\text{last}} + \text{FINAL\_RESULT} + \text{Score} + \text{PASS/FAIL})$$

Agar kimdir SQLite bazasini tashqaridan ochib biror jarimani o'chirsa yoki ballni o'zgartirsa, qayta hisoblangan xesh ildizi `$H_{\text{final}}$` ga mos kelmaydi va tizim zudlik bilan tahrirlanganligini fosh qiladi.
