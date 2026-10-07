"""Unit tests for Multilingual Foundation (Phase 1).

Covers:
- Catalog loading & 100% key parity
- ICU pluralization (one, few, many, other) across Russian and Uzbek
- Strict fallback chain and MissingTranslationKeyError
- Formatting helpers (speed, number, datetime)
- Rules YAML 3-language passport verification
- Translation linter (check_translations.py)
- Database schema migration & new tables (license_state, consent_log, app_settings)
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from driving_eval.core.config_schema import RulesManifest
from driving_eval.db.repository import DatabaseRepository
from driving_eval.i18n.check_translations import run_translation_checks
from driving_eval.i18n.service import (
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
    I18nService,
    MissingTranslationKeyError,
)


@pytest.fixture
def i18n_service() -> I18nService:
    catalogs_dir = Path("src/driving_eval/i18n/catalogs")
    return I18nService(default_lang=DEFAULT_LANGUAGE, catalogs_dir=catalogs_dir, strict_mode=False)


@pytest.fixture
def strict_i18n_service() -> I18nService:
    catalogs_dir = Path("src/driving_eval/i18n/catalogs")
    return I18nService(default_lang=DEFAULT_LANGUAGE, catalogs_dir=catalogs_dir, strict_mode=True)


def test_catalogs_key_parity_and_non_empty(i18n_service: I18nService) -> None:
    """Verifies that all 3 language catalogs contain identical non-empty keys."""
    keys_latn = i18n_service.get_catalog_keys("uz-Latn")
    keys_cyrl = i18n_service.get_catalog_keys("uz-Cyrl")
    keys_ru = i18n_service.get_catalog_keys("ru")

    assert len(keys_latn) > 30, "uz-Latn catalog should contain substantial keys"
    assert keys_latn == keys_cyrl, f"Diff Latn-Cyrl: {keys_latn ^ keys_cyrl}"
    assert keys_latn == keys_ru, f"Diff Latn-Ru: {keys_latn ^ keys_ru}"


def test_translation_retrieval_and_formatting(i18n_service: I18nService) -> None:
    """Tests basic string retrieval and parameter substitution across languages."""
    # uz-Latn
    i18n_service.set_language("uz-Latn")
    assert i18n_service.t("btn_start_test") == "TESTNI BOSHLASH"
    assert i18n_service.tf("popup_queue_more", 3) == "Navbatda yana: 3 ta"

    # uz-Cyrl
    i18n_service.set_language("uz-Cyrl")
    assert i18n_service.t("btn_start_test") == "ТЕСТНИ БОШЛАШ"
    assert i18n_service.tf("popup_queue_more", 3) == "Навбатда яна: 3 та"

    # ru
    i18n_service.set_language("ru")
    assert i18n_service.t("btn_start_test") == "НАЧАТЬ ТЕСТ"
    assert i18n_service.tf("popup_queue_more", 3) == "В очереди еще: 3"


def test_icu_pluralization_rules(i18n_service: I18nService) -> None:
    """Tests ICU plural rules for Russian (one, few, many) and Uzbek (other)."""
    # Russian tests
    i18n_service.set_language("ru")
    assert i18n_service.t_plural("penalty_points_plural", 1) == "1 балл"
    assert i18n_service.t_plural("penalty_points_plural", 2) == "2 балла"
    assert i18n_service.t_plural("penalty_points_plural", 4) == "4 балла"
    assert i18n_service.t_plural("penalty_points_plural", 5) == "5 баллов"
    assert i18n_service.t_plural("penalty_points_plural", 11) == "11 баллов"
    assert i18n_service.t_plural("penalty_points_plural", 21) == "21 балл"
    assert i18n_service.t_plural("penalty_points_plural", 22) == "22 балла"

    assert i18n_service.t_plural("errors_count_plural", 1) == "1 ошибка"
    assert i18n_service.t_plural("errors_count_plural", 2) == "2 ошибки"
    assert i18n_service.t_plural("errors_count_plural", 5) == "5 ошибок"

    # Uzbek Latin tests
    i18n_service.set_language("uz-Latn")
    assert i18n_service.t_plural("penalty_points_plural", 1) == "1 ball"
    assert i18n_service.t_plural("penalty_points_plural", 2) == "2 ball"
    assert i18n_service.t_plural("penalty_points_plural", 10) == "10 ball"

    # Uzbek Cyrillic tests
    i18n_service.set_language("uz-Cyrl")
    assert i18n_service.t_plural("penalty_points_plural", 1) == "1 балл"
    assert i18n_service.t_plural("penalty_points_plural", 5) == "5 балл"


def test_fallback_chain_and_strict_mode(tmp_path: Path) -> None:
    """Tests fallback chain (ru/uz-Cyrl -> uz-Latn) and strict mode exceptions."""
    custom_catalogs = tmp_path / "catalogs"
    custom_catalogs.mkdir()

    # uz-Latn has base_key and extra_key
    (custom_catalogs / "uz-Latn.json").write_text(
        '{"base_key": {"text": "Asosiy"}, "extra_key": {"text": "Qo\'shimcha"}}',
        encoding="utf-8",
    )
    # ru has only base_key
    (custom_catalogs / "ru.json").write_text(
        '{"base_key": {"text": "Базовый"}}',
        encoding="utf-8",
    )
    # uz-Cyrl is empty
    (custom_catalogs / "uz-Cyrl.json").write_text("{}", encoding="utf-8")

    # Non-strict mode: falls back to uz-Latn
    service_lax = I18nService(
        default_lang="ru", catalogs_dir=custom_catalogs, strict_mode=False
    )
    assert service_lax.t("base_key") == "Базовый"
    assert service_lax.t("extra_key") == "Qo'shimcha"  # Fell back to uz-Latn
    assert service_lax.t("completely_missing_key") == "completely_missing_key"

    # Strict mode: raises MissingTranslationKeyError immediately
    service_strict = I18nService(
        default_lang="ru", catalogs_dir=custom_catalogs, strict_mode=True
    )
    assert service_strict.t("base_key") == "Базовый"
    with pytest.raises(MissingTranslationKeyError):
        service_strict.t("extra_key")

    with pytest.raises(MissingTranslationKeyError):
        service_strict.t("completely_missing_key")


def test_locale_formatting_helpers(i18n_service: I18nService) -> None:
    """Tests format_speed, format_number, and format_datetime."""
    i18n_service.set_language("uz-Latn")
    assert i18n_service.format_speed(25.4) == "25 km/h"

    i18n_service.set_language("uz-Cyrl")
    assert i18n_service.format_speed(25.4) == "25 км/соат"

    i18n_service.set_language("ru")
    assert i18n_service.format_speed(25.4) == "25 км/ч"

    assert i18n_service.format_number(12500) == "12 500"
    dt = datetime(2026, 10, 6, 14, 30, 0)
    assert i18n_service.format_datetime(dt) == "06.10.2026 14:30:00"


def test_language_switch_signal(i18n_service: I18nService) -> None:
    """Verifies that set_language changes state and emits languageChanged."""
    emitted = []
    i18n_service.languageChanged.connect(lambda lang: emitted.append(lang))

    assert i18n_service.set_language("ru") is True
    assert i18n_service.current_language == "ru"
    assert emitted == ["ru"]

    # Setting unsupported language returns False
    assert i18n_service.set_language("fr") is False
    assert i18n_service.current_language == "ru"
    assert emitted == ["ru"]


def test_rules_yaml_has_all_three_languages() -> None:
    """Verifies that config/rules.yaml has complete passports for all 3 languages."""
    rules_path = Path("config/rules.yaml")
    manifest = RulesManifest.load_from_yaml(rules_path)

    assert len(manifest.rules) >= 9, "Should load at least 9 rules"
    for rule in manifest.rules:
        for lang in SUPPORTED_LANGUAGES:
            assert lang in rule.translations, f"Rule {rule.code} missing {lang}"
            assert rule.get_title(lang), f"Rule {rule.code} missing title in {lang}"
            assert rule.get_screen_text(lang), f"Rule {rule.code} missing screen_text in {lang}"
            assert rule.get_voice_text(lang), f"Rule {rule.code} missing voice_text in {lang}"
            v_file = rule.get_voice_file(lang)
            assert v_file.endswith(".wav"), f"Rule {rule.code} voice_file must be .wav in {lang}"


def test_translation_linter_report_clean() -> None:
    """Executes the translation linter and confirms 100% clean report."""
    report = run_translation_checks(
        catalogs_dir=Path("src/driving_eval/i18n/catalogs"),
        rules_path=Path("config/rules.yaml"),
    )
    assert report.is_valid is True
    assert len(report.missing_keys) == 0
    assert len(report.placeholder_mismatches) == 0
    assert len(report.rules_errors) == 0
    assert len(report.script_leakages) == 0


def test_script_leakage_detection(tmp_path: Path) -> None:
    """Verifies that script leakage detection catches Cyrillic in Latn, Uzbek in Ru, and Latin in Cyrl."""
    cat_dir = tmp_path / "catalogs"
    cat_dir.mkdir()
    # uz-Latn with Cyrillic character
    (cat_dir / "uz-Latn.json").write_text('{"k1": {"text": "Test \u0430 text"}}', encoding="utf-8")
    # uz-Cyrl with non-whitelisted English word
    (cat_dir / "uz-Cyrl.json").write_text('{"k1": {"text": "Тест disconnect text"}}', encoding="utf-8")
    # ru with Uzbek apostrophe
    (cat_dir / "ru.json").write_text('{"k1": {"text": "Тест o\'tgan text"}}', encoding="utf-8")

    dummy_rules = tmp_path / "rules.yaml"
    dummy_rules.write_text("rules: []\n", encoding="utf-8")

    report = run_translation_checks(catalogs_dir=cat_dir, rules_path=dummy_rules, project_root=tmp_path)
    assert report.is_valid is False
    assert len(report.script_leakages) >= 3
    assert any("[uz-Latn Cyrillic leak]" in x for x in report.script_leakages)
    assert any("[uz-Cyrl Latin leak]" in x for x in report.script_leakages)
    assert any("[ru Uzbek-Latin leak]" in x for x in report.script_leakages)


def test_db_migration_and_repository_extensions(tmp_path: Path) -> None:
    """Tests migration 2, mode/language in test_sessions, and new repository tables."""
    db_file = tmp_path / "test_eval.db"
    repo = DatabaseRepository(db_path=db_file)

    # 1. Create a session with explicit mode and language
    student_id = repo.register_or_get_student("AB1234567", "Ali", "Valiyev")
    vehicle_id = repo.register_vehicle("CAR-01", "VIN123", "01A777AA", "Cobalt", 2024)

    session_id = "SESS-PHASE1-TEST"
    repo.create_session(
        session_id=session_id,
        student_id=student_id,
        vehicle_id=vehicle_id,
        start_score=100,
        rules_version="2026.1",
        app_version="1.0.0",
        mode="TRAINING",
        language="uz-Cyrl",
    )

    sess = repo.get_session(session_id)
    assert sess is not None
    assert sess["mode"] == "TRAINING"
    assert sess["language"] == "uz-Cyrl"

    # 2. Test Consent Log
    assert repo.has_valid_consent(student_id, "v1.0") is False
    repo.record_consent(student_id, "v1.0", agreed=True, ip_or_device="TOUCHSCREEN_01")
    assert repo.has_valid_consent(student_id, "v1.0") is True

    # 3. Test License State
    repo.save_license_state(
        license_key="TEST-LIC-KEY-123",
        machine_id="MCH-NODE-456",
        issued_at="2026-01-01T00:00:00Z",
        expires_at="2027-01-01T00:00:00Z",
        features=["TRAINING", "ASSESSMENT"],
        signature="FAKESIG123",
        anti_clock_max_timestamp="2026-10-06T12:00:00Z",
    )
    lic = repo.get_license_state()
    assert lic is not None
    assert lic["license_key"] == "TEST-LIC-KEY-123"
    assert lic["machine_id"] == "MCH-NODE-456"

    # 4. Test App Settings
    repo.set_app_setting("ui_theme", "dark_contrast")
    assert repo.get_app_setting("ui_theme") == "dark_contrast"
    assert repo.get_app_setting("non_existent", "default_val") == "default_val"
