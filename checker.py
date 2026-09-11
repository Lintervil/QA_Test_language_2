"""Ultra-fast detection of untranslated English text in Russian website content."""

from __future__ import annotations

import re
from collections import Counter
from typing import Iterable
from urllib.parse import urlparse

from exceptions import BASE_EXCEPTIONS

DOMAIN_SUFFIXES = {"com", "ru", "net", "org", "info", "рф", "by", "kz"}

FILE_SUFFIXES = {
    "jpg", "jpeg", "png", "gif", "svg", "webp", "avif", "ico",
    "mp4", "mp3", "avi", "mov", "webm", "mkv",
    "pdf", "doc", "docx", "xls", "xlsx", "zip", "rar", "csv", "json",
    "css", "js", "woff", "woff2", "ttf", "eot"
}

GENERIC_SITE_TERMS = {
    "www", "shop", "store", "online", "official", "site", "home", "main",
    "catalog", "ru", "com", "net", "org", "info",
}

# Регулярка для отсечения технических единиц бытовой техники
TECHNICAL_UNITS_RE = re.compile(
    r"^\d+(?:[.,]\d+)?\s*(?:v|w|kw|kwh|a|ma|hz|khz|mhz|ghz|db|rpm|kg|g|mg|l|ml|mm|cm|m|km|bar|pa|kpa|btu|din|ip\d{2})$",
    re.IGNORECASE
)

# НЮАНС №2: Конструкции вида «Русский текст (English text)» или [English]
# Вырезает латиницу в скобках, если перед ними идет русский текст
BILINGUAL_RE = re.compile(
    r"([А-Яа-яЁё0-9\s\-–—/]{1,80})\s*[\(\[][A-Za-z0-9\s\-–—,./+#'\"]{1,100}[\)\]]"
)

# НЮАНС №1: Ссылки и файлы
URL_RE = re.compile(r"https?://\S+|www\.\S+")
FILES_RE = re.compile(
    r"\b[\w\-.]+\.(?:jpg|jpeg|png|gif|svg|webp|avif|mp4|webm|avi|mov|mp3|pdf|zip|rar|css|js|json|xml)\b",
    re.IGNORECASE
)


def parse_exceptions(value: str | Iterable[str] | None) -> set[str]:
    if not value:
        return set()
    if isinstance(value, str):
        values = re.split(r"[,;\n]+", value)
    else:
        values = value
    return {str(item).strip().casefold() for item in values if str(item).strip()}


def automatic_exceptions(start_url: str, pages: list[dict]) -> set[str]:
    """Быстрый сбор домена и моделей без создания мусорных фраз."""
    result = set()
    host = urlparse(start_url).hostname or ""
    for part in host.split("."):
        if len(part) > 2 and part.casefold() not in GENERIC_SITE_TERMS:
            result.add(part.casefold())

    for page in pages:
        raw_terms = page.get("site_terms", []) + page.get("model_terms", [])
        for term in raw_terms:
            for token in re.findall(r"\b[A-Za-z0-9-]{2,}\b", str(term)):
                t_lower = token.casefold()
                if t_lower in GENERIC_SITE_TERMS or len(t_lower) < 3:
                    continue
                if any(c.isdigit() for c in token) or token.isupper() or token[0].isupper():
                    result.add(t_lower)
    return result


def is_technical_token(word: str) -> bool:
    """Проверка, является ли слово артикулом, габаритом или системным обозначением."""
    if len(word) <= 1:
        return True

    lower = word.casefold()
    if lower in DOMAIN_SUFFIXES or lower in FILE_SUFFIXES:
        return True

    # Габариты (60x60, 595x595x564)
    if re.fullmatch(r"\d+x\d+(?:x\d+)?", lower):
        return True

    # Единицы измерений техники (220v, 1400rpm, 50hz)
    if TECHNICAL_UNITS_RE.match(word):
        return True

    # Артикулы моделей с цифрами и буквами (BOP798S54X, SPV4HMX14Q)
    has_digit = any(c.isdigit() for c in word)
    has_alpha = any(c.isalpha() for c in word)
    if has_digit and has_alpha:
        return True

    # Аббревиатуры из заглавных букв (LED, OLED, NFC, USB)
    if re.fullmatch(r"[A-Z0-9]{2,}(?:[-/][A-Z0-9]+)*", word):
        return True

    return False


