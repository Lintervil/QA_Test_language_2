"""Playwright crawler used by the Streamlit translation checker."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from collections import deque
from urllib.parse import urldefrag, urljoin, urlparse

try:
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_IMPORT_ERROR = ""
except ModuleNotFoundError as error:
    # Keep the Streamlit interface available so it can show a useful setup error.
    sync_playwright = None
    PlaywrightError = Exception
    PlaywrightTimeoutError = TimeoutError
    PLAYWRIGHT_IMPORT_ERROR = str(error)


MAX_SCREENSHOT_HEIGHT = 6000
NAVIGATION_TIMEOUT = 35_000
DEFAULT_HEADERS = {
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.5",
}


def normalize_url(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    if not re.match(r"^https?://", value, re.IGNORECASE):
        value = "https://" + value
    value, _ = urldefrag(value)
    return value.rstrip("/") or value


def _same_domain(first: str, second: str) -> bool:
    left = (urlparse(first).hostname or "").casefold().removeprefix("www.")
    right = (urlparse(second).hostname or "").casefold().removeprefix("www.")
    return bool(left and left == right)


def _internal_links(page, base_url: str) -> list[str]:
    links = page.eval_on_selector_all(
        "a[href]",
        "elements => elements.map(element => element.href)",
    )
    result: list[str] = []
    seen: set[str] = set()
    for raw_url in links:
        url = normalize_url(urljoin(base_url, str(raw_url)))
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not _same_domain(url, base_url):
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
        "button[aria-label*='next' i]",
        "button[title*='next' i]",
    ]
    for selector in selectors:
        try:
            locator = page.locator(selector)
            count = min(locator.count(), 80)
            for index in range(count):
                try:
                    item = locator.nth(index)
                    if item.is_visible(timeout=250):
                        item.click(timeout=900, force=True)
                        page.wait_for_timeout(100)
                except (PlaywrightError, PlaywrightTimeoutError):
                    continue
        except (PlaywrightError, PlaywrightTimeoutError):
            continue


def _scroll_to_end(page) -> None:
    last_height = 0
    for _ in range(12):
        height = page.evaluate("document.documentElement.scrollHeight")
        page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
        page.wait_for_timeout(350)
        new_height = page.evaluate("document.documentElement.scrollHeight")
        if new_height == last_height or new_height == height:
            break
        last_height = new_height
    page.evaluate("window.scrollTo(0, 0)")


def _collect_page(page, url: str, depth: int, expand_dynamic: bool) -> dict:
    page.goto(url, wait_until="domcontentloaded", timeout=NAVIGATION_TIMEOUT)
    page.wait_for_timeout(800)
    if expand_dynamic:
        _expand_dynamic_content(page)
    _scroll_to_end(page)
    if expand_dynamic:
        _expand_dynamic_content(page)
        _scroll_to_end(page)

    text = page.locator("body").inner_text(timeout=5_000)
    attributes = page.eval_on_selector_all(
        "[alt], [title], [placeholder], [aria-label]",
        """
        elements => elements.map(element => {
          const values = ['alt', 'title', 'placeholder', 'aria-label']
            .filter(name => element.hasAttribute(name))
            .map(name => `${name}: ${element.getAttribute(name)}`);
          return values.join(' | ');
        }).filter(Boolean).join('\n')
        """,
    )
    title = page.title()
    description = page.locator("meta[name='description']").get_attribute("content") or ""
    page_height = page.evaluate("Math.max(document.documentElement.scrollHeight, window.innerHeight)")
    viewport_width = page.evaluate("window.innerWidth") or 1440
    screenshot = page.screenshot(
        clip={
            "x": 0,
            "y": 0,
            "width": min(int(viewport_width), 1440),
            "height": min(int(page_height), MAX_SCREENSHOT_HEIGHT),
        },
        animations="disabled",
    )
    return {
        "url": url,
        "depth": depth,
        "title": title,
        "description": description,
        "text": text,
        "attributes": attributes,
        "screenshot": screenshot,
        "issues": [],
        "error": "",
        "links": _internal_links(page, url),
    }


def _install_browser_if_needed() -> None:
    """Streamlit Community Cloud may not have the Playwright browser cache yet."""
    if sync_playwright is None:
        raise RuntimeError(
            "Не установлен Playwright. Добавьте requirements.txt в корень GitHub-репозитория "
            "рядом с app.py и перезапустите приложение."
        ) from ModuleNotFoundError(PLAYWRIGHT_IMPORT_ERROR)
    with sync_playwright() as playwright:
        executable = playwright.chromium.executable_path
    if os.path.exists(executable):
        return
    subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def crawl_site(
    start_url: str,
    max_depth: int = 0,
    max_pages: int = 20,
    expand_dynamic: bool = True,
    progress=None,
    status=None,
) -> list[dict]:
    """Breadth-first crawl of one domain, returning one result per visited page."""
    start_url = normalize_url(start_url)
    if not start_url:
        raise ValueError("Не указана ссылка на сайт")
    if urlparse(start_url).scheme not in {"http", "https"}:
        raise ValueError("Ссылка должна начинаться с http:// или https://")

    max_depth = max(0, min(int(max_depth), 3))
    max_pages = max(1, min(int(max_pages), 20))
    queue = deque([(start_url, 0)])
    queued = {start_url}
    results: list[dict] = []

    _install_browser_if_needed()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            args=["--disable-dev-shm-usage", "--no-sandbox"],
        )
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            locale="ru-RU",
            extra_http_headers=DEFAULT_HEADERS,
            ignore_https_errors=True,
        )
        page = context.new_page()
        page.set_default_timeout(5_000)
        page.set_default_navigation_timeout(NAVIGATION_TIMEOUT)
        try:
            while queue and len(results) < max_pages:
                url, depth = queue.popleft()
                if status:
                    status(f"Проверяется страница {len(results) + 1} из {max_pages}: {url}")
                if progress:
                    progress(len(results) / max_pages)
                try:
                    result = _collect_page(page, url, depth, expand_dynamic)
                except Exception as error:
                    result = {
                        "url": url,
                        "depth": depth,
                        "title": "",
                        "description": "",
                        "text": "",
                        "attributes": "",
                        "screenshot": None,
                        "issues": [],
                        "error": str(error),
                        "links": [],
                    }
                results.append(result)
                for link in result.get("links", []):
                    next_depth = depth + 1
                    if next_depth > max_depth or link in queued or len(queued) >= max_pages:
                        continue
                    queued.add(link)
                    queue.append((link, next_depth))
                if progress:
                    progress(len(results) / max_pages)
        finally:
            context.close()
            browser.close()
    if status:
        status(f"Проверка завершена: {len(results)} страниц")
    return results
