"""
Internationalization (i18n)
Auto-detect system language and provide translations
"""

import json
import locale
from pathlib import Path
from typing import Optional

# Supported languages
SUPPORTED_LANGUAGES = {
    "en": "English",
    "es": "Español",
    "de": "Deutsch",
    "fr": "Français",
    "pt": "Português",
    "ru": "Русский",
    "zh": "中文",
    "ja": "日本語",
    "ko": "한국어",
}

# Current language and translations
_current_lang = "en"
_translations = {}
_fallback = {}  # English fallback


def get_lang_dir() -> Path:
    """Get the language files directory"""
    return Path(__file__).parent.parent / "data" / "lang"


def detect_system_language() -> str:
    """
    Detect the system's language
    
    Returns:
        2-letter language code (e.g., 'en', 'es', 'de')
    """
    try:
        # Get system locale
        system_locale = locale.getdefaultlocale()[0]
        
        if system_locale:
            # Extract language code (first 2 chars)
            lang_code = system_locale[:2].lower()
            
            if lang_code in SUPPORTED_LANGUAGES:
                return lang_code
    except Exception:
        pass
    
    return "en"  # Default to English


def load_language(lang_code: str) -> dict:
    """Load a language file"""
    lang_file = get_lang_dir() / f"{lang_code}.json"
    
    if not lang_file.exists():
        return {}
    
    try:
        with open(lang_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Failed to load language {lang_code}: {e}")
        return {}


def init_i18n(lang_code: Optional[str] = None):
    """
    Initialize internationalization
    
    Args:
        lang_code: Override language code, or None to auto-detect
    """
    global _current_lang, _translations, _fallback
    
    # Load English as fallback
    _fallback = load_language("en")
    
    # Detect or use specified language
    _current_lang = lang_code or detect_system_language()
    
    if _current_lang == "en":
        _translations = _fallback
    else:
        _translations = load_language(_current_lang)
    
    print(f"Language initialized: {_current_lang} ({SUPPORTED_LANGUAGES.get(_current_lang, 'Unknown')})")


def get_current_language() -> str:
    """Get current language code"""
    return _current_lang


def set_language(lang_code: str) -> bool:
    """
    Change the current language
    
    Args:
        lang_code: 2-letter language code
    
    Returns:
        True if successful
    """
    global _current_lang, _translations
    
    if lang_code not in SUPPORTED_LANGUAGES:
        return False
    
    _current_lang = lang_code
    
    if lang_code == "en":
        _translations = _fallback
    else:
        _translations = load_language(lang_code)
    
    return True


def t(key: str, **kwargs) -> str:
    """
    Translate a key to the current language
    
    Args:
        key: Translation key (e.g., "dashboard", "settings.title")
        **kwargs: Format arguments for string interpolation
    
    Returns:
        Translated string, or key if not found
    """
    # Support nested keys with dots
    parts = key.split(".")
    
    # Try current language first
    value = _translations
    for part in parts:
        if isinstance(value, dict) and part in value:
            value = value[part]
        else:
            value = None
            break
    
    # Fall back to English
    if value is None:
        value = _fallback
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                value = key  # Return key if not found
                break
    
    # Format with kwargs if provided
    if isinstance(value, str) and kwargs:
        try:
            value = value.format(**kwargs)
        except KeyError:
            pass
    
    return value if isinstance(value, str) else key


def get_available_languages() -> dict:
    """Get all available languages that have translation files"""
    available = {}
    lang_dir = get_lang_dir()
    
    for code, name in SUPPORTED_LANGUAGES.items():
        if (lang_dir / f"{code}.json").exists():
            available[code] = name
    
    return available


# Auto-initialize on import
init_i18n()
