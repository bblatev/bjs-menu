"""Kitchen Display System Localization Service.

Provides multilingual support for kitchen displays, allowing diverse
kitchen staff to view orders in their preferred language.
"""

import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class SupportedLanguage(str, Enum):
    ENGLISH = "en"
    SPANISH = "es"
    BULGARIAN = "bg"
    FRENCH = "fr"
    GERMAN = "de"
    ITALIAN = "it"
    PORTUGUESE = "pt"
    CHINESE = "zh"
    VIETNAMESE = "vi"
    KOREAN = "ko"
    JAPANESE = "ja"
    ARABIC = "ar"
    RUSSIAN = "ru"
    POLISH = "pl"
    TURKISH = "tr"


@dataclass
class Translation:
    """A translation entry."""
    key: str
    language: SupportedLanguage
    text: str
    category: str = "general"  # general, modifier, station, status, ui


@dataclass
class StationLanguage:
    """Language preference for a station."""
    station_id: str
    language: SupportedLanguage
    fallback_language: SupportedLanguage = SupportedLanguage.ENGLISH


class KDSLocalizationService:
    """Service for KDS multilingual support.

    Features:
    - Per-station language settings
    - Menu item translations
    - Modifier translations
    - UI element translations
    - Order note translations (via external API)
    """

    def __init__(self):
        # Translation storage: {language: {key: text}}
        self._translations: Dict[str, Dict[str, str]] = {}

        # Station language preferences
        self._station_languages: Dict[str, StationLanguage] = {}

        # Menu item translations: {item_id: {language: name}}
        self._item_translations: Dict[str, Dict[str, str]] = {}

        # Modifier translations: {modifier_id: {language: name}}
        self._modifier_translations: Dict[str, Dict[str, str]] = {}

        # Initialize default translations
        self._init_default_translations()

    def _init_default_translations(self):
        """Initialize default UI translations."""
        # English (base)
        self._translations["en"] = {
            # Status
            "status.new": "NEW",
            "status.cooking": "COOKING",
            "status.ready": "READY",
            "status.served": "SERVED",
            "status.voided": "VOIDED",
            "status.rush": "RUSH",
            "status.vip": "VIP",

            # Stations
            "station.grill": "Grill",
            "station.fryer": "Fryer",
            "station.saute": "Sauté",
            "station.salad": "Salad",
            "station.dessert": "Dessert",
            "station.expo": "Expo",
            "station.bar": "Bar",
            "station.pizza": "Pizza",

            # UI
            "ui.bump": "BUMP",
            "ui.recall": "RECALL",
            "ui.priority": "PRIORITY",
            "ui.timer": "Timer",
            "ui.table": "Table",
            "ui.seat": "Seat",
            "ui.course": "Course",
            "ui.items": "Items",
            "ui.notes": "Notes",
            "ui.modifiers": "Modifiers",
            "ui.quantity": "Qty",
            "ui.minutes": "min",
            "ui.seconds": "sec",
            "ui.all_day": "All Day",
            "ui.fire": "FIRE",
            "ui.hold": "HOLD",

            # Common modifiers
            "mod.no": "NO",
            "mod.extra": "EXTRA",
            "mod.light": "LIGHT",
            "mod.side": "SIDE",
            "mod.well_done": "Well Done",
            "mod.medium": "Medium",
            "mod.medium_rare": "Medium Rare",
            "mod.rare": "Rare",

            # Courses
            "course.appetizer": "Appetizer",
            "course.main": "Main",
            "course.dessert": "Dessert",
            "course.drinks": "Drinks",
        }

        # Spanish
        self._translations["es"] = {
            "status.new": "NUEVO",
            "status.cooking": "COCINANDO",
            "status.ready": "LISTO",
            "status.served": "SERVIDO",
            "status.voided": "ANULADO",
            "status.rush": "URGENTE",
            "status.vip": "VIP",

            "station.grill": "Parrilla",
            "station.fryer": "Freidora",
            "station.saute": "Salteado",
            "station.salad": "Ensaladas",
            "station.dessert": "Postres",
            "station.expo": "Expedición",
            "station.bar": "Bar",
            "station.pizza": "Pizza",

            "ui.bump": "LISTO",
            "ui.recall": "RECUPERAR",
            "ui.priority": "PRIORIDAD",
            "ui.timer": "Tiempo",
            "ui.table": "Mesa",
            "ui.seat": "Asiento",
            "ui.course": "Tiempo",
            "ui.items": "Artículos",
            "ui.notes": "Notas",
            "ui.modifiers": "Modificadores",
            "ui.quantity": "Cant",
            "ui.minutes": "min",
            "ui.seconds": "seg",
            "ui.all_day": "Todo el día",
            "ui.fire": "FUEGO",
            "ui.hold": "ESPERAR",

            "mod.no": "SIN",
            "mod.extra": "EXTRA",
            "mod.light": "POCO",
            "mod.side": "APARTE",
            "mod.well_done": "Bien Cocido",
            "mod.medium": "Término Medio",
            "mod.medium_rare": "Medio Rojo",
            "mod.rare": "Rojo",

            "course.appetizer": "Entrada",
            "course.main": "Plato Fuerte",
            "course.dessert": "Postre",
            "course.drinks": "Bebidas",
        }

        # Bulgarian
        self._translations["bg"] = {
            "status.new": "НОВА",
            "status.cooking": "ГОТВИ СЕ",
            "status.ready": "ГОТОВО",
            "status.served": "СЕРВИРАНО",
            "status.voided": "АНУЛИРАНО",
            "status.rush": "СПЕШНО",
            "status.vip": "VIP",

            "station.grill": "Скара",
            "station.fryer": "Фритюрник",
            "station.saute": "Соте",
            "station.salad": "Салати",
            "station.dessert": "Десерти",
            "station.expo": "Експедиция",
            "station.bar": "Бар",
            "station.pizza": "Пица",

            "ui.bump": "ГОТОВО",
            "ui.recall": "ВЪРНИ",
            "ui.priority": "ПРИОРИТЕТ",
            "ui.timer": "Време",
            "ui.table": "Маса",
            "ui.seat": "Място",
            "ui.course": "Смяна",
            "ui.items": "Артикули",
            "ui.notes": "Бележки",
            "ui.modifiers": "Модификатори",
            "ui.quantity": "Бр",
            "ui.minutes": "мин",
            "ui.seconds": "сек",
            "ui.all_day": "Общо",
            "ui.fire": "ОГЪН",
            "ui.hold": "ЧАКАЙ",

            "mod.no": "БЕЗ",
            "mod.extra": "ЕКСТРА",
            "mod.light": "МАЛКО",
            "mod.side": "ОТСТРАНИ",
            "mod.well_done": "Добре Изпечено",
            "mod.medium": "Средно",
            "mod.medium_rare": "Средно Рядко",
            "mod.rare": "Рядко",

            "course.appetizer": "Предястие",
            "course.main": "Основно",
            "course.dessert": "Десерт",
            "course.drinks": "Напитки",
        }

        # French
        self._translations["fr"] = {
            "status.new": "NOUVEAU",
            "status.cooking": "EN COURS",
            "status.ready": "PRÊT",
            "status.served": "SERVI",
            "status.voided": "ANNULÉ",
            "status.rush": "URGENT",
            "status.vip": "VIP",

            "station.grill": "Grill",
            "station.fryer": "Friteuse",
            "station.saute": "Sauté",
            "station.salad": "Salades",
            "station.dessert": "Desserts",
            "station.expo": "Expédition",
            "station.bar": "Bar",
            "station.pizza": "Pizza",

            "ui.bump": "TERMINÉ",
            "ui.recall": "RAPPELER",
            "ui.priority": "PRIORITÉ",
            "ui.timer": "Minuteur",
            "ui.table": "Table",
            "ui.seat": "Place",
            "ui.course": "Service",
            "ui.items": "Articles",
            "ui.notes": "Notes",
            "ui.modifiers": "Modificateurs",
            "ui.quantity": "Qté",
            "ui.minutes": "min",
            "ui.seconds": "sec",
            "ui.all_day": "Journée",
            "ui.fire": "FEU",
            "ui.hold": "ATTENDRE",

            "mod.no": "SANS",
            "mod.extra": "EXTRA",
            "mod.light": "LÉGER",
            "mod.side": "À CÔTÉ",
            "mod.well_done": "Bien Cuit",
            "mod.medium": "À Point",
            "mod.medium_rare": "Rosé",
            "mod.rare": "Bleu",

            "course.appetizer": "Entrée",
            "course.main": "Plat Principal",
            "course.dessert": "Dessert",
            "course.drinks": "Boissons",
        }

        # Chinese (Simplified)
        self._translations["zh"] = {
            "status.new": "新订单",
            "status.cooking": "制作中",
            "status.ready": "完成",
            "status.served": "已上菜",
            "status.voided": "已取消",
            "status.rush": "加急",
            "status.vip": "VIP",

            "station.grill": "烧烤台",
            "station.fryer": "油炸台",
            "station.saute": "炒菜台",
            "station.salad": "沙拉台",
            "station.dessert": "甜点台",
            "station.expo": "出菜口",
            "station.bar": "吧台",
            "station.pizza": "披萨台",

            "ui.bump": "完成",
            "ui.recall": "召回",
            "ui.priority": "优先",
            "ui.timer": "计时",
            "ui.table": "桌号",
            "ui.seat": "座位",
            "ui.course": "上菜顺序",
            "ui.items": "菜品",
            "ui.notes": "备注",
            "ui.modifiers": "特殊要求",
            "ui.quantity": "数量",
            "ui.minutes": "分钟",
            "ui.seconds": "秒",
            "ui.all_day": "全天",
            "ui.fire": "催菜",
            "ui.hold": "暂停",

            "mod.no": "不要",
            "mod.extra": "加",
            "mod.light": "少",
            "mod.side": "分开",
            "mod.well_done": "全熟",
            "mod.medium": "七分熟",
            "mod.medium_rare": "五分熟",
            "mod.rare": "三分熟",

            "course.appetizer": "前菜",
            "course.main": "主菜",
            "course.dessert": "甜点",
            "course.drinks": "饮品",
        }

    # =========================================================================
    # Station Language Settings
    # =========================================================================

    def set_station_language(
        self,
        station_id: str,
        language: SupportedLanguage,
        fallback_language: SupportedLanguage = SupportedLanguage.ENGLISH,
    ) -> StationLanguage:
        """Set language preference for a station."""
        station_lang = StationLanguage(
            station_id=station_id,
            language=language,
            fallback_language=fallback_language,
        )
        self._station_languages[station_id] = station_lang
        logger.info(f"Set station {station_id} language to {language.value}")
        return station_lang

    def get_station_language(self, station_id: str) -> SupportedLanguage:
        """Get language preference for a station."""
        station_lang = self._station_languages.get(station_id)
        if station_lang:
            return station_lang.language
        return SupportedLanguage.ENGLISH

    def list_station_languages(self) -> List[Dict[str, str]]:
        """List all station language settings."""
        return [
            {
                "station_id": sl.station_id,
                "language": sl.language.value,
                "fallback_language": sl.fallback_language.value,
            }
            for sl in self._station_languages.values()
        ]

    # =========================================================================
    # Translations
    # =========================================================================

    def get_translation(
        self,
        key: str,
        language: SupportedLanguage,
        fallback: Optional[str] = None,
    ) -> str:
        """Get a translation for a key."""
        lang_dict = self._translations.get(language.value, {})
        text = lang_dict.get(key)

        if text:
            return text

        # Try English fallback
        if language != SupportedLanguage.ENGLISH:
            eng_dict = self._translations.get("en", {})
            text = eng_dict.get(key)
            if text:
                return text

        # Return fallback or key
        return fallback or key

    def add_translation(
        self,
        key: str,
        language: SupportedLanguage,
        text: str,
    ):
        """Add or update a translation."""
        if language.value not in self._translations:
            self._translations[language.value] = {}

        self._translations[language.value][key] = text

    def get_all_translations(self, language: SupportedLanguage) -> Dict[str, str]:
        """Get all translations for a language."""
        return self._translations.get(language.value, {}).copy()

    # =========================================================================
    # Menu Item Translations
    # =========================================================================

    def set_item_translation(
        self,
        item_id: str,
        language: SupportedLanguage,
        name: str,
    ):
        """Set translation for a menu item."""
        if item_id not in self._item_translations:
            self._item_translations[item_id] = {}

        self._item_translations[item_id][language.value] = name

    def get_item_name(
        self,
        item_id: str,
        language: SupportedLanguage,
        default_name: str,
    ) -> str:
        """Get translated item name."""
        item_trans = self._item_translations.get(item_id, {})
        return item_trans.get(language.value, default_name)

    def set_modifier_translation(
        self,
        modifier_id: str,
        language: SupportedLanguage,
        name: str,
    ):
        """Set translation for a modifier."""
        if modifier_id not in self._modifier_translations:
            self._modifier_translations[modifier_id] = {}

        self._modifier_translations[modifier_id][language.value] = name

    def get_modifier_name(
        self,
        modifier_id: str,
        language: SupportedLanguage,
        default_name: str,
    ) -> str:
        """Get translated modifier name."""
        mod_trans = self._modifier_translations.get(modifier_id, {})
        return mod_trans.get(language.value, default_name)

    # =========================================================================
    # Order Localization
    # =========================================================================

    def localize_order(
        self,
        order: Dict[str, Any],
        station_id: str,
    ) -> Dict[str, Any]:
        """Localize an order for display on a station."""
        language = self.get_station_language(station_id)
        localized = order.copy()

        # Localize status
        if "status" in localized:
            status_key = f"status.{localized['status'].lower()}"
            localized["status_display"] = self.get_translation(status_key, language, localized["status"])

        # Localize items
        if "items" in localized:
            localized_items = []
            for item in localized["items"]:
                loc_item = item.copy()

                # Translate item name
                if "item_id" in item:
                    loc_item["name"] = self.get_item_name(
                        item["item_id"],
                        language,
                        item.get("name", ""),
                    )

                # Translate modifiers
                if "modifiers" in item:
                    loc_mods = []
                    for mod in item["modifiers"]:
                        loc_mod = mod.copy()
                        if "modifier_id" in mod:
                            loc_mod["name"] = self.get_modifier_name(
                                mod["modifier_id"],
                                language,
                                mod.get("name", ""),
                            )
                        loc_mods.append(loc_mod)
                    loc_item["modifiers"] = loc_mods

                localized_items.append(loc_item)

            localized["items"] = localized_items

        # Localize course
        if "course" in localized:
            course_key = f"course.{localized['course'].lower()}"
            localized["course_display"] = self.get_translation(course_key, language, localized["course"])

        return localized

    def get_ui_labels(self, station_id: str) -> Dict[str, str]:
        """Get all UI labels for a station in its configured language."""
        language = self.get_station_language(station_id)

        labels = {}
        all_trans = self.get_all_translations(language)

        for key, text in all_trans.items():
            if key.startswith("ui."):
                label_key = key.replace("ui.", "")
                labels[label_key] = text

        return labels

    # =========================================================================
    # Supported Languages
    # =========================================================================

    def list_supported_languages(self) -> List[Dict[str, str]]:
        """List all supported languages."""
        language_names = {
            "en": "English",
            "es": "Español",
            "bg": "Български",
            "fr": "Français",
            "de": "Deutsch",
            "it": "Italiano",
            "pt": "Português",
            "zh": "中文",
            "vi": "Tiếng Việt",
            "ko": "한국어",
            "ja": "日本語",
            "ar": "العربية",
            "ru": "Русский",
            "pl": "Polski",
            "tr": "Türkçe",
        }

        return [
            {
                "code": lang.value,
                "name": language_names.get(lang.value, lang.value),
                "has_translations": lang.value in self._translations,
            }
            for lang in SupportedLanguage
        ]


# Singleton instance
_kds_localization_service: Optional[KDSLocalizationService] = None


def get_kds_localization_service() -> KDSLocalizationService:
    """Get the KDS localization service singleton."""
    global _kds_localization_service
    if _kds_localization_service is None:
        _kds_localization_service = KDSLocalizationService()
    return _kds_localization_service
