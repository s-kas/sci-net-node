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

    def render(self, emails: List[Dict[str, Any]], email_handler=None):
        """
        Отображение основной панели
        emails - список писем, которые прошли через фильтры боковой панели
        """
        if not emails:
            st.info("📭 Нет писем с DOI для отображения")
            return

        st.header(f"📚 Найдено писем: {len(emails)}")

        # Создаем словарь для группировки по уникальным DOI
        grouped = {}
        for email in emails:
            doi = self.extract_first_doi(email.get('text', ''))
            if not doi:
                continue

            if doi not in grouped:
                grouped[doi] = []
            grouped[doi].append(email)

        # Формируем карточки для уникальных DOI
        for doi, group_emails in grouped.items():
            merged_data = self.merge_email_data(group_emails)

            with st.container():
                st.markdown(
                    """<div style="border: 1px solid #ddd; border-radius: 10px; padding: 15px; margin: 10px 0; background-color: #f9f9f9;">""",
                    unsafe_allow_html=True)

                st.markdown(f"### 📄 DOI: [{doi}](https://doi.org/{doi})")

                pub_type = merged_data.get('type', 'Не указан')
                year = merged_data.get('year', 'Не указан')
                title = merged_data.get('title', 'Без названия')
                st.markdown(f"**Тип (M3/PY):** {pub_type}")
                st.markdown(f"**Название (TI):** {title}")
                st.markdown(f"**Год (PY):** {year}")

                authors = merged_data.get('authors', [])
                if authors:
                    first_author = authors[0]
                    last_author = authors[-1] if len(authors) > 1 else ''
                    st.markdown(f"**Первый автор:** {first_author}")
                    if last_author and last_author != first_author:
                        st.markdown(f"**Последний автор:** {last_author}")

                st.markdown("</div>", unsafe_allow_html=True)

    def extract_first_doi(self, text: str) -> str:
        """Извлечение первого DOI из текста письма"""
        import re
        doi_pattern = r'\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b'
        matches = re.findall(doi_pattern, text, re.IGNORECASE)
        return matches[0] if matches else ''

    def merge_email_data(self, emails: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Объединение данных из всех писем с одним DOI.
        Значения берутся с приоритетом первого найденного или последнего для списка авторов.
        """
        merged = {
            'type': '',
            'year': '',
            'title': '',
            'authors': []
        }

        for email in emails:
            # Получаем RIS данные из письма, если они есть
            ris_data = email.get('ris_data', {})

            # Тип публикации (M3, если нет - TY)
            type_val = ris_data.get('M3') or ris_data.get('TY')
            if type_val and not merged['type']:
                merged['type'] = type_val

            # Год публикации PY
            year_val = ris_data.get('PY')
            if year_val and not merged['year']:
                merged['year'] = year_val

            # Название TI
            title_val = ris_data.get('TI')
            if title_val and not merged['title']:
                merged['title'] = title_val

            # Авторы AU - берем в виде списка, последний список авторов приоритетен
            authors_val = ris_data.get('AU')
            if authors_val:
                if isinstance(authors_val, list):
                    merged['authors'] = authors_val
                else:
                    merged['authors'] = [authors_val]

        return merged
