from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import yaml


class I18n:
    def __init__(self, locales_dir: Path, default: str = "de") -> None:
        self.locales_dir = Path(locales_dir)
        self.default = (default or "de").strip().lower()
        self.messages: Dict[str, Dict[str, object]] = {}
        self.language_labels: Dict[str, str] = {}
        self.lang = self.default
        self._load_locales()
        if self.default not in self.messages and self.messages:
            self.default = next(iter(self.messages))
        self.set_language(self.default)

    def _load_locales(self) -> None:
        if not self.locales_dir.exists():
            return
        for path in sorted(self.locales_dir.glob("*.yml")):
            self._load_locale_file(path)
        for path in sorted(self.locales_dir.glob("*.yaml")):
            self._load_locale_file(path)

    def _load_locale_file(self, path: Path) -> None:
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = yaml.safe_load(handle) or {}
        except (yaml.YAMLError, OSError):
            return
        if not isinstance(data, dict):
            return
        meta = data.pop("meta", {}) if isinstance(data, dict) else {}
        code = path.stem.lower()
        if isinstance(meta, dict):
            label = meta.get("language_name")
            if isinstance(label, str) and label.strip():
                self.language_labels[code] = label.strip()
        self.messages[code] = data

    def set_language(self, code: str) -> bool:
        normalized = (code or "").strip().lower()
        if normalized not in self.messages:
            normalized = self.default if self.default in self.messages else self.lang
            if normalized not in self.messages and self.messages:
                normalized = next(iter(self.messages))
        changed = normalized != self.lang
        self.lang = normalized
        return changed

    def t(self, key: str, **kwargs) -> str:
        if not key:
            return ""
        parts = key.split(".")
        value = self._resolve(self.messages.get(self.lang, {}), parts)
        if value is None and self.default in self.messages:
            value = self._resolve(self.messages.get(self.default, {}), parts)
        if not isinstance(value, str):
            return key
        if kwargs:
            try:
                return value.format(**kwargs)
            except (KeyError, ValueError):
                return value
        return value

    def get_language_label(self, code: str) -> str:
        normalized = (code or "").strip().lower()
        return self.language_labels.get(normalized, normalized or self.lang)

    def get_language_options(self) -> List[Tuple[str, str]]:
        options = []
        for code in self.messages.keys():
            options.append((code, self.get_language_label(code)))
        return sorted(options, key=lambda item: item[1].lower())

    @staticmethod
    def _resolve(data: object, parts: Iterable[str]) -> object:
        current = data
        for part in parts:
            if not isinstance(current, dict):
                return None
            current = current.get(part)
        return current


def build_translator(locales_dir: Path, default: str = "de") -> I18n:
    return I18n(locales_dir, default=default)
