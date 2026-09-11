"""Streamlit interface for website language and translation QA."""

from __future__ import annotations

from datetime import datetime
from urllib.parse import urlparse

import pandas as pd
import streamlit as st

from checker import automatic_exceptions, check_page, top_words
from crawler import crawl_site

st.set_page_config(
    page_title="Проверка качества перевода сайтов",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root { color-scheme: dark; }
    .stApp { background: #0c1015; color: #e8edf2; }
    [data-testid="stHeader"] { background: #0c1015; }
    [data-testid="stSidebar"] { background: #121820; border-right: 1px solid #273240; }
    .block-container { max-width: 1400px; padding-top: 1.6rem; padding-bottom: 3rem; }
    h1, h2, h3 { color: #f5f7fa !important; }
    .badge-clean { background: #1b472e; color: #58d68d; padding: 4px 10px; border-radius: 6px; font-weight: 700; }
    .badge-error { background: #4d1c1a; color: #ff8179; padding: 4px 10px; border-radius: 6px; font-weight: 700; }
    </style>
    """,
    unsafe_allow_html=True,
)


def _issue_rows(pages: list[dict]) -> list[dict[str, str]]:
    rows = []
    for page_number, page in enumerate(pages, 1):
        url = page.get("url", "")
        # ЗАЩИТА: Исключаем mailto и служебные протоколы из отчета
        if "mailto:" in url.casefold() or "@" in url:
            continue

        for issue in page.get("issues", []):
            rows.append(
                {
                    "Страница": page_number,
                    "URL": url,
                    "Слово или фраза": issue["word"],
                    "Контекст": issue["context"],
                    "Источник": issue["source"],
                }
            )
    return rows


def _show_page(index: int, page: dict) -> None:
    issues = page.get("issues", [])
    title = page.get("title", "").strip() or "Без заголовка"
    url = page.get("url", "")

    label = f"#{index} {url} — {len(issues)} нарушений" if issues else f"#{index} {url} — чисто"
    with st.expander(label):
        st.caption(f"Title: {title}")
        if page.get("error"):
            st.error(f"Ошибка загрузки: {page['error']}")
            return

        if issues:
            df_page = pd.DataFrame(issues)
            df_page.columns = ["Слово/фраза", "Контекст", "Источник"]
            st.dataframe(df_page, use_container_width=True, hide_index=True)
        else:
            st.markdown("<span class='badge-clean'>Нарушений перевода не найдено</span>", unsafe_allow_html=True)


# --- САЙДБАР ---
with st.sidebar:
    st.title("Параметры проверки")
    start_url = st.text_input("URL сайта", value="https://miele-store.ru/")

    crawl_mode = st.radio(
        "Какие страницы проверять",
        ["🧭 Навигация — путь пользователя", "Все ссылки"],
        index=0,
    )
    max_depth = st.number_input("Глубина обхода", min_value=1, max_value=5, value=3)
    max_pages = st.number_input("Лимит страниц", min_value=10, max_value=300, value=100, step=10)
    product_sample = st.number_input("Карточек товара на раздел", min_value=1, max_value=5, value=2)

    custom_exceptions = st.text_area(
        "Свои слова и модели-исключения",
        value="",
        placeholder="Слова через запятую или с новой строки",
        height=100,
    )

    col1, col2 = st.columns(2)
    start_btn = col1.button("Старт", type="primary", use_container_width=True)
    clear_btn = col2.button("Очистить", use_container_width=True)

    if clear_btn:
        st.session_state.clear()
        st.rerun()

# --- ОСНОВНАЯ ЧАСТЬ ---
st.title("Проверка качества перевода сайтов")

if start_btn and start_url:
    status_box = st.empty()
    progress_bar = st.progress(0)

    try:
        pages = crawl_site(
            start_url=start_url,
            max_depth=max_depth,
            max_pages=max_pages,
            product_sample=product_sample,
            expand_dynamic=True,
            smart_mode=(crawl_mode == "🧭 Навигация — путь пользователя"),
            progress=progress_bar.progress,
            status=status_box.info,
        )

        status_box.info("Анализ контента страниц...")
        auto_whitelist = automatic_exceptions(start_url, pages)

        for p in pages:
            p["issues"] = check_page(p, custom_exceptions, auto_whitelist)

        st.session_state["pages"] = pages
        status_box.success(f"Проверено {len(pages)} страниц.")
    except Exception as e:
        status_box.error(f"Ошибка выполнения: {e}")

if "pages" in st.session_state:
    pages = st.session_state["pages"]
    valid_pages = [p for p in pages if "mailto:" not in p.get("url", "").casefold() and "@" not in p.get("url", "")]

    total_issues = sum(len(p.get("issues", [])) for p in valid_pages)
    pages_with_issues = sum(1 for p in valid_pages if p.get("issues"))

    m1, m2, m3 = st.columns(3)
    m1.metric("Всего страниц", len(valid_pages))
    m2.metric("Страниц с нарушениями", pages_with_issues)
    m3.metric("Всего нарушений", total_issues)

    rows = _issue_rows(valid_pages)
    if rows:
        st.subheader("Сводная таблица нарушений")
        df_export = pd.DataFrame(rows)
        st.dataframe(df_export, use_container_width=True, hide_index=True)

        csv_data = df_export.to_csv(index=False).encode("utf-8-sig")
        timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M")
        domain = urlparse(start_url).hostname or "site"
        st.download_button(
            "📥 Скачать отчет CSV",
            csv_data,
            f"{timestamp}_{domain}_export.csv",
            "text/csv",
            use_container_width=True,
        )

    st.subheader("Список страниц")
    only_problems = st.checkbox("Показывать только страницы с ошибками", value=True)
    filter_word = st.text_input("Поиск по URL или слову", value="")

    for idx, p in enumerate(valid_pages, 1):
        if only_problems and not p.get("issues"):
            continue
        search_blob = p["url"] + " " + " ".join(i["word"] for i in p.get("issues", []))
        if filter_word and filter_word.casefold() not in search_blob.casefold():
            continue
        _show_page(idx, p)
