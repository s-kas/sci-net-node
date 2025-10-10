"""
Главное приложение Sci.Net.Node
Научная сеть для управления публикациями через электронную почту
"""

import streamlit as st
import os
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
    initial_sidebar_state="expanded"
)

# Кастомные стили
st.markdown("""
<style>
    .stApp {
        max-width: 1200px;
        margin: 0 auto;
    }
    .publication-card {
        border: 1px solid #ddd;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        background-color: #f9f9f9;
    }
    .metric-container {
        background-color: #e6f3ff;
        padding: 10px;
        border-radius: 5px;
        margin: 5px 0;
    }
</style>
""", unsafe_allow_html=True)

# Инициализация сессионного состояния
if 'email_handler' not in st.session_state:
    st.session_state.email_handler = EmailHandler()

if 'ris_parser' not in st.session_state:
    st.session_state.ris_parser = RISParser()

if 'publications' not in st.session_state:
    st.session_state.publications = []

if 'connected' not in st.session_state:
    st.session_state.connected = False

def main():
    """Главная функция приложения"""

    # Заголовок приложения
    st.title("🔬 Sci.Net.Node")
    st.markdown(f"*{APP_CONFIG['description']}*")
    st.markdown("---")

    # Инициализация компонентов
    email_handler = st.session_state.email_handler
    ris_parser = st.session_state.ris_parser

    # Получаем список папок если подключены
    folders = []
    if st.session_state.connected:
        folders = email_handler.get_folders()

    # Создаем боковую панель
    sidebar = SidebarPanel(st.session_state.publications)

    # Секция подключения к почте
    connection_data = sidebar.render_connection_section()

    # Обработка подключения
    if connection_data['connect'] and connection_data['email'] and connection_data['password']:
        with st.spinner("🔄 Подключение к почтовому серверу..."):
            if email_handler.connect(connection_data['email'], connection_data['password']):
                st.session_state.connected = True
                st.success("✅ Успешно подключен к почте!")
                st.rerun()
            else:
                st.error("❌ Ошибка подключения к почте")

    # Если подключены, показываем фильтры и загружаем данные  
    if st.session_state.connected:

        # Обновляем список папок
        folders = email_handler.get_folders()

        # Показываем статус подключения
        st.sidebar.success(f"✅ Подключен: {email_handler.email}")

        if st.sidebar.button("🔌 Отключиться"):
            email_handler.disconnect()
            st.session_state.connected = False
            st.session_state.publications = []
            st.rerun()

        # Секция фильтров
        filters = sidebar.render_filters_section(folders)

        # Кнопка загрузки писем
        if st.sidebar.button("📥 Загрузить письма", type="primary"):
            load_emails(email_handler, ris_parser, filters)

        # Применяем фильтры к уже загруженным данным
        filtered_publications = apply_filters(st.session_state.publications, filters)

        # Секция аналитики
        sidebar.render_analytics_section(filtered_publications)

        # Основная панель
        main_panel = MainPanel()
        main_panel.render(filtered_publications, email_handler)

    else:
        # Показываем инструкции для неподключенных пользователей
        show_welcome_screen()

def load_emails(email_handler, ris_parser, filters):
    """Загрузка писем с DOI"""

    try:
        with st.spinner("📧 Загрузка писем с DOI..."):

            # Преобразуем даты
            date_from = datetime.combine(filters['date_from'], datetime.min.time()) if filters['date_from'] else None
            date_to = datetime.combine(filters['date_to'], datetime.max.time()) if filters['date_to'] else None

            # Получаем письма
            emails = email_handler.get_emails_with_doi(
                folders=filters['folders'],
                date_from=date_from,
                date_to=date_to
            )

            if not emails:
                st.warning("📭 Не найдено писем с DOI в выбранных папках и периоде")
                return

            # Обрабатываем каждое письмо
            publications = []
            progress_bar = st.progress(0)

            for i, email in enumerate(emails):
                # Обновляем прогресс
                progress_bar.progress((i + 1) / len(emails))

                # Парсим RIS данные из письма
                ris_data = ris_parser.parse_ris_from_text(email.get('text', ''))

                # Извлекаем информацию о публикации
                pub_info = ris_parser.extract_publication_info(ris_data)

                # Добавляем данные письма
                pub_info.update({
                    'folder': email.get('folder', ''),
                    'from': email.get('from', ''),
                    'subject': email.get('subject', ''),
                    'date': email.get('date', ''),
                    'uid': email.get('uid', ''),
                    'text': email.get('text', ''),
                    'html': email.get('html', '')
                })

                # Если нет заголовка, используем тему письма
                if not pub_info.get('title') and email.get('subject'):
                    pub_info['title'] = email['subject']

                # Если нет DOI из RIS, используем DOI из письма
                if not pub_info.get('doi') and email.get('doi'):
                    pub_info['doi'] = email['doi']

                publications.append(pub_info)

            # Сохраняем в сессию
            st.session_state.publications = publications

            progress_bar.empty()
            st.success(f"✅ Загружено {len(publications)} писем с DOI")

    except Exception as e:
        st.error(f"❌ Ошибка загрузки писем: {e}")

def apply_filters(publications, filters):
    """Применение фильтров к публикациям"""

    if not publications:
        return []

    filtered = publications.copy()

    # Фильтр по типу публикации
    if filters['types']:
        filtered = [p for p in filtered if p.get('type', '') in filters['types']]

    # Фильтр по году
    if filters['years']:
        filtered = [p for p in filtered if str(p.get('year', '')) in [str(y) for y in filters['years']]]

    # Фильтр по автору
    if filters['author_search']:
        search_term = filters['author_search'].lower()
        filtered = [p for p in filtered 
                   if any(search_term in str(author).lower() 
                         for author in p.get('authors', []))]

    # Фильтр по заголовку
    if filters['title_search']:
        search_term = filters['title_search'].lower()
        filtered = [p for p in filtered 
                   if search_term in str(p.get('title', '')).lower()]

    # Фильтр по ключевым словам
    if filters['keywords_search']:
        search_term = filters['keywords_search'].lower()
        filtered = [p for p in filtered 
                   if any(search_term in str(kw).lower() 
                         for kw in p.get('keywords', []))]

    return filtered

def show_welcome_screen():
    """Экран приветствия для неподключенных пользователей"""

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("""
        <div style="text-align: center; padding: 50px;">
        <h2>🔬 Добро пожаловать в Sci.Net.Node!</h2>
        <p style="font-size: 18px;">Система управления научными публикациями через электронную почту</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        ### 🚀 Как начать работу:

        1. **🔐 Подключитесь к почте**
           - Введите данные вашего ящика Mail.ru в боковой панели
           - Нажмите кнопку "Подключиться"

        2. **📧 Загрузите письма**
           - Выберите папки для поиска
           - Установите период поиска
           - Нажмите "Загрузить письма"

        3. **🔍 Используйте фильтры**
           - Фильтруйте по типу публикации
           - Ищите по авторам и ключевым словам
           - Анализируйте временные тренды

        4. **📊 Анализируйте данные**
           - Стройте диаграммы частот
           - Исследуйте концепты через OpenAlex
           - Экспортируйте результаты в RIS/CSV

        5. **🔗 Взаимодействуйте с Sci.Net.Core**
           - Запрашивайте дополнительную информацию
           - Добавляйте свои заметки и данные
           - Синхронизируйтесь через email
        """)

        st.markdown("---")

        st.info("""
        💡 **Подсказка:** Убедитесь, что ваши письма содержат DOI публикаций. 
        Система автоматически найдет и обработает все письма с научными публикациями.
        """)

if __name__ == "__main__":
    main()
