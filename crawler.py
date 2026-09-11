"""Playwright crawler with deep category-to-product traversal and balanced quotas."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from collections import deque
from urllib.parse import parse_qsl, urlencode, urldefrag, urljoin, urlparse, urlsplit, urlunsplit

try:
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_IMPORT_ERROR = ""
except ModuleNotFoundError as error:
    sync_playwright = None
    PlaywrightError = Exception
    PlaywrightTimeoutError = TimeoutError
    PLAYWRIGHT_IMPORT_ERROR = str(error)

NAVIGATION_TIMEOUT = 35_000
DEFAULT_HEADERS = {
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.5",
}

MEDIA_EXTENSIONS_PATTERN = re.compile(
    r"\.(?:pdf|jpg|jpeg|png|gif|svg|webp|avif|mp4|webm|avi|mov|mp3|zip|rar|tar|gz|css|js|woff|woff2|ttf|eot)(?:$|\?)",
    re.IGNORECASE,
)


def normalize_url(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    if not re.match(r"^https?://", value, re.IGNORECASE):
        value = "https://" + value
    value, _ = urldefrag(value)
    parsed = urlsplit(value)

    # Исключаем параметры пагинации, сортировки и аналитики во избежание зацикливания
    ignored_params = (
        "utm_", "fbclid", "gclid", "yclid", "_openstat",
        "sort", "order", "orderby", "dir", "limit", "view", "page", "p"
    )
    query = [
        (key, item)
        for key, item in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.casefold().startswith(ignored_params)
    ]
    value = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), ""))
    return value.rstrip("/") or value


def _same_domain(first: str, second: str) -> bool:
    left = (urlparse(first).hostname or "").casefold().removeprefix("www.")
    right = (urlparse(second).hostname or "").casefold().removeprefix("www.")
    return bool(left and left == right)


def _looks_like_product_url(url: str) -> bool:
    path = (urlparse(url).path or "").casefold()
    return (
        path.endswith((".html", ".htm"))
        or any(marker in path for marker in ("/product/", "/products/", "/item/", "/goods/", "/p/"))
    )


def _looks_like_catalog_url(url: str) -> bool:
    if _looks_like_product_url(url):
        return False
    path = (urlparse(url).path or "").casefold()
    return any(marker in path.split("/") for marker in ("catalog", "catalogue", "category", "categories", "shop"))


def classify_url(url: str) -> str:
    """Определяет роль страницы: главная, товар, каталог, статьи или инфо."""
    path = (urlparse(url).path or "").strip("/").casefold()
    if not path:
        return "home"
    if _looks_like_product_url(url):
        return "product"

    # Новости, промо-акции и статьи
    article_markers = ("news", "articles", "article", "blog", "stati", "novosti", "obzory", "promo", "actions", "action", "sale", "skidki", "akcii")
    if any(marker in path.split("/") for marker in article_markers):
        return "article"

    # Служебные инфо-разделы
    info_markers = ("about", "contacts", "delivery", "payment", "warranty", "service", "dostavka", "oplata", "garantiya", "servis", "policy", "privacy")
    if any(marker in path.split("/") for marker in info_markers):
        return "info"

    if _looks_like_catalog_url(url) or len(path.split("/")) <= 3:
        return "catalog"

    return "info"


NAV_LINK_SELECTOR = (
    "header a[href], nav a[href], footer a[href], [role='navigation'] a[href], "
    "[class*='header'] a[href], [class*='footer'] a[href], [class*='menu'] a[href]"
)


def _internal_links(page, base_url: str, selector: str = "a[href]", allow_hidden: bool = False) -> list[str]:
    # allow_hidden=True позволяет доставать подкатегории из выпадающих шторок меню
    js_code = f"""
    elements => elements.filter(element => {{
        if ({str(allow_hidden).lower()}) return true;
        const style = getComputedStyle(element);
        const rect = element.getBoundingClientRect();
        return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
    }}).map(element => element.href)
    """
    links = page.eval_on_selector_all(selector, js_code)
    result: list[str] = []
    seen: set[str] = set()
    for raw_url in links:
        raw_str = str(raw_url).strip()
        if raw_str.startswith(("javascript:", "tel:", "mailto:")):
            continue
        url = normalize_url(urljoin(base_url, raw_str))
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not _same_domain(url, base_url):
            continue
        if MEDIA_EXTENSIONS_PATTERN.search(parsed.path):
            continue
        if url in seen:
            continue
        seen.add(url)
        result.append(url)
    return result


def _expand_dynamic_content(page) -> None:
    selectors = [
        "button[aria-expanded='false']",
        "[role='button'][aria-expanded='false']",
        "summary",
        "[role='tab']",
        ".swiper-button-next",
        ".slick-next",
        ".owl-next",
    ]
    for selector in selectors:
        try:
            locator = page.locator(selector)
            count = min(locator.count(), 30)
            for index in range(count):
                try:
                    item = locator.nth(index)
                    if item.is_visible(timeout=150):
                        item.click(timeout=500, force=True)
                        page.wait_for_timeout(60)
                except (PlaywrightError, PlaywrightTimeoutError):
                    continue
        except (PlaywrightError, PlaywrightTimeoutError):
            continue


def _scroll_to_end(page) -> None:
    last_height = 0
    for _ in range(6):
        height = page.evaluate("document.documentElement.scrollHeight")
        page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
        page.wait_for_timeout(250)
        new_height = page.evaluate("document.documentElement.scrollHeight")
        if new_height == last_height or new_height == height:
            break
        last_height = new_height
    page.evaluate("window.scrollTo(0, 0)")


def _collect_page(page, url: str, depth: int, expand_dynamic: bool) -> dict:
    response = page.goto(url, wait_until="domcontentloaded", timeout=NAVIGATION_TIMEOUT)
    page.wait_for_timeout(500)

    # Игнорируем страницы 404, 500 и прочие системные сбои
    if response and response.status >= 400:
        return {
            "url": url, "depth": depth, "title": "", "description": "",
            "text": "", "attributes": "", "site_terms": [], "model_terms": [],
            "issues": [], "error": f"HTTP {response.status} ({response.status_text})",
            "links": [], "nav_links": [],
        }

    if expand_dynamic:
        _expand_dynamic_content(page)
    _scroll_to_end(page)

    # Очищаем DOM от скриптов, стилей и SVG перед извлечением текста
    page.evaluate("""() => {
        const remove = ['script', 'style', 'noscript', 'svg', 'iframe', 'template'];
        document.querySelectorAll(remove.join(',')).forEach(el => el.remove());
    }""")

    text = page.locator("body").inner_text(timeout=5_000)

    attributes = page.eval_on_selector_all(
        "[alt], [title], [placeholder], [aria-label]",
        """
        elements => elements.map(element => {
          const values = ['alt', 'title', 'placeholder', 'aria-label']
            .filter(name => element.hasAttribute(name))
            .map(name => `${name}: ${element.getAttribute(name)}`);
          return values.join(' | ');
        }).filter(Boolean).join(String.fromCharCode(10))
        """,
    )
    site_terms = page.eval_on_selector_all(
        "[class*='logo'], [id*='logo'], [data-brand], [itemprop='brand'], meta[property='og:site_name']",
        """
        elements => elements.map(element => (
          element.innerText || element.getAttribute('alt') ||
          element.getAttribute('aria-label') || element.getAttribute('content') || ''
        ).trim()).filter(Boolean).slice(0, 50)
        """,
    )
    model_selector = "h1, [itemprop='name'], [class*='model'], [id*='model'], [class*='sku'], [class*='product-name']"
    model_terms = page.eval_on_selector_all(
        model_selector,
        """
        elements => elements.map(element => (
          element.innerText || element.getAttribute('content') || ''
        ).trim()).filter(Boolean).slice(0, 100)
        """,
    )
    title = page.title()
    description = page.locator("meta[name='description']").get_attribute("content") or ""

    return {
        "url": url, "depth": depth, "title": title, "description": description,
        "text": text, "attributes": attributes, "site_terms": site_terms or [],
        "model_terms": model_terms or [], "issues": [], "error": "",
        "links": _internal_links(page, url),
        "nav_links": _internal_links(page, url, NAV_LINK_SELECTOR, allow_hidden=True),
    }


def _install_browser_if_needed() -> None:
    if sync_playwright is None:
        raise RuntimeError("Не установлен Playwright. Добавьте playwright в requirements.txt.") from ModuleNotFoundError(PLAYWRIGHT_IMPORT_ERROR)
    with sync_playwright() as playwright:
        executable = playwright.chromium.executable_path
    if os.path.exists(executable):
        return
    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)


def crawl_site(
    start_url: str,
    max_depth: int | None = 3,
    max_pages: int | None = 100,
    product_sample: int = 2,
    expand_dynamic: bool = True,
    smart_mode: bool = True,
    progress=None,
    status=None,
) -> list[dict]:
    start_url = normalize_url(start_url)
    if not start_url:
        raise ValueError("Не указана ссылка на сайт")
    if urlparse(start_url).scheme not in {"http", "https"}:
        raise ValueError("Ссылка должна начинаться с http:// или https://")

    total_limit = max_pages or 100
    product_sample = max(1, min(int(product_sample), 5))

    # Сбалансированные квоты для распределения типов страниц
    LIMIT_CATALOG = int(total_limit * 0.35)   # До 35% категорий и подкатегорий
    LIMIT_PRODUCT = int(total_limit * 0.45)   # До 45% товаров
    LIMIT_CONTENT = total_limit - (LIMIT_CATALOG + LIMIT_PRODUCT)  # Остаток под статьи, акции и инфо

    counts = {"catalog": 0, "product": 0, "content": 0}

    queue = deque([(start_url, 0, "home")])
    visited: set[str] = set()
    enqueued: set[str] = {start_url}
    results: list[dict] = []
    limit_reached = False

    _install_browser_if_needed()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, args=["--disable-dev-shm-usage", "--no-sandbox"])
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            locale="ru-RU",
            extra_http_headers=DEFAULT_HEADERS,
            ignore_https_errors=True,
        )
        page = context.new_page()
        page.set_default_navigation_timeout(NAVIGATION_TIMEOUT)

        try:
            while queue and len(results) < total_limit:
                url, depth, kind = queue.popleft()
                if url in visited:
                    continue
                visited.add(url)

                if status:
                    status(f"Проверяется [{kind}]: {url} ({len(results) + 1}/{total_limit})")
                if progress:
                    progress(len(results) / total_limit)

                try:
                    result = _collect_page(page, url, depth, expand_dynamic)
                except Exception as error:
                    result = {
                        "url": url, "depth": depth, "title": "", "description": "",
                        "text": "", "attributes": "", "site_terms": [], "model_terms": [],
                        "issues": [], "error": str(error), "links": [], "nav_links": [],
                    }

                results.append(result)
                if result.get("error"):
                    continue

                links = result.get("links", [])
                nav_links = result.get("nav_links", [])

                if kind == "home":
                    # С главной сразу забираем инфо-разделы и акции из навигации
                    for link in nav_links:
                        c_type = classify_url(link)
                        if c_type in {"info", "article"} and counts["content"] < LIMIT_CONTENT and link not in enqueued:
                            enqueued.add(link)
                            counts["content"] += 1
                            queue.append((link, depth + 1, c_type))

                    # Забираем основные категории каталога
                    for link in nav_links + links:
                        if classify_url(link) == "catalog" and counts["catalog"] < LIMIT_CATALOG and link not in enqueued:
                            enqueued.add(link)
                            counts["catalog"] += 1
                            queue.append((link, depth + 1, "catalog"))

                elif kind == "catalog":
                    # 1. Если внутри раздела есть подкатегории (Встраиваемые, Компактные и т.д.)
                    subcats = [l for l in links if classify_url(l) == "catalog" and l not in enqueued]
                    for sub in subcats[:3]:  # Берем до 3 подкатегорий
                        if counts["catalog"] < LIMIT_CATALOG:
                            enqueued.add(sub)
                            counts["catalog"] += 1
                            queue.appendleft((sub, depth + 1, "catalog"))

                    # 2. Берем товары из этой категории и сразу ставим вперед на проверку
                    prods = [l for l in links if classify_url(l) == "product" and l not in enqueued]
                    for prod in prods[:product_sample]:
                        if counts["product"] < LIMIT_PRODUCT:
                            enqueued.add(prod)
                            counts["product"] += 1
                            queue.appendleft((prod, depth + 1, "product"))

                elif kind in {"info", "article"}:
                    # Из общих разделов статей берем отдельные статьи/акции
                    for link in links:
                        c_type = classify_url(link)
                        if c_type in {"info", "article"} and counts["content"] < LIMIT_CONTENT and link not in enqueued:
                            enqueued.add(link)
                            counts["content"] += 1
                            queue.append((link, depth + 1, c_type))

                if progress:
                    progress(len(results) / total_limit)
        finally:
            context.close()
            browser.close()

    if len(results) >= total_limit:
        limit_reached = True

    if results:
        results[0]["_limit_reached"] = limit_reached

    if status:
        status(f"Проверка завершена: {len(results)} страниц")
    return results
