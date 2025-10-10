"""
Основная панель с карточками публикаций для Sci.Net.Node
"""

import streamlit as st
from typing import List, Dict, Any
import pandas as pd
from datetime import datetime
from config import REQUEST_PATTERNS, SCINET_CORE_EMAIL
import urllib.parse

class MainPanel:
    """Класс для основной панели с отображением карточек публикаций"""

    def __init__(self):
        pass

    def render(self, publications: List[Dict[str, Any]], email_handler=None):
        """Отображение основной панели"""

        if not publications:
            st.info("📭 Нет писем с DOI для отображения")
            st.markdown("""
            ### Как начать работу:
            1. 🔐 Подключитесь к вашему почтовому ящику в боковой панели
            2. 📧 Убедитесь, что в ваших письмах содержатся DOI публикаций
            3. 🔍 Используйте фильтры для поиска нужных публикаций
            4. 📊 Анализируйте данные с помощью диаграмм
            """)
            return

        # Заголовок с количеством публикаций
        st.header(f"📚 Найдено публикаций: {len(publications)}")

        # Группируем публикации по уникальным DOI
        unique_publications = self._group_by_doi(publications)

        # Отображаем карточки
        for doi, pub_group in unique_publications.items():
            self._render_publication_card(pub_group, email_handler)

    def _group_by_doi(self, publications: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Группировка публикаций по уникальным DOI"""
        grouped = {}

        for pub in publications:
            doi = pub.get('doi', '')
            if doi:
                if doi not in grouped:
                    grouped[doi] = []
                grouped[doi].append(pub)

        return grouped

    def _render_publication_card(self, pub_group: List[Dict[str, Any]], email_handler=None):
        """Отображение карточки одной публикации"""

        # Берем данные из первой публикации группы (основная информация)
        main_pub = pub_group[0]

        # Объединяем данные из всех писем группы
        merged_data = self._merge_publication_data(pub_group)

        # Создаем контейнер для карточки
        with st.container():
            # Создаем карточку с рамкой
            st.markdown("""
                <div style="border: 1px solid #ddd; border-radius: 10px; padding: 15px; margin: 10px 0; background-color: #f9f9f9;">
            """, unsafe_allow_html=True)

            # Заголовок публикации
            title = merged_data.get('title', 'Без названия')
            doi = merged_data.get('doi', '')

            col1, col2 = st.columns([4, 1])

            with col1:
                st.markdown(f"### 📄 {title}")
                st.markdown(f"**DOI:** [{doi}](https://doi.org/{doi})")

            with col2:
                # Кнопка для разворачивания деталей
                expanded = st.checkbox("Детали", key=f"details_{doi}")

            # Основная информация в двух колонках
            col1, col2 = st.columns(2)

            with col1:
                # Тип публикации
                pub_type = merged_data.get('type', 'Не указан')
                st.markdown(f"**Тип (M3/TY):** {pub_type}")

                # Год публикации  
                year = merged_data.get('year', 'Не указан')
                st.markdown(f"**Год (PY):** {year}")

                # Журнал
                journal = merged_data.get('journal', 'Не указан')
                if journal:
                    st.markdown(f"**Журнал (T2):** {journal}")

            with col2:
                # Авторы
                authors = merged_data.get('authors', [])
                if authors:
                    first_author = authors[0]
                    last_author = authors[-1] if len(authors) > 1 else ''

                    st.markdown(f"**Первый автор:** {first_author}")
                    if last_author and last_author != first_author:
                        st.markdown(f"**Последний автор:** {last_author}")

                    if len(authors) > 2:
                        st.markdown(f"*и еще {len(authors)-1} авторов*")

            # Развернутая информация
            if expanded:
                st.markdown("---")
                self._render_expanded_details(merged_data, pub_group, email_handler)

            st.markdown("</div>", unsafe_allow_html=True)

    def _merge_publication_data(self, pub_group: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Объединение данных публикации из всех писем группы"""

        merged = {
            'doi': '',
            'title': '',
            'type': '',
            'year': '',
            'authors': [],
            'journal': '',
            'keywords': [],
            'abstract': '',
            'notes': '',
            'urls': [],
            'emails': []
        }

        # Собираем данные из всех писем
        all_authors = set()
        all_keywords = set()

        for pub in pub_group:
            # Основные поля - берем первое непустое значение
            for field in ['doi', 'title', 'type', 'year', 'journal', 'abstract']:
                if not merged[field] and pub.get(field):
                    merged[field] = pub[field]

            # Авторы - объединяем
            pub_authors = pub.get('authors', [])
            if isinstance(pub_authors, list):
                all_authors.update(pub_authors)
            elif pub_authors:
                all_authors.add(pub_authors)

            # Ключевые слова - объединяем
            pub_keywords = pub.get('keywords', [])
            if isinstance(pub_keywords, list):
                all_keywords.update(pub_keywords)
            elif pub_keywords:
                all_keywords.add(pub_keywords)

            # Заметки - объединяем
            if pub.get('notes'):
                if merged['notes']:
                    merged['notes'] += f"; {pub['notes']}"
                else:
                    merged['notes'] = pub['notes']

            # URL и информация о письмах
            merged['emails'].append({
                'folder': pub.get('folder', ''),
                'from': pub.get('from', ''),
                'subject': pub.get('subject', ''),
                'date': pub.get('date', ''),
                'uid': pub.get('uid', '')
            })

        merged['authors'] = list(all_authors)
        merged['keywords'] = list(all_keywords)

        return merged

    def _render_expanded_details(self, merged_data: Dict[str, Any], 
                                pub_group: List[Dict[str, Any]], 
                                email_handler=None):
        """Отображение развернутых деталей публикации"""

        # Создаем табы для разной информации
        tab1, tab2, tab3, tab4 = st.tabs(["📋 Данные", "📧 Письма", "🔗 Действия", "📊 Статистика"])

        with tab1:
            self._render_publication_data_tab(merged_data)

        with tab2:
            self._render_emails_tab(merged_data['emails'])

        with tab3:
            self._render_actions_tab(merged_data, email_handler)

        with tab4:
            self._render_stats_tab(pub_group)

    def _render_publication_data_tab(self, merged_data: Dict[str, Any]):
        """Таб с данными публикации"""

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📝 Основные данные")

            # Все авторы
            authors = merged_data.get('authors', [])
            if authors:
                st.markdown("**Авторы (AU):**")
                for author in authors[:10]:  # Показываем первых 10
                    st.markdown(f"- {author}")
                if len(authors) > 10:
                    st.markdown(f"*...и еще {len(authors)-10} авторов*")

            # Дополнительная информация
            volume = merged_data.get('volume', '')
            issue = merged_data.get('issue', '') 
            pages = merged_data.get('pages', '')

            if volume:
                st.markdown(f"**Том (VL):** {volume}")
            if issue:
                st.markdown(f"**Выпуск (IS):** {issue}")
            if pages:
                st.markdown(f"**Страницы (SP):** {pages}")

        with col2:
            st.subheader("🏷️ Метаданные")

            # Ключевые слова
            keywords = merged_data.get('keywords', [])
            if keywords:
                st.markdown("**Ключевые слова (KW/DE):**")
                for keyword in keywords[:15]:  # Показываем первые 15
                    st.markdown(f"- {keyword}")
                if len(keywords) > 15:
                    st.markdown(f"*...и еще {len(keywords)-15} ключевых слов*")

            # Абстракт
            abstract = merged_data.get('abstract', '')
            if abstract:
                st.markdown("**Абстракт (AB):**")
                st.markdown(abstract[:500] + ("..." if len(abstract) > 500 else ""))

            # Заметки
            notes = merged_data.get('notes', '')
            if notes:
                st.markdown("**Заметки (N2/PA):**")
                st.markdown(notes)

    def _render_emails_tab(self, emails: List[Dict[str, Any]]):
        """Таб со списком писем"""

        st.subheader(f"📧 Письма ({len(emails)})")

        # Создаем таблицу писем
        emails_data = []
        for email in emails:
            emails_data.append({
                'Папка': email.get('folder', ''),
                'От кого': email.get('from', ''),
                'Тема': email.get('subject', '')[:50] + ("..." if len(email.get('subject', '')) > 50 else ''),
                'Дата': email.get('date', '').strftime('%Y-%m-%d %H:%M') if isinstance(email.get('date'), datetime) else str(email.get('date', ''))
            })

        df = pd.DataFrame(emails_data)
        st.dataframe(df, use_container_width=True)

    def _render_actions_tab(self, merged_data: Dict[str, Any], email_handler=None):
        """Таб с действиями"""

        st.subheader("🔗 Доступные действия")

        doi = merged_data.get('doi', '')
        title = merged_data.get('title', '')

        if not doi:
            st.warning("DOI не найден для выполнения действий")
            return

        # Кнопки запросов в Sci.Net.Core
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("**📄 Получить данные:**")

            if st.button(f"📋 Тип работы", key=f"m3_{doi}"):
                self._create_request_link("M3_REQUEST", doi, title, email_handler)

            if st.button(f"📚 PDF файл", key=f"pdf_{doi}"):
                self._create_request_link("PDF_REQUEST", doi, title, email_handler)

            if st.button(f"🔬 PubMed", key=f"pmid_{doi}"):
                self._create_request_link("PMID_REQUEST", doi, title, email_handler)

        with col2:
            st.markdown("**🏷️ Получить метаданные:**")

            if st.button(f"🎯 Ключевые слова", key=f"kw_{doi}"):
                self._create_request_link("KW_REQUEST", doi, title, email_handler)

            if st.button(f"📖 Цитирования", key=f"cits_{doi}"):
                self._create_request_link("CITS_REQUEST", doi, title, email_handler)

        with col3:
            st.markdown("**✏️ Добавить данные:**")

            if st.button(f"📝 Добавить абстракт", key=f"abs_{doi}"):
                self._create_insert_link("INSERT_ABSTRACT", title)

            if st.button(f"🏷️ Добавить ключевые слова", key=f"keys_{doi}"):
                self._create_insert_link("INSERT_KEYWORDS", title)

            if st.button(f"📋 Добавить заметки", key=f"notes_{doi}"):
                self._create_insert_link("INSERT_NOTES", title)

        # Прямые ссылки
        st.markdown("**🌐 Внешние ссылки:**")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"[🔗 DOI.org](https://doi.org/{doi})")
        with col2:
            st.markdown(f"[🎓 Google Scholar](https://scholar.google.com/scholar?q={urllib.parse.quote(title)})")
        with col3:
            st.markdown(f"[📚 PubMed](https://pubmed.ncbi.nlm.nih.gov/?term={urllib.parse.quote(title)})")

    def _render_stats_tab(self, pub_group: List[Dict[str, Any]]):
        """Таб со статистикой"""

        st.subheader("📊 Статистика по письмам")

        # Статистика по папкам
        folders = [pub.get('folder', '') for pub in pub_group]
        folder_counts = pd.Series(folders).value_counts()

        st.markdown("**Распределение по папкам:**")
        for folder, count in folder_counts.items():
            st.markdown(f"- {folder}: {count} писем")

        # Статистика по отправителям
        senders = [pub.get('from', '') for pub in pub_group]
        sender_counts = pd.Series(senders).value_counts()

        st.markdown("**Основные корреспонденты:**")
        for sender, count in sender_counts.head(5).items():
            st.markdown(f"- {sender}: {count} писем")

        # Временная статистика
        dates = [pub.get('date') for pub in pub_group if pub.get('date')]
        if dates:
            min_date = min(dates)
            max_date = max(dates)
            st.markdown(f"**Период переписки:** {min_date.strftime('%Y-%m-%d')} - {max_date.strftime('%Y-%m-%d')}")

    def _create_request_link(self, request_type: str, doi: str, title: str, email_handler=None):
        """Создание ссылки запроса"""

        pattern = REQUEST_PATTERNS.get(request_type, "[request]")
        body = f"{pattern} https://doi.org/{doi}"

        mailto_link = f"mailto:{SCINET_CORE_EMAIL}?subject={urllib.parse.quote(title)}&body={urllib.parse.quote(body)}"

        st.success(f"🔗 Ссылка для запроса создана:")
        st.markdown(f"[📧 Открыть в почтовом клиенте]({mailto_link})")

        # Если доступен email_handler, можем отправить напрямую
        if email_handler and email_handler.connected:
            if st.button("📤 Отправить запрос", key=f"send_{request_type}_{doi}"):
                if email_handler.send_request_email(title, body):
                    st.success("✅ Запрос отправлен!")
                else:
                    st.error("❌ Ошибка отправки запроса")

    def _create_insert_link(self, insert_type: str, title: str):
        """Создание ссылки для вставки данных"""

        body_templates = {
            "INSERT_ABSTRACT": "PDF could be attached to this mail\n\nAB - [вставьте абстракт здесь]\n\nBest regards,",
            "INSERT_KEYWORDS": "DE - [вставьте ключевые слова через запятую]\n\nBest regards,", 
            "INSERT_NOTES": "PA - [вставьте ваши заметки здесь]\n\nBest regards,"
        }

        body = body_templates.get(insert_type, "Best regards,")

        mailto_link = f"mailto:{SCINET_CORE_EMAIL}?subject={urllib.parse.quote(title)}&body={urllib.parse.quote(body)}"

        st.success(f"🔗 Шаблон для добавления данных:")
        st.markdown(f"[📧 Открыть в почтовом клиенте]({mailto_link})")