def clean_text_fast(text: str, multiword_exceptions: list[str]) -> str:
    """Мгновенная очистка текста в 3 шага."""
    # 1. Вырезаем формат «Слово (Word)»
    cleaned = BILINGUAL_RE.sub(r"\1 ()", text)

    # 2. Вырезаем URL и имена файлов
    cleaned = URL_RE.sub(" ", cleaned)
    cleaned = FILES_RE.sub(" ", cleaned)

    # 3. Вырезаем словосочетания из исключений за один проход
    if multiword_exceptions:
        pattern = r"\b(?:" + "|".join(re.escape(w) for w in multiword_exceptions) + r")\b"
        cleaned = re.sub(pattern, " ", cleaned, flags=re.IGNORECASE)

    return cleaned


def _make_context(original_text: str, start: int, end: int, radius: int = 50) -> str:
    left = max(0, start - radius)
    right = min(len(original_text), end + radius)
    snippet = re.sub(r"\s+", " ", original_text[left:right]).strip()
    return f"...{snippet}..."


def find_english_issues(
    text: str,
    source: str,
    allowlist: set[str],
    multiword_exceptions: list[str],
    limit: int = 200,
) -> list[dict[str, str]]:
    if not text or len(text.strip()) == 0:
        return []

    cleaned = clean_text_fast(text, multiword_exceptions)

    # Находим все английские слова
    tokens = list(re.finditer(r"\b[A-Za-z][A-Za-z0-9]*(?:[-'][A-Za-z0-9]+)*\b", cleaned))
    if not tokens:
        return []

    # Отбираем только неизвестные (проблемные) слова
    problem_tokens = []
    for m in tokens:
        word = m.group(0)
        if word.casefold() in allowlist or is_technical_token(word):
            continue
        problem_tokens.append(m)

    if not problem_tokens:
        return []

    # Склеиваем идущие подряд слова в целые фразы (например: 'Add' + 'to' + 'cart')
    issues: list[dict[str, str]] = []
    seen: set[str] = set()

    current_group = [problem_tokens[0]]
    for token in problem_tokens[1:]:
        prev = current_group[-1]
        gap = cleaned[prev.end():token.start()]
        # Если между словами только пробелы (длиной не более 3 символов) — объединяем во фразу
        if gap.strip() == "" and len(gap) <= 3:
            current_group.append(token)
        else:
            phrase = " ".join(t.group(0) for t in current_group)
            start_pos = current_group[0].start()
            end_pos = current_group[-1].end()
            ctx = _make_context(text, start_pos, end_pos)
            if phrase.casefold() not in seen:
                seen.add(phrase.casefold())
                issues.append({"word": phrase, "context": ctx, "source": source})
            current_group = [token]

    if current_group:
        phrase = " ".join(t.group(0) for t in current_group)
        start_pos = current_group[0].start()
        end_pos = current_group[-1].end()
        ctx = _make_context(text, start_pos, end_pos)
        if phrase.casefold() not in seen:
            issues.append({"word": phrase, "context": ctx, "source": source})

    return issues[:limit]


def check_page(
    page: dict,
    custom_exceptions: str | Iterable[str] | None = None,
    automatic_whitelist: str | Iterable[str] | None = None,
) -> list[dict[str, str]]:
    if page.get("error"):
        return []

    allowlist = (
        {item.casefold() for item in BASE_EXCEPTIONS}
        | parse_exceptions(custom_exceptions)
        | parse_exceptions(automatic_whitelist)
    )

    # Список фраз с пробелами, отсортированный по длине
    multiword_exceptions = sorted([w for w in allowlist if " " in w], key=len, reverse=True)

    issues: list[dict[str, str]] = []

    # 1. Текст страницы
    issues.extend(find_english_issues(page.get("text", ""), "Видимый текст", allowlist, multiword_exceptions))

    # 2. Атрибуты (alt, title, placeholder)
    attrs = re.sub(r"(?:^|\n)(?:alt|title|placeholder|aria-label):\s*", "\n", page.get("attributes", ""), flags=re.IGNORECASE)
    issues.extend(find_english_issues(attrs, "Атрибуты интерфейса", allowlist, multiword_exceptions))

    # 3. Мета-теги
    issues.extend(find_english_issues(page.get("title", ""), "HTML title", allowlist, multiword_exceptions))
    issues.extend(find_english_issues(page.get("description", ""), "Meta description", allowlist, multiword_exceptions))

    # Финальная дедупликация
    unique: list[dict[str, str]] = []
    seen = set()
    for issue in issues:
        key = (issue["word"].casefold(), issue["source"], issue["context"].casefold())
        if key not in seen:
            seen.add(key)
            unique.append(issue)

    return unique


def top_words(pages: list[dict]) -> list[tuple[str, int]]:
    counter = Counter(
        issue["word"].casefold()
        for page in pages
        for issue in page.get("issues", [])
    )
    return counter.most_common(10)
