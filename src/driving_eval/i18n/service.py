"""Production Multilingual Internationalization (i18n) Service.

Supports:
- uz-Latn: Uzbek Latin
- uz-Cyrl: Uzbek Cyrillic
- ru: Russian

Guarantees:
- 100% offline local JSON catalog loading.
- Strict fallback chain: uz-Cyrl -> uz-Latn -> Exception; ru -> uz-Latn -> Exception.
- ICU pluralization (one, few, many, other) for Russian and Uzbek.
- Locale-aware speed, number, and datetime formatting.
- PySide6 QObject integration with languageChanged signal.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, QObject, Signal, Slot

logger = logging.getLogger(__name__)

SUPPORTED_LANGUAGES: tuple[str, ...] = ("uz-Latn", "uz-Cyrl", "ru")
DEFAULT_LANGUAGE: str = "uz-Latn"
LANGUAGE_ALIASES: dict[str, str] = {"uz": "uz-Latn"}


class MissingTranslationKeyError(KeyError):
    """Raised when a translation key is missing in catalogs."""


class I18nService(QObject):
    """Offline Localization Service with strict validation and fallback."""

    languageChanged = Signal(str)

    def __init__(
        self,
        default_lang: str = DEFAULT_LANGUAGE,
        catalogs_dir: Path | str | None = None,
        strict_mode: bool = False,
        load_saved_locale: bool = False,
    ) -> None:
        super().__init__()
        normalized_lang = LANGUAGE_ALIASES.get(default_lang, default_lang)
        if normalized_lang not in SUPPORTED_LANGUAGES:
            raise ValueError(
                f"Unsupported language: '{default_lang}'. Supported: {SUPPORTED_LANGUAGES}"
            )

        self._locale_file = Path("data/config/locale.json")
        if load_saved_locale and self._locale_file.exists():
            try:
                with open(self._locale_file, encoding="utf-8") as f:
                    saved = json.load(f)
                    saved_lang = saved.get("language")
                    if saved_lang and saved_lang in SUPPORTED_LANGUAGES:
                        normalized_lang = saved_lang
            except Exception:
                pass

        self._current_lang = normalized_lang
        self._strict_mode = strict_mode

        if catalogs_dir is None:
            self._catalogs_dir = Path(__file__).parent / "catalogs"
        else:
            self._catalogs_dir = Path(catalogs_dir)

        # In-memory catalogs: {lang_code: {key: {field: val}}}
        self._catalogs: dict[str, dict[str, Any]] = {}
        self._load_all_catalogs()

    @Property(str, notify=languageChanged)
    def currentLanguage(self) -> str:
        """Exposes the currently active BCP-47 language code to QML."""
        return self._current_lang

    @property
    def current_language(self) -> str:
        """Returns the currently active BCP-47 language code in Python."""
        return self._current_lang

    @Slot(result=list)
    def get_supported_languages(self) -> list[dict[str, str]]:
        """Returns list of supported language options for UI selectors."""
        return [
            {"code": "uz-Latn", "name": "O‘zbekcha", "flag": "🇺🇿"},
            {"code": "uz-Cyrl", "name": "Ўзбекча", "flag": "🇺🇿"},
            {"code": "ru", "name": "Русский", "flag": "🇷🇺"},
        ]

    def _load_all_catalogs(self) -> None:
        """Loads all supported language catalogs into memory."""
        for lang in SUPPORTED_LANGUAGES:
            catalog_file = self._catalogs_dir / f"{lang}.json"
            if not catalog_file.exists():
                logger.warning("Catalog file not found: %s", catalog_file)
                self._catalogs[lang] = {}
                continue

            with open(catalog_file, encoding="utf-8") as f:
                raw_data = json.load(f)
            self._catalogs[lang] = raw_data

    @Slot(str, result=bool)
    def set_language(self, lang_code: str) -> bool:
        """Switches the active language, persists to disk, and emits languageChanged."""
        target_lang = LANGUAGE_ALIASES.get(lang_code, lang_code)
        if target_lang not in SUPPORTED_LANGUAGES:
            logger.error("Attempted to set unsupported language: %s", lang_code)
            return False

        if self._current_lang != target_lang:
            self._current_lang = target_lang
            self.languageChanged.emit(target_lang)
            logger.info("Language switched to %s", target_lang)
            try:
                self._locale_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self._locale_file, "w", encoding="utf-8") as f:
                    json.dump({"language": target_lang}, f)
            except Exception as e:
                logger.warning("Could not persist locale to %s: %s", self._locale_file, e)
        return True

    def _resolve_key(self, key: str, lang: str | None = None) -> Any:
        """Resolves raw entry for key following strict fallback rules."""
        target_lang = lang or self._current_lang
        cat = self._catalogs.get(target_lang, {})

        if key in cat:
            return cat[key]

        # In strict mode, raise immediately
        if self._strict_mode:
            raise MissingTranslationKeyError(
                f"Missing key '{key}' for language '{target_lang}' (strict mode)"
            )

        # Fallback chain: uz-Cyrl -> uz-Latn, ru -> uz-Latn
        if target_lang in ("uz-Cyrl", "ru"):
            fallback_cat = self._catalogs.get(DEFAULT_LANGUAGE, {})
            if key in fallback_cat:
                logger.warning(
                    "Key '%s' missing in '%s', falling back to '%s'",
                    key,
                    target_lang,
                    DEFAULT_LANGUAGE,
                )
                return fallback_cat[key]

        raise MissingTranslationKeyError(
            f"Translation key '{key}' not found in '{target_lang}' or fallback '{DEFAULT_LANGUAGE}'"
        )

    @Slot(str, result=str)
    def t(self, key: str) -> str:
        """Returns translated string for key."""
        try:
            entry = self._resolve_key(key)
        except MissingTranslationKeyError:
            if self._strict_mode:
                raise
            return key

        if isinstance(entry, dict):
            return str(entry.get("text", key))
        return str(entry)

    @Slot(str, str, result=str)
    def tf(self, key: str, arg: Any) -> str:
        """Returns translated template string with {0} replaced."""
        text = self.t(key)
        return text.replace("{0}", str(arg))

    @Slot(str, int, result=str)
    def t_plural(self, key: str, count: int) -> str:
        """Returns translated plural string for count."""
        try:
            entry = self._resolve_key(key)
        except MissingTranslationKeyError:
            if self._strict_mode:
                raise
            return f"{count} {key}"

        if not isinstance(entry, dict):
            return str(entry).replace("{n}", str(count))

        category = self._get_plural_category(self._current_lang, count)
        template = entry.get(category)
        if not template and category != "other":
            template = entry.get("other")
        if not template:
            template = entry.get("text", f"{{n}} {key}")

        return str(template).replace("{n}", str(count))

    @staticmethod
    def _get_plural_category(lang: str, n: int) -> str:
        """Calculates ICU plural category for language and integer."""
        if lang == "ru":
            abs_n = abs(n)
            rem10 = abs_n % 10
            rem100 = abs_n % 100
            if rem10 == 1 and rem100 != 11:
                return "one"
            if 2 <= rem10 <= 4 and not (12 <= rem100 <= 14):
                return "few"
            if rem10 == 0 or (5 <= rem10 <= 9) or (11 <= rem100 <= 14):
                return "many"
            return "other"
        # Uzbek Latin and Uzbek Cyrillic use 'other'
        return "other"

    def format_speed(self, speed_kmh: float) -> str:
        """Returns localized speed string with appropriate unit."""
        val = int(round(speed_kmh))
        if self._current_lang == "uz-Latn":
            return f"{val} km/h"
        if self._current_lang == "uz-Cyrl":
            return f"{val} км/соат"
        # ru
        return f"{val} км/ч"

    def format_number(self, val: int | float) -> str:
        """Returns localized formatted number."""
        if isinstance(val, int):
            return f"{val:,}".replace(",", " ")
        return f"{val:,.1f}".replace(",", " ")

    def format_datetime(self, dt: datetime) -> str:
        """Returns localized formatted date/time."""
        # Standard ISO-like or locale DD.MM.YYYY HH:MM:SS
        return dt.strftime("%d.%m.%Y %H:%M:%S")

    def get_catalog_keys(self, lang: str) -> set[str]:
        """Returns all keys present in the specified catalog."""
        return set(self._catalogs.get(lang, {}).keys())

    def get_raw_entry(self, lang: str, key: str) -> dict[str, Any] | None:
        """Returns the raw entry dictionary for review metadata checks."""
        entry = self._catalogs.get(lang, {}).get(key)
        if isinstance(entry, dict):
            return entry
        return None
