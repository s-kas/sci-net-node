"""
Move 'Load emails' button below 'Mailbox folders' selection and set default folders to only INBOX and Sent.
"""
import streamlit as st
from datetime import datetime, date
from typing import List, Dict, Any
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter
import pandas as pd

class SidebarPanel:
    def __init__(self, publications: List[Dict[str, Any]]):
        self.publications = publications
        st.markdown("""
        <style>
        .css-1d391kg { background-color: #f8f9fa !important; }
        .css-1d391kg h2, .css-1d391kg h3 { color:#1a1a1a!important; font-weight:600!important; }
        .css-1d391kg label { color:#333!important; font-weight:500!important; }
        .css-1d391kg .stButton > button { width:100%; background:#007bff; color:#fff; border:none; border-radius:6px; font-weight:500; margin:2px 0; }
        .css-1d391kg .stButton > button:hover { background:#0056b3; }
        @media (prefers-color-scheme: dark) { .css-1d391kg { background:#2a2a2a!important; } .css-1d391kg h2, .css-1d391kg h3 { color:#fff!important; } .css-1d391kg label { color:#e4e4e4!important; } }
        </style>
        """, unsafe_allow_html=True)

    def render_connection_section(self) -> Dict[str, str]:
        st.sidebar.header("🔐 Подключение к почте")
        email = st.sidebar.text_input("Email адрес", placeholder="username@mail.ru", help="Ваш адрес электронной почты Mail.ru")
        password = st.sidebar.text_input("Пароль", type="password", help="Пароль от почтового ящика")
        connect_button = st.sidebar.button("🔗 Подключиться", type="primary")
        return {'email': email, 'password': password, 'connect': connect_button}

    def _get_mailbox_bounds(self) -> tuple[date, date]:
        """Определение периода по умолчанию: от даты первого письма до сегодняшнего дня.
        Используем информацию из публикаций (если уже загружены) как приближение.
        Если данных нет — ставим год назад до сегодня.
        """
        today = date.today()
        if not self.publications:
            return today.replace(year=today.year-1), today
        dates = []
        for p in self.publications:
            d = p.get('date')
            if isinstance(d, str):
                try:
                    from dateutil import parser
                    d = parser.parse(d).date()
                except Exception:
                    d = None
            elif isinstance(d, datetime):
                d = d.date()
            if isinstance(d, date):
                dates.append(d)
        if not dates:
            return today.replace(year=today.year-1), today
        return min(dates), today

    def render_filters_section(self, folders: List[str]) -> Dict[str, Any]:
        st.sidebar.header("🔍 Фильтры")

        # Фильтр по папкам - только INBOX и Отправленные по умолчанию
        default_folders = []
        for folder in folders:
            if folder in ['INBOX', 'Отправленные', 'Sent'] or 'sent' in folder.lower() or 'inbox' in folder.lower():
                default_folders.append(folder)
        
        # Если не найдены стандартные папки, берем первые две
        if not default_folders and folders:
            default_folders = folders[:2] if len(folders) >= 2 else folders
        
        selected_folders = st.sidebar.multiselect(
            "Папки почтового ящика", 
            options=folders, 
            default=default_folders, 
            help="Выберите папки для отображения писем"
        )

        # Кнопка загрузки писем — ПОСЛЕ выбора папок
        load_click = st.sidebar.button("📥 Загрузить письма", type="primary")

        # Период
        st.sidebar.subheader("📅 Период")
        default_from, default_to = self._get_mailbox_bounds()
        col1, col2 = st.sidebar.columns(2)
        with col1:
            date_from = st.date_input("С даты", value=default_from, help="Начальная дата фильтрации")
        with col2:
            date_to = st.date_input("До даты", value=default_to, help="Конечная дата фильтрации")

        # RIS фильтры
        st.sidebar.subheader("📋 RIS поля")
        unique_types = self._get_unique_field_values('type')
        unique_years = self._get_unique_field_values('year')
        selected_types = st.sidebar.multiselect("Тип публикации (M3/TY)", options=unique_types, help="Фильтр по типу работы")
        selected_years = st.sidebar.multiselect("Год публикации (PY)", options=sorted(unique_years, reverse=True), help="Фильтр по году публикации")
        author_search = st.sidebar.text_input("Поиск по автору (AU)", placeholder="Введите имя автора...", help="Поиск по авторам публикации")
        title_search = st.sidebar.text_input("Поиск по заголовку (TI)", placeholder="Введите ключевые слова...", help="Поиск по заголовку публикации")
        keywords_search = st.sidebar.text_input("Поиск по ключевым словам (KW/DE)", placeholder="Введите ключевые слова...", help="Поиск по ключевым словам")

        # Возвращаем сигнал о клике на загрузку вместе с фильтрами
        return {
            'folders': selected_folders,
            'date_from': date_from,
            'date_to': date_to,
            'types': selected_types,
            'years': selected_years,
            'author_search': author_search,
            'title_search': title_search,
            'keywords_search': keywords_search,
            'load_click': load_click
        }

    def render_analytics_section(self, filtered_publications: List[Dict[str, Any]]):
        st.sidebar.header("📊 Аналитика")
        if not filtered_publications:
            st.sidebar.info("Нет данных для анализа")
            return
            
        total_pubs = len(filtered_publications)
        unique_dois = len(set(pub.get('doi', '') for pub in filtered_publications if pub.get('doi')))
        st.sidebar.metric("Всего публикаций", total_pubs)
        st.sidebar.metric("Уникальных DOI", unique_dois)
        
        st.sidebar.subheader("📈 Диаграммы")
        analysis_field = st.sidebar.selectbox(
            "Поле для анализа", 
            options=['type','year','keywords'], 
            format_func=lambda x:{
                'type':'Тип публикации (TY/M3)',
                'year':'Год публикации (PY)',
                'keywords':'Ключевые слова (KW/DE)'
            }[x]
        )
        
        if st.sidebar.button("📊 Показать частоты", key="frequency_chart"):
            self._show_frequency_chart(filtered_publications, analysis_field)
        
        if st.sidebar.button("🌟 Отобразить концепции", key="concepts_chart"):
            self._show_concepts_sankey(filtered_publications)
        
        st.sidebar.subheader("💾 Экспорт")
        if st.sidebar.button("📄 Скачать RIS"):
            self._export_to_ris(filtered_publications)
        if st.sidebar.button("📊 Скачать CSV"):
            self._export_to_csv(filtered_publications)

    def _get_unique_field_values(self, field: str) -> List[str]:
        values = set()
        for pub in self.publications:
            value = pub.get(field)
            if isinstance(value, list):
                values.update(str(v) for v in value if v)
            elif value:
                values.add(str(value))
        return sorted(list(values))

    def _show_frequency_chart(self, publications: List[Dict[str, Any]], field: str):
        """Отображение диаграммы частот для выбранного поля"""
        values = []
        for pub in publications:
            value = pub.get(field)
            if isinstance(value, list):
                values.extend([str(v) for v in value if v])
            elif value:
                values.append(str(value))
        
        if not values:
            st.warning(f"Нет данных для поля {field}")
            return
        
        # Подсчет частот
        freq_counter = Counter(values)
        top_values = freq_counter.most_common(10)  # Топ-10
        
        if not top_values:
            st.warning(f"Нет данных для отображения")
            return
        
        # Создание диаграммы
        labels, counts = zip(*top_values)
        
        fig = px.bar(
            x=list(counts),
            y=list(labels),
            orientation='h',
            title=f"Топ-10 {field}",
            labels={'x': 'Количество', 'y': field.title()}
        )
        fig.update_layout(height=400)
        
        st.plotly_chart(fig, use_container_width=True)

    def _show_concepts_sankey(self, publications: List[Dict[str, Any]]):
        """Отображение Sankey диаграммы связей между концепциями"""
        # Собираем связи между авторами и ключевыми словами
        author_keyword_pairs = []
        
        for pub in publications:
            authors = pub.get('authors', []) or pub.get('AU', [])
            keywords = pub.get('keywords', []) or pub.get('KW', []) or pub.get('DE', [])
            
            if not isinstance(authors, list):
                authors = [authors] if authors else []
            if not isinstance(keywords, list):
                keywords = [keywords] if keywords else []
            
            # Берем первого автора и первые 3 ключевых слова
            first_author = authors[0] if authors else "Неизвестный автор"
            top_keywords = keywords[:3] if keywords else ["Без ключевых слов"]
            
            for keyword in top_keywords:
                author_keyword_pairs.append((str(first_author), str(keyword)))
        
        if not author_keyword_pairs:
            st.warning("Нет данных для создания диаграммы связей")
            return
        
        # Подсчитываем частоты связей
        pair_counter = Counter(author_keyword_pairs)
        top_pairs = pair_counter.most_common(15)  # Топ-15 связей
        
        # Создаем узлы и связи для Sankey
        all_nodes = set()
        for (author, keyword), count in top_pairs:
            all_nodes.add(f"Автор: {author}")
            all_nodes.add(f"КС: {keyword}")
        
        node_list = list(all_nodes)
        node_dict = {node: i for i, node in enumerate(node_list)}
        
        # Создаем связи
        sources = []
        targets = []
        values = []
        
        for (author, keyword), count in top_pairs:
            source_idx = node_dict[f"Автор: {author}"]
            target_idx = node_dict[f"КС: {keyword}"]
            sources.append(source_idx)
            targets.append(target_idx)
            values.append(count)
        
        # Создаем Sankey диаграмму
        fig = go.Figure(data=[go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color="black", width=0.5),
                label=node_list,
                color="lightblue"
            ),
            link=dict(
                source=sources,
                target=targets,
                value=values
            )
        )])
        
        fig.update_layout(
            title_text="Связи между авторами и ключевыми словами",
            font_size=10,
            height=600
        )
        
        st.plotly_chart(fig, use_container_width=True)

    def _export_to_ris(self, publications: List[Dict[str, Any]]):
        """Экспорт публикаций в формат RIS"""
        if not publications:
            st.warning("Нет данных для экспорта")
            return
        
        ris_content = []
        
        for pub in publications:
            ris_content.append("TY  - JOUR")
            
            # Заголовок
            title = pub.get('title') or pub.get('TI') or pub.get('subject', '')
            if title:
                ris_content.append(f"TI  - {title}")
            
            # Авторы
            authors = pub.get('authors', []) or pub.get('AU', [])
            if isinstance(authors, list):
                for author in authors:
                    if author:
                        ris_content.append(f"AU  - {author}")
            elif authors:
                ris_content.append(f"AU  - {authors}")
            
            # Год
            year = pub.get('year') or pub.get('PY')
            if year:
                ris_content.append(f"PY  - {year}")
            
            # Журнал
            journal = pub.get('journal') or pub.get('T2')
            if journal:
                ris_content.append(f"T2  - {journal}")
            
            # DOI
            doi = pub.get('doi') or pub.get('DO')
            if doi:
                ris_content.append(f"DO  - {doi}")
            
            # Ключевые слова
            keywords = pub.get('keywords', []) or pub.get('KW', []) or pub.get('DE', [])
            if isinstance(keywords, list):
                for keyword in keywords:
                    if keyword:
                        ris_content.append(f"KW  - {keyword}")
            elif keywords:
                ris_content.append(f"KW  - {keywords}")
            
            # Аннотация
            abstract = pub.get('abstract') or pub.get('AB') or pub.get('N2')
            if abstract:
                ris_content.append(f"AB  - {abstract}")
            
            ris_content.append("ER  - ")
            ris_content.append("")
        
        # Создаем файл для скачивания
        ris_text = "\n".join(ris_content)
        
        st.download_button(
            label="📄 Скачать RIS файл",
            data=ris_text,
            file_name=f"sci_net_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.ris",
            mime="application/x-research-info-systems"
        )

    def _export_to_csv(self, publications: List[Dict[str, Any]]):
        """Экспорт публикаций в формат CSV"""
        if not publications:
            st.warning("Нет данных для экспорта")
            return
        
        # Подготавливаем данные для CSV
        csv_data = []
        
        for pub in publications:
            row = {
                'Title': pub.get('title') or pub.get('TI') or pub.get('subject', ''),
                'Authors': ', '.join(pub.get('authors', []) or pub.get('AU', []) if isinstance(pub.get('authors') or pub.get('AU', []), list) else [pub.get('authors') or pub.get('AU', '')]),
                'Year': pub.get('year') or pub.get('PY', ''),
                'Journal': pub.get('journal') or pub.get('T2', ''),
                'DOI': pub.get('doi') or pub.get('DO', ''),
                'Type': pub.get('type') or pub.get('M3') or pub.get('TY', ''),
                'Keywords': ', '.join(pub.get('keywords', []) or pub.get('KW', []) or pub.get('DE', []) if isinstance(pub.get('keywords') or pub.get('KW', []) or pub.get('DE', []), list) else [pub.get('keywords') or pub.get('KW') or pub.get('DE', '')]),
                'Abstract': pub.get('abstract') or pub.get('AB') or pub.get('N2', ''),
                'Volume': pub.get('VL', ''),
                'Issue': pub.get('IS', ''),
                'Pages': pub.get('SP', ''),
                'URL': pub.get('UR') or pub.get('L1') or pub.get('L2', ''),
                'Folder': pub.get('folder', ''),
                'Email_From': pub.get('from', ''),
                'Email_Date': pub.get('date', ''),
                'PDF_Count': len(pub.get('pdf_attachments', []))
            }
            csv_data.append(row)
        
        # Создаем DataFrame
        df = pd.DataFrame(csv_data)
        
        # Конвертируем в CSV
        csv_buffer = df.to_csv(index=False, encoding='utf-8-sig')
        
        st.download_button(
            label="📊 Скачать CSV файл",
            data=csv_buffer,
            file_name=f"sci_net_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )