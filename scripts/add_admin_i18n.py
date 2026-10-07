import json
from pathlib import Path

new_keys = {
    "admin.hardware_title": {
        "uz-Latn": "Apparat vositalari va datchiklar telemetriyasi",
        "uz-Cyrl": "Аппарат воситалари ва датчиклар телеметрияси",
        "ru": "Телеметрия аппаратных средств и датчиков"
    },
    "admin.camera_grid_title": {
        "uz-Latn": "4-kamera jonli ko'rinishi va kadrlar tahlili",
        "uz-Cyrl": "4-камера жонли кўриниши ва кадрлар таҳлили",
        "ru": "Прямой эфир с 4 камер и анализ кадров"
    },
    "admin.bev_title": {
        "uz-Latn": "BEV (Qush parvozi) proyeksiyasi va kalibratsiya sifati",
        "uz-Cyrl": "BEV (Қуш парвози) проекцияси ва калибровка сифати",
        "ru": "BEV (Вид сверху) проекция и качество калибровки"
    },
    "admin.polygon_title": {
        "uz-Latn": "Poligon konfiguratsiyasi va 8 ta mashq zonalari",
        "uz-Cyrl": "Полигон конфигурацияси ва 8 та машқ зоналари",
        "ru": "Конфигурация автодрома и зоны 8 упражнений"
    },
    "admin.rules_title": {
        "uz-Latn": "Imtihon qoidalari pasporti (rules.yaml)",
        "uz-Cyrl": "Имтиҳон қоидалари паспорти (rules.yaml)",
        "ru": "Паспорт правил экзамена (rules.yaml)"
    },
    "admin.license_title": {
        "uz-Latn": "Litsenziya, apparat imzosi va xavfsizlik",
        "uz-Cyrl": "Лицензия, аппарат имзоси ва хавфсизлик",
        "ru": "Лицензия, аппаратная подпись и безопасность"
    },
    "admin.logs_title": {
        "uz-Latn": "Tizim audit jurnali va hodisalar tarixi",
        "uz-Cyrl": "Тизим аудит журнали ва ҳодисалар тарихи",
        "ru": "Системный журнал аудита и история событий"
    },
    "admin.wizard_title": {
        "uz-Latn": "Uskunalarni boshlang'ich sozlash ustasi",
        "uz-Cyrl": "Ускуналарни бошланғич созлаш устаси",
        "ru": "Мастер начальной настройки оборудования"
    },
    "admin.btn_refresh_diag": {
        "uz-Latn": "Diagnostikani yangilash",
        "uz-Cyrl": "Диагностикани янгилаш",
        "ru": "Обновить диагностику"
    },
    "admin.btn_run_wizard": {
        "uz-Latn": "Sozlash ustasini ishga tushirish",
        "uz-Cyrl": "Созлаш устасини ишга тушириш",
        "ru": "Запустить мастер настройки"
    },
    "admin.btn_auto_calibrate": {
        "uz-Latn": "Avtomatik qayta kalibrovka",
        "uz-Cyrl": "Автоматик қайта калибровка",
        "ru": "Автоматическая перекалибровка"
    },
    "admin.filter_all": {
        "uz-Latn": "Barchasi",
        "uz-Cyrl": "Барчаси",
        "ru": "Все"
    },
    "admin.filter_errors": {
        "uz-Latn": "Xatolar",
        "uz-Cyrl": "Хатолар",
        "ru": "Ошибки"
    },
    "admin.filter_audit": {
        "uz-Latn": "Audit",
        "uz-Cyrl": "Аудит",
        "ru": "Аудит"
    },
    "admin.calib_ok": {
        "uz-Latn": "Kalibrovka normada",
        "uz-Cyrl": "Калибровка нормада",
        "ru": "Калибровка в норме"
    },
    "admin.calib_drift": {
        "uz-Latn": "Siljish (Drift)",
        "uz-Cyrl": "Силжиш (Drift)",
        "ru": "Смещение (Drift)"
    },
    "admin.active": {
        "uz-Latn": "Faol",
        "uz-Cyrl": "Фаол",
        "ru": "Активно"
    },
    "admin.maintenance": {
        "uz-Latn": "Ta'mirda",
        "uz-Cyrl": "Таъмирда",
        "ru": "На ремонте"
    },
    "wizard.title": {
        "uz-Latn": "BOSHLANG'ICH SOZLASH USTASI",
        "uz-Cyrl": "БОШЛАНҒИЧ СОЗЛАШ УСТАСИ",
        "ru": "МАСТЕР НАЧАЛЬНОЙ НАСТРОЙКИ"
    },
    "wizard.step1": {
        "uz-Latn": "1. Til va EULA",
        "uz-Cyrl": "1. Тил ва EULA",
        "ru": "1. Язык и EULA"
    },
    "wizard.step2": {
        "uz-Latn": "2. Apparat va USB",
        "uz-Cyrl": "2. Аппарат ва USB",
        "ru": "2. Оборудование и USB"
    },
    "wizard.step3": {
        "uz-Latn": "3. 4 Kamera oqimi",
        "uz-Cyrl": "3. 4 Камера оқими",
        "ru": "3. Потоки 4 камер"
    },
    "wizard.step4": {
        "uz-Latn": "4. Kalibrovka va BEV",
        "uz-Cyrl": "4. Калибровка ва BEV",
        "ru": "4. Калибровка и BEV"
    },
    "wizard.step5": {
        "uz-Latn": "5. Poligon zonalari",
        "uz-Cyrl": "5. Полигон зоналари",
        "ru": "5. Зоны полигона"
    },
    "wizard.step6": {
        "uz-Latn": "6. Audio dinamik testi",
        "uz-Cyrl": "6. Аудио динамик тести",
        "ru": "6. Тест аудиодинамиков"
    },
    "wizard.step7": {
        "uz-Latn": "7. Litsenziya va Yakunlash",
        "uz-Cyrl": "7. Лицензия ва Якунлаш",
        "ru": "7. Лицензия и Завершение"
    },
    "wizard.eula_agree": {
        "uz-Latn": "Foydalanuvchi shartnomasiga to'liq roziman",
        "uz-Cyrl": "Фойдаланувчи шартномасига тўлиқ розиман",
        "ru": "Полностью согласен с пользовательским соглашением"
    },
    "wizard.btn_rescan": {
        "uz-Latn": "Qayta skanerlash",
        "uz-Cyrl": "Қайта сканерлаш",
        "ru": "Повторное сканирование"
    },
    "wizard.btn_test_audio": {
        "uz-Latn": "Ovozni sinash",
        "uz-Cyrl": "Овозни синаш",
        "ru": "Проверить звук"
    },
    "wizard.btn_complete": {
        "uz-Latn": "Sozlashni yakunlash",
        "uz-Cyrl": "Созлашни якунлаш",
        "ru": "Завершить настройку"
    }
}

catalogs = {
    "uz-Latn": Path("src/driving_eval/i18n/catalogs/uz-Latn.json"),
    "uz-Cyrl": Path("src/driving_eval/i18n/catalogs/uz-Cyrl.json"),
    "ru": Path("src/driving_eval/i18n/catalogs/ru.json"),
}

for lang, p in catalogs.items():
    data = json.loads(p.read_text(encoding="utf-8"))
    reviewer = "metodist_ru" if lang == "ru" else "metodist_uz"
    for k, v in new_keys.items():
        data[k] = {
            "text": v[lang],
            "reviewed": True,
            "reviewer": reviewer
        }
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Updated {lang}: {len(data)} total keys")
