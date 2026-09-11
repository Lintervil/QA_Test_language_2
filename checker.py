"""Detection of untranslated English text in Russian website content."""

from __future__ import annotations

import re
from collections import Counter
from typing import Iterable
from urllib.parse import urlparse

from exceptions import BASE_EXCEPTIONS


ENGLISH_RUN_RE = re.compile(
    r"(?<![A-Za-z])"
    r"(?:[A-Za-z][A-Za-z0-9]*(?:[._/+&'-][A-Za-z0-9]+)*)"
    r"(?:\s+(?:[A-Za-z][A-Za-z0-9]*(?:[._/+&'-][A-Za-z0-9]+)*)){0,6}"
    r"(?![A-Za-z])"
)
TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9]*(?:[._/+&'-][A-Za-z0-9]+)*")
DOMAIN_SUFFIXES = {"com", "ru", "net", "org", "info", "рф", "by", "kz"}

# НЮАНС №1: Расширенный список расширений статики и медиа
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

# Регулярка для технических единиц бытовой техники (V, W, Hz, rpm, mm, cm, kg, dB и т.д.)
TECHNICAL_UNITS_RE = re.compile(
    r"^\d+(?:[.,]\d+)?\s*(?:v|w|kw|kwh|a|ma|hz|khz|mhz|ghz|db|rpm|kg|g|mg|l|ml|mm|cm|m|km|bar|pa|kpa|btu|din|ip\d{2})$",
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
    values: list[str] = []
    host = urlparse(start_url).hostname or ""
    values.extend(re.findall(r"[A-Za-z][A-Za-z0-9-]{2,}", host))
    for page in pages:
        values.extend(page.get("site_terms", []))
        values.extend(page.get("model_terms", []))

    result: set[str] = set()
    for value in values:
        for match in ENGLISH_RUN_RE.finditer(str(value)):
            phrase = match.group(0).strip(" .,:;!?\"'«»()[]{}")
            if not phrase:
                continue
            tokens = TOKEN_RE.findall(phrase)
            if not tokens:
                continue
            if phrase.casefold() not in GENERIC_SITE_TERMS:
                result.add(phrase.casefold())
            for token in tokens:
                if token.casefold() in GENERIC_SITE_TERMS or len(token) < 3:
                    continue
                if any(char.isdigit() for char in token) or token[:1].isupper() or token.isupper():
                    result.add(token.casefold())
    return result


def _is_inside_translation_parentheses(text: str, start: int, end: int) -> bool:
    """
    НЮАНС №2: Проверяет, находится ли слово в скобках вида:
    'Посудомоечная машина (Dishwasher)' или [Built-in].
    """
    before = text[:start]
    open_round = before.rfind("(")
    close_round = before.rfind(")")
    open_square = before.rfind("[")
    close_square = before.rfind("]")

    # Определяем тип скобки
    open_idx = -1
    close_char = ""
    if open_round > close_round:
        open_idx = open_round
        close_char = ")"
    elif open_square > close_square:
        open_idx = open_square
        close_char = "]"

    if open_idx == -1:
        return False

    after = text[end:]
    close_idx_rel = after.find(close_char)
    if close_idx_rel < 0:
        return False

    close_idx = end + close_idx_rel

    # Скобки не должны разрываться абзацами или быть длиннее 100 символов
    inside_content = text[open_idx:close_idx + 1]
    if "\n" in inside_content or len(inside_content) > 100:
        return False

    # До открывающей скобки должен присутствовать русский текст
    before_bracket = before[:open_idx]
    return bool(re.search(r"[А-Яа-яЁё]", before_bracket[-80:]))


def _is_technical_identifier(candidate: str, text: str, start: int, end: int) -> bool:
    """НЮАНС №1 и характеристики: отсекает файлы, габариты, артикулы и единицы измерения."""
    lower = candidate.casefold()
    if len(candidate) == 1:
        return True
    if any(marker in lower for marker in ("://", "@")):
        return True
    if start and text[start - 1] in {"/", "\\"}:
        return True
    if end < len(text) and text[end] in {"/", "\\"}:
        return True

    # Расширения файлов (image.png, clip.mp4)
    if "." in candidate and candidate.rsplit(".", 1)[-1].casefold() in (DOMAIN_SUFFIXES | FILE_SUFFIXES):
        return True

    # Единицы измерений (напр. 220v, 1400rpm, 50hz)
    if TECHNICAL_UNITS_RE.match(candidate):
        return True

    # Габариты (напр. 60x60x85)
    if re.fullmatch(r"\d+x\d+(?:x\d+)?", lower):
        return True

    # Если спереди или сзади вплотную примыкает цифра
    if (start and text[start - 1].isdigit()) or (end < len(text) and text[end].isdigit()):
        return True

    # Смесь букв и цифр (артикулы моделей: SPV4HMX14Q, BWD421PRO)
    if any(char.isdigit() for char in candidate) and any(char.isalpha() for char in candidate):
        return True

    # Аббревиатуры из заглавных букв (LED, OLED, NFC)
    if re.fullmatch(r"[A-Z]{2,}(?:[-/][A-Z0-9]+)*", candidate):
        return True

    if lower in DOMAIN_SUFFIXES:
        return True

    return False


def _context(text: str, start: int, end: int, radius: int = 62) -> str:
    left = max(0, start - radius)
    right = min(len(text), end + radius)
    value = re.sub(r"\s+", " ", text[left:right]).strip()
    if left:
        value = "..." + value
    if right < len(text):
        value += "..."
    return value


def find_english_issues(
    text: str,
    source: str,
    custom_exceptions: str | Iterable[str] | None = None,
    limit: int = 200,
) -> list[dict[str, str]]:
    if not text:
        return []

    allowlist = {item.casefold() for item in BASE_EXCEPTIONS} | parse_exceptions(custom_exceptions)
    issues: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()

    for match in ENGLISH_RUN_RE.finditer(text):
        candidate = match.group(0).strip(" .,:;!?\"'«»()[]{}")
        if not candidate or _is_technical_identifier(candidate, text, match.start(), match.end()):
            continue
        tokens = TOKEN_RE.findall(candidate)
        if not tokens:
            continue
        if candidate.casefold() in allowlist:
            continue

        candidate_for_tokens = candidate
        for allowed_phrase in sorted(
            (item for item in allowlist if " " in item),
            key=len,
            reverse=True,
        ):
            candidate_for_tokens = re.sub(
                rf"(?<![A-Za-z]){re.escape(allowed_phrase)}(?![A-Za-z])",
                " ",
                candidate_for_tokens,
                flags=re.IGNORECASE,
            )

        unknown = [
            token for token in TOKEN_RE.findall(candidate_for_tokens)
            if token.casefold() not in allowlist and not TECHNICAL_UNITS_RE.match(token)
        ]

        if not unknown or _is_inside_translation_parentheses(text, match.start(), match.end()):
            continue

        term = " ".join(unknown)
        key = (term.casefold(), source, _context(text, match.start(), match.end()).casefold())
        if key in seen:
            continue
        seen.add(key)
        issues.append(
            {
                "word": term,
                "context": _context(text, match.start(), match.end()),
                "source": source,
            }
        )
        if len(issues) >= limit:
            break
    return issues


def check_page(
    page: dict,
    custom_exceptions: str | Iterable[str] | None = None,
    automatic_whitelist: str | Iterable[str] | None = None,
) -> list[dict[str, str]]:
    exceptions = parse_exceptions(custom_exceptions) | parse_exceptions(automatic_whitelist)
    issues: list[dict[str, str]] = []

    # Не ищем ошибки на страницах, вернувших HTTP-ошибку
    if page.get("error"):
        return []

    issues.extend(find_english_issues(page.get("text", ""), "Видимый текст", exceptions))

    attributes = re.sub(
        r"(?:^|\n)(?:alt|title|placeholder|aria-label):\s*",
        "\n",
        page.get("attributes", ""),
        flags=re.IGNORECASE,
    )
    issues.extend(find_english_issues(attributes, "Атрибуты интерфейса", exceptions))
    issues.extend(find_english_issues(page.get("title", ""), "HTML title", exceptions))
    issues.extend(find_english_issues(page.get("description", ""), "Meta description", exceptions))

    unique: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
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
