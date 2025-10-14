"""
Главное приложение Sci.Net.Node
Белый фон для всего приложения + ограничение ширины контейнера
"""

import streamlit as st
from datetime import datetime, date
import pandas as pd

# Импорты компонентов
from components.email_handler import EmailHandler
from components.ris_parser import RISParser
from components.sidebar import SidebarPanel
from components.main_panel import MainPanel
from utils.doi_utils import DOIUtils
from utils.openalex_utils import OpenAlexUtils
from config import APP_CONFIG

# Настройка страницы
st.set_page_config(
    page_title=APP_CONFIG["title"],
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Глобальные стили: белый фон, центрирование контейнера и улучшенная читаемость заголовков
st.markdown(
    """
    <style>
      .stApp {background:#ffffff !important;}
      .block-container {max-width: 1200px; margin: 0 auto;}
      .main h1, .main h2, .main h3, .main h4, .main h5, .main h6 {
        color: #1a1a1a !important;
        font-weight: 600 !important;
      }
      .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        color: #1a1a1a !important;
        font-weight: 600 !important;
      }
      /* Улучшение контраста для всех заголовков */
      div[data-testid="stMarkdownContainer"] h1,
      div[data-testid="stMarkdownContainer"] h2,
      div[data-testid="stMarkdownContainer"] h3,
      div[data-testid="stMarkdownContainer"] h4 {
        color: #1a1a1a !important;
        font-weight: 600 !important;
      }
      /* Общие стили для лучшей читаемости */
      .stApp p, .stApp span, .stApp div {
        color: #333 !important;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# Инициализация сессионного состояния
if "email_handler" not in st.session_state:
    st.session_state.email_handler = EmailHandler()

if "ris_parser" not in st.session_state:
    st.session_state.ris_parser = RISParser()

if "publications" not in st.session_state:
    st.session_state.publications = []

if "connected" not in st.session_state:
    st.session_state.connected = False


def main():
    """Главная функция приложения"""

    st.title("🔬 Sci.Net.Node")
    st.markdown(f"*{APP_CONFIG['description']}*")
    st.markdown("---")

    email_handler = st.session_state.email_handler
    ris_parser = st.session_state.ris_parser

    folders = []
    if st.session_state.connected:
        folders = email_handler.get_folders()

    sidebar = SidebarPanel(st.session_state.publications)

    connection_data = sidebar.render_connection_section()

    if connection_data["connect"] and connection_data["email"] and connection_data["password"]:
        with st.spinner("🔄 Подключение к почтовому серверу..."):
            if email_handler.connect(connection_data["email"], connection_data["password"]):
                st.session_state.connected = True
                st.success("✅ Успешно подключен к почте!")
                st.rerun()
            else:
                st.error("❌ Ошибка подключения к почте")

    if st.session_state.connected:
        folders = email_handler.get_folders()
        st.sidebar.success(f"✅ Подключен: {email_handler.email}")

        if st.sidebar.button("🔌 Отключиться"):
            email_handler.disconnect()
            st.session_state.connected = False
            st.session_state.publications = []
            st.rerun()

        filters = sidebar.render_filters_section(folders)

        if st.sidebar.button("📥 Загрузить письма", type="primary"):
            load_emails(email_handler, ris_parser, filters)

        filtered_publications = apply_filters(st.session_state.publications, filters)

        sidebar.render_analytics_section(filtered_publications)

        main_panel = MainPanel()
        main_panel.render(filtered_publications, email_handler)
    else:
        show_welcome_screen()


def load_emails(email_handler, ris_parser, filters):
    """Загрузка писем с DOI"""
    from datetime import datetime as _dt

    try:
        with st.spinner("📧 Загрузка писем с DOI..."):
            date_from = _dt.combine(filters["date_from"], _dt.min.time()) if filters["date_from"] else None
            date_to = _dt.combine(filters["date_to"], _dt.max.time()) if filters["date_to"] else None

            emails = email_handler.get_emails_with_doi(
                folders=filters["folders"],
                date_from=date_from,
                date_to=date_to,
            )

            if not emails:
                st.warning("📭 Не найдено писем с DOI в выбранных папках и периоде")
                return

            publications = []
            progress_bar = st.progress(0)

            for i, email in enumerate(emails):
                progress_bar.progress((i + 1) / len(emails))

                ris_data = ris_parser.parse_ris_from_text(email.get("text", ""))
                pub_info = ris_parser.extract_publication_info(ris_data)

                pub_info.update(
                    {
                        "folder": email.get("folder", ""),
                        "from": email.get("from", ""),
                        "subject": email.get("subject", ""),
                        "date": email.get("date", ""),
                        "uid": email.get("uid", ""),
                        "text": email.get("text", ""),
                        "html": email.get("html", ""),
                        "DO": email.get("doi"),
                    }
                )

                if not pub_info.get("title") and email.get("subject"):
                    pub_info["title"] = email["subject"]

                if not pub_info.get("doi") and email.get("doi"):
                    pub_info["doi"] = email["doi"]

                publications.append(pub_info)

            st.session_state.publications = publications
            progress_bar.empty()
            st.success(f"✅ Загружено {len(publications)} писем с DOI")

    except Exception as e:
        st.error(f"❌ Ошибка загрузки писем: {e}")


def apply_filters(publications, filters):
    if not publications:
        return []

    filtered = publications.copy()

    if filters["types"]:
        filtered = [p for p in filtered if p.get("type", "") in filters["types"]]

    if filters["years"]:
        filtered = [p for p in filtered if str(p.get("year", "")) in [str(y) for y in filters["years"]]]

    if filters["author_search"]:
        term = filters["author_search"].lower()
        filtered = [p for p in filtered if any(term in str(a).lower() for a in p.get("authors", []))]

    if filters["title_search"]:
        term = filters["title_search"].lower()
        filtered = [p for p in filtered if term in str(p.get("title", "")).lower()]

    if filters["keywords_search"]:
        term = filters["keywords_search"].lower()
        filtered = [p for p in filtered if any(term in str(k).lower() for k in p.get("keywords", []))]

    return filtered


def show_welcome_screen():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(
            """
            <div style="text-align:center; padding: 50px;">
              <h2>🔬 Добро пожаловать в Sci.Net.Node!</h2>
              <p style="font-size: 18px;">Система управления научными публикациями через электронную почту</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            ### 🚀 Как начать работу:
            1. **🔐 Подключитесь к почте** — введите данные Mail.ru в боковой панели и нажмите «Подключиться»
            2. **📧 Загрузите письма** — выберите папки/период и нажмите «Загрузить письма»
            3. **🔍 Используйте фильтры** — по типу, авторам, ключевым словам
            4. **📊 Аналитика** — диаграммы, экспорт RIS/CSV
            """
        )


if __name__ == "__main__":
    main()
