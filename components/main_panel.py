\"\"\"Основная панель с карточками писем для Sci.Net.Node\"\"\"

import streamlit as st
from typing import List, Dict, Any
from datetime import datetime
import urllib.parse

class MainPanel:
    \"\"\"Класс для отображения карточек писем, проходящих через фильтры\"\"\"

    def render(self, emails: List[Dict[str, Any]], email_handler=None):
        \"\"\"Отображение писем как карточек\"\"\"
        if not emails:
            st.info(\"📭 Нет писем, соответствующих текущим фильтрам\")
            return

        st.header(f\"📧 Показано писем: {len(emails)}\")

        for email in emails:
            self._render_email_card(email, email_handler)

    def _render_email_card(self, email: Dict[str, Any], email_handler=None):
        with st.container():
            st.markdown(
                \"\"\"<div style=\"border: 1px solid #ddd; border-radius: 10px; padding: 15px; margin: 10px 0; background-color: #f0f8ff;\">\"\"\",
                unsafe_allow_html=True)
            
            subject = email.get('subject', 'Без темы')
            date = email.get('date')
            date_str = date.strftime('%Y-%m-%d %H:%M') if isinstance(date, datetime) else str(date)
            folder = email.get('folder', '')
            doi = email.get('doi', '')

            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f\"### {subject}\")
                if doi:
                    st.markdown(f\"**DOI:** [{doi}](https://doi.org/{doi})\")
                st.markdown(f\"**Папка:** {folder}\")
                st.markdown(f\"**Дата:** {date_str}\")

            with col2:
                expanded = st.checkbox(\"Показать детали\", key=f\"details_{email.get('uid', '')}\")

            if expanded:
                st.markdown(\"---\")
                self._render_email_details(email, email_handler)

            st.markdown(\"</div>\", unsafe_allow_html=True)

    def _render_email_details(self, email: Dict[str, Any], email_handler=None):
        st.subheader(\"Подробности письма\")

        st.markdown(f\"**От:** {email.get('from', '')}\")
        st.markdown(f\"**Кому:** {email.get('to', '')}\")
        st.markdown(f\"**Тема:** {email.get('subject', '')}\")
        st.markdown(f\"**Дата:** {email.get('date', '')}\")

        # Отобразить тело письма (текст или HTML как plain text)
        text = email.get('text', '')
        if text:
            st.markdown(\"**Тело письма:**\")
            st.text_area(\"\", text, height=200)
        else:
            st.info(\"Текст письма отсутствует\")

        # Кнопки запросов Sci.Net.Core
        if not email_handler or not email_handler.connected:
            st.info(\"Подключитесь к почтовому ящику для отправки запросов\")
            return

        doi = email.get('doi', '')
        subject = email.get('subject', '')
        request_types = {
            \"M3\": \"[M3 request]\",
            \"PDF\": \"[PDF request]\",
            \"PubMed\": \"[PMID request]\",
            \"Citations\": \"[CITS request]\",
            \"Insert Abstract\": \"[insert abstract]\",
            \"Insert Keywords\": \"[insert authors keywords]\",
            \"Insert Notes\": \"[insert notes]\"
        }

        st.markdown(\"🔗 **Доступные запросы к Sci.Net.Core:**\")

        cols = st.columns(4)
        for i, (label, pattern) in enumerate(request_types.items()):
            if cols[i % 4].button(label, key=f\"req_{label}_{email.get('uid', '')}\"):
                body = f\"{pattern} {doi}\" if doi else pattern
                sent = email_handler.send_request_email(subject, body)
                if sent:
                    st.success(f\"Запрос '{label}' отправлен.\")
                else:
                    st.error(f\"Ошибка отправки запроса '{label}'.\")

