"""
Основная панель с карточками публикаций для Sci.Net.Node
Отображает уникальные публикации по DOI в виде ленты карточек
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

        # Группируем публикации по уникальным DOI
        unique_publications = self._group_by_unique_doi(publications)

        # Заголовок с количеством уникальных публикаций
        st.header(f"📚 Найдено публикаций: {len(unique_publications)}")
        
        if len(publications) > len(unique_publications):
            st.info(f"ℹ️ Показаны уникальные публикации по DOI. Всего писем с публикациями: {len(publications)}")

        # Отображаем карточки в виде ленты
        for doi, pub_data in unique_publications.items():
            self._render_publication_card(pub_data, email_handler)

    def _group_by_unique_doi(self, publications: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Группировка публикаций по уникальным DOI с агрегацией данных"""
        
        grouped = {}

        for pub in publications:
            doi = self._extract_clean_doi(pub)
            
            if not doi:
                continue
                
            if doi not in grouped:
                # Создаем новую запись для уникального DOI
                grouped[doi] = {
                    'doi': doi,
                    'title': '',
                    'type': '',
                    'year': '',
                    'journal': '',
                    'first_author': '',
                    'last_author': '',
                    'authors': set(),
                    'keywords': set(),
                    'abstract': '',
                    'notes': [],
                    'volume': '',
                    'issue': '',
                    'pages': '',
                    'emails': []
                }
            
            # Агрегируем данные из текущего письма
            current_data = grouped[doi]
            
            # Основные поля - берем первое непустое значение (кроме полей в квадратных скобках)
            for field in ['title', 'journal', 'volume', 'issue', 'pages', 'abstract']:
                field_value = pub.get(field, '')
                if field_value and not current_data[field]:
                    # Проверяем, не является ли значение текстом в квадратных скобках
                    if not (isinstance(field_value, str) and field_value.strip().startswith('[') and field_value.strip().endswith(']')):
                        current_data[field] = field_value
            
            # Тип публикации - исключаем mailto ссылки и значения в квадратных скобках
            pub_type = pub.get('type', '')
            if pub_type and not current_data['type']:
                if not (pub_type.startswith('href=') or pub_type.startswith('mailto:') or 
                       (pub_type.strip().startswith('[') and pub_type.strip().endswith(']'))):
                    current_data['type'] = pub_type
            
            # Год - берем валидный числовой год
            pub_year = pub.get('year', '')
            if pub_year and not current_data['year']:
                if str(pub_year).isdigit() and 1900 <= int(pub_year) <= 2030:
                    current_data['year'] = pub_year
            
            # Авторы - агрегируем всех уникальных авторов
            pub_authors = pub.get('authors', [])
            if isinstance(pub_authors, list):
                current_data['authors'].update(pub_authors)
            elif pub_authors:
                current_data['authors'].add(pub_authors)
            
            # Первый и последний автор
            if pub_authors and not current_data['first_author']:
                if isinstance(pub_authors, list) and pub_authors:
                    current_data['first_author'] = pub_authors[0]
                elif isinstance(pub_authors, str):
                    current_data['first_author'] = pub_authors
                    
            if pub_authors and isinstance(pub_authors, list) and len(pub_authors) > 1:
                current_data['last_author'] = pub_authors[-1]
            
            # Ключевые слова - агрегируем
            pub_keywords = pub.get('keywords', [])
            if isinstance(pub_keywords, list):
                current_data['keywords'].update(pub_keywords)
            elif pub_keywords:
                current_data['keywords'].add(pub_keywords)
            
            # Заметки - собираем все
            pub_notes = pub.get('notes', '')
            if pub_notes and pub_notes not in current_data['notes']:
                current_data['notes'].append(pub_notes)
            
            # Информация о письме
            email_info = {
                'folder': pub.get('folder', ''),
                'from': pub.get('from', ''),
                'subject': pub.get('subject', ''),
                'date': pub.get('date', ''),
                'uid': pub.get('uid', ''),
                'text': pub.get('text', ''),
                'html': pub.get('html', '')
            }
            current_data['emails'].append(email_info)
        
        # Преобразуем sets в lists для удобства отображения
        for doi_data in grouped.values():
            doi_data['authors'] = sorted(list(doi_data['authors']))
            doi_data['keywords'] = sorted(list(doi_data['keywords']))
            
        return grouped
    
    def _extract_clean_doi(self, pub: Dict[str, Any]) -> str:
        """Извлечение и очистка DOI"""
        doi = pub.get('doi', '')
        if not doi:
            return ''
            
        # Очищаем DOI от префиксов и лишних символов
        doi = str(doi).strip()
        doi = doi.replace('https://doi.org/', '')
        doi = doi.replace('http://doi.org/', '')
        doi = doi.replace('doi.org/', '')
        doi = doi.replace('DOI:', '')
        doi = doi.replace('doi:', '')
        
        return doi.strip()

    def _render_publication_card(self, pub_data: Dict[str, Any], email_handler=None):
        """Отображение карточки одной публикации"""

        doi = pub_data['doi']
        
        # Создаем контейнер-карточку с улучшенным стилем
        with st.container():
            st.markdown(f"""
                <div style="
                    border: 2px solid #e0e0e0;
                    border-radius: 12px;
                    padding: 20px;
                    margin: 15px 0;
                    background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    transition: all 0.3s ease;
                ">
            """, unsafe_allow_html=True)

            # Заголовок карточки
            title = pub_data.get('title', 'Без названия')
            
            col1, col2 = st.columns([5, 1])
            
            with col1:
                st.markdown(f"### 📄 {title}")
                st.markdown(f"**DOI:** `{doi}` [🔗](https://doi.org/{doi})")
            
            with col2:
                # Кнопка деталей
                expanded = st.toggle("Детали", key=f"details_{doi}")

            # Основная информация в карточке
            col1, col2, col3 = st.columns([2, 2, 2])

            with col1:
                # Тип публикации
                pub_type = pub_data.get('type', 'Не указан')
                st.markdown(f"**Тип (M3/TY):** {pub_type}")
                
                # Год публикации  
                year = pub_data.get('year', 'Не указан')
                st.markdown(f"**Год (PY):** {year}")

            with col2:
                # Журнал
                journal = pub_data.get('journal', 'Не указан')
                st.markdown(f"**Журнал (T2):** {journal}")
                
                # Количество писем
                email_count = len(pub_data.get('emails', []))
                st.markdown(f"**📧 Писем:** {email_count}")

            with col3:
                # Авторы
                first_author = pub_data.get('first_author', '')
                last_author = pub_data.get('last_author', '')
                authors_count = len(pub_data.get('authors', []))
                
                if first_author:
                    st.markdown(f"**Первый автор:** {first_author}")
                    
                if last_author and last_author != first_author:
                    st.markdown(f"**Последний автор:** {last_author}")
                elif authors_count > 1:
                    st.markdown(f"**Авторов:** {authors_count}")

            # Развернутая информация
            if expanded:
                st.markdown("---")
                self._render_expanded_details(pub_data, email_handler)

            st.markdown("</div>", unsafe_allow_html=True)

    def _render_expanded_details(self, pub_data: Dict[str, Any], email_handler=None):
        """Отображение развернутых деталей публикации"""

        # Создаем табы для разной информации
        tab1, tab2, tab3, tab4 = st.tabs(["📋 Данные", "📧 Письма", "🔗 Действия", "📊 Статистика"])

        with tab1:
            self._render_publication_data_tab(pub_data)

        with tab2:
            self._render_emails_tab(pub_data.get('emails', []))

        with tab3:
            self._render_actions_tab(pub_data, email_handler)

        with tab4:
            self._render_stats_tab(pub_data)

    def _render_publication_data_tab(self, pub_data: Dict[str, Any]):
        """Таб с данными публикации"""

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📝 Основные данные")

            # Все авторы
            authors = pub_data.get('authors', [])
            if authors:
                st.markdown("**Авторы (AU):**")
                for i, author in enumerate(authors[:10]):
                    st.markdown(f"{i+1}. {author}")
                if len(authors) > 10:
                    st.markdown(f"*...и еще {len(authors)-10} авторов*")

            # Библиографическая информация
            volume = pub_data.get('volume', '')
            issue = pub_data.get('issue', '') 
            pages = pub_data.get('pages', '')

            if volume:
                st.markdown(f"**Том (VL):** {volume}")
            if issue:
                st.markdown(f"**Выпуск (IS):** {issue}")
            if pages:
                st.markdown(f"**Страницы (SP):** {pages}")

        with col2:
            st.subheader("🏷️ Метаданные")

            # Ключевые слова
            keywords = pub_data.get('keywords', [])
            if keywords:
                st.markdown("**Ключевые слова (KW/DE):**")
                
                # Отображаем ключевые слова в виде тегов
                keywords_text = ", ".join(keywords[:15])
                st.markdown(f"_{keywords_text}_")
                
                if len(keywords) > 15:
                    st.markdown(f"*...и еще {len(keywords)-15} ключевых слов*")

            # Абстракт
            abstract = pub_data.get('abstract', '')
            if abstract:
                st.markdown("**Абстракт (AB):**")
                with st.expander("Показать абстракт"):
                    st.markdown(abstract)

            # Заметки
            notes = pub_data.get('notes', [])
            if notes:
                st.markdown("**Заметки (N2/PA):**")
                for i, note in enumerate(notes, 1):
                    st.markdown(f"{i}. {note}")

    def _render_emails_tab(self, emails: List[Dict[str, Any]]):
        """Таб со списком писем"""

        st.subheader(f"📧 Письма с этой публикацией ({len(emails)})")
        
        if not emails:
            st.info("Нет писем для отображения")
            return

        # Создаем детальную таблицу писем
        for i, email in enumerate(emails, 1):
            with st.expander(f"Письмо {i}: {email.get('subject', 'Без темы')[:60]}..."):
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"**📁 Папка:** {email.get('folder', 'Не указана')}")
                    st.markdown(f"**👤 От кого:** {email.get('from', 'Не указан')}")
                    st.markdown(f"**📅 Дата:** {self._format_date(email.get('date', ''))}")
                
                with col2:
                    st.markdown(f"**📋 Тема:** {email.get('subject', 'Без темы')}")
                    st.markdown(f"**🆔 UID:** {email.get('uid', 'Не указан')}")
                
                # Предварительный просмотр содержимого
                email_text = email.get('text', '')
                if email_text:
                    preview_text = email_text[:300] + ("..." if len(email_text) > 300 else "")
                    st.markdown("**📄 Содержимое (предварительный просмотр):**")
                    st.markdown(f"```\n{preview_text}\n```")

    def _render_actions_tab(self, pub_data: Dict[str, Any], email_handler=None):
        """Таб с действиями"""

        st.subheader("🔗 Доступные действия")

        doi = pub_data.get('doi', '')
        title = pub_data.get('title', '')

        if not doi:
            st.warning("DOI не найден для выполнения действий")
            return

        # Кнопки запросов в Sci.Net.Core
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("**📄 Получить данные:**")

            if st.button(f"📋 Тип работы", key=f"m3_{doi}", help="Запросить тип публикации (M3)"):
                self._create_request_link("M3_REQUEST", doi, title, email_handler)

            if st.button(f"📚 PDF файл", key=f"pdf_{doi}", help="Запросить PDF файл"):
                self._create_request_link("PDF_REQUEST", doi, title, email_handler)

            if st.button(f"🔬 PubMed ID", key=f"pmid_{doi}", help="Запросить PMID"):
                self._create_request_link("PMID_REQUEST", doi, title, email_handler)

        with col2:
            st.markdown("**🏷️ Получить метаданные:**")

            if st.button(f"🎯 Ключевые слова", key=f"kw_{doi}", help="Запросить ключевые слова"):
                self._create_request_link("KW_REQUEST", doi, title, email_handler)

            if st.button(f"📖 Цитирования", key=f"cits_{doi}", help="Запросить цитирования"):
                self._create_request_link("CITS_REQUEST", doi, title, email_handler)

        with col3:
            st.markdown("**✏️ Добавить данные:**")

            if st.button(f"📝 Добавить абстракт", key=f"abs_{doi}", help="Отправить абстракт"):
                self._create_insert_link("INSERT_ABSTRACT", title)

            if st.button(f"🏷️ Добавить ключевые слова", key=f"keys_{doi}", help="Отправить ключевые слова"):
                self._create_insert_link("INSERT_KEYWORDS", title)

            if st.button(f"📋 Добавить заметки", key=f"notes_{doi}", help="Отправить заметки"):
                self._create_insert_link("INSERT_NOTES", title)

        # Прямые ссылки
        st.markdown("---")
        st.markdown("**🌐 Внешние ссылки:**")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"[🔗 DOI.org](https://doi.org/{doi})")
        with col2:
            st.markdown(f"[🎓 Google Scholar](https://scholar.google.com/scholar?q={urllib.parse.quote(title)})")
        with col3:
            st.markdown(f"[📚 PubMed](https://pubmed.ncbi.nlm.nih.gov/?term={urllib.parse.quote(title)})")
        with col4:
            st.markdown(f"[🔍 Crossref](https://search.crossref.org/?q={urllib.parse.quote(title)})")

    def _render_stats_tab(self, pub_data: Dict[str, Any]):
        """Таб со статистикой"""

        st.subheader("📊 Статистика по письмам")
        
        emails = pub_data.get('emails', [])
        
        if not emails:
            st.info("Нет писем для анализа")
            return

        # Статистика по папкам
        folders = [email.get('folder', 'Неизвестно') for email in emails]
        folder_counts = pd.Series(folders).value_counts()

        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**📁 Распределение по папкам:**")
            for folder, count in folder_counts.items():
                percentage = (count / len(emails)) * 100
                st.markdown(f"- {folder}: {count} писем ({percentage:.1f}%)")

        # Статистика по отправителям
        senders = [email.get('from', 'Неизвестно') for email in emails]
        sender_counts = pd.Series(senders).value_counts()

        with col2:
            st.markdown("**👤 Основные корреспонденты:**")
            for sender, count in sender_counts.head(5).items():
                percentage = (count / len(emails)) * 100
                sender_short = sender[:30] + "..." if len(sender) > 30 else sender
                st.markdown(f"- {sender_short}: {count} писем ({percentage:.1f}%)")

        # Временная статистика
        dates = [email.get('date') for email in emails if email.get('date')]
        if dates:
            dates_formatted = [self._parse_date(date) for date in dates]
            dates_formatted = [d for d in dates_formatted if d]  # Убираем None
            
            if dates_formatted:
                min_date = min(dates_formatted)
                max_date = max(dates_formatted)
                
                st.markdown("---")
                st.markdown("**📅 Временные рамки:**")
                st.markdown(f"- Первое письмо: {min_date.strftime('%Y-%m-%d %H:%M')}")
                st.markdown(f"- Последнее письмо: {max_date.strftime('%Y-%m-%d %H:%M')}")
                
                time_span = (max_date - min_date).days
                if time_span > 0:
                    st.markdown(f"- Период переписки: {time_span} дней")

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
        
    def _format_date(self, date_obj):
        """Форматирование даты для отображения"""
        if isinstance(date_obj, datetime):
            return date_obj.strftime('%Y-%m-%d %H:%M')
        elif isinstance(date_obj, str):
            return date_obj
        else:
            return str(date_obj) if date_obj else 'Не указана'
            
    def _parse_date(self, date_obj):
        """Парсинг даты в datetime объект"""
        if isinstance(date_obj, datetime):
            return date_obj
        elif isinstance(date_obj, str):
            try:
                # Попытка парсинга строки даты
                from dateutil import parser
                return parser.parse(date_obj)
            except:
                return None
        return None