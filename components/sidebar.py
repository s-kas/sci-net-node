"""
Move 'Load emails' button above Period and set default Period from earliest email date to today.
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

        # Кнопка загрузки писем — СЮДА, перед периодом
        load_click = st.sidebar.button("📥 Загрузить письма", type="primary")

        # Фильтр по папкам
        selected_folders = st.sidebar.multiselect("Папки почтового ящика", options=folders, default=folders, help="Выберите папки для отображения писем")

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

    # Остальной код (аналитика/экспорт) без изменений ниже...
    def render_analytics_section(self, filtered_publications: List[Dict[str, Any]]):
        st.sidebar.header("📊 Аналитика")
        if not filtered_publications:
            st.sidebar.info("Нет данных для анализа"); return
        total_pubs = len(filtered_publications)
        unique_dois = len(set(pub.get('doi', '') for pub in filtered_publications if pub.get('doi')))
        st.sidebar.metric("Всего публикаций", total_pubs)
        st.sidebar.metric("Уникальных DOI", unique_dois)
        st.sidebar.subheader("📈 Диаграммы")
        analysis_field = st.sidebar.selectbox("Поле для анализа", options=['type','year','keywords'], format_func=lambda x:{'type':'Тип публикации (TY/M3)','year':'Год публикации (PY)','keywords':'Ключевые слова (KW/DE)'}[x])
        if st.sidebar.button("📊 Показать частоты", key="frequency_chart"): self._show_frequency_chart(filtered_publications, analysis_field)
        if st.sidebar.button("🌟 Отобразить концепции", key="concepts_chart"): self._show_concepts_sankey(filtered_publications)
        st.sidebar.subheader("💾 Экспорт")
        if st.sidebar.button("📄 Скачать RIS"): self._export_to_ris(filtered_publications)
        if st.sidebar.button("📊 Скачать CSV"): self._export_to_csv(filtered_publications)

    def _get_unique_field_values(self, field: str) -> List[str]:
        values=set()
        for pub in self.publications:
            value=pub.get(field)
            if isinstance(value,list): values.update(str(v) for v in value if v)
            elif value: values.add(str(value))
        return sorted(list(values))

    # keep rest (charts/export) same as previous version
