"""Localization service adapter for QML layer."""

from driving_eval.i18n.service import (
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
    I18nService,
    MissingTranslationKeyError,
)

__all__ = [
    "DEFAULT_LANGUAGE",
    "SUPPORTED_LANGUAGES",
    "I18nService",
    "MissingTranslationKeyError",
]
