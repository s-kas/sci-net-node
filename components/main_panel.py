"""
Основная панель с карточками публикаций для Sci.Net.Node
Оглавление журнала: серая карточка-лента, раскрытие через горизонтальный разделитель со стрелкой
"""

import streamlit as st
from typing import List, Dict, Any
import pandas as pd
from datetime import datetime
from config import REQUEST_PATTERNS, SCINET_CORE_EMAIL
import urllib.parse

SECTION_DIVIDER_STYLE = """
<style>
.card-toc {
  background: #f1f3f5; /* светло-серый фон для оглавления */
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 16px 18px;
  margin: 12px 0;
}
.card-toc:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.card-meta { color:#4d4d4d; font-size:0.95rem; }
.hr-toggle {
  cursor: pointer;
  user-select: none;
  margin: 8px 0 0 0;
  padding: 6px 0;
  display:flex; align-items:center; gap:8px;
  color:#495057;
  border-top: 1px solid #dee2e6; /* горизонтальный разделитель */
}
.hr-toggle .arrow { transition: transform .2s ease; }
.hr-toggle.open .arrow { transform: rotate(180deg); }
.details-pane {
  background: #fafbfc; /* более светлый фон */
  border: 1px solid #eceff1;
  border-radius: 8px;
  padding: 14px 16px;
  margin: 8px 0 2px 0;
}
.badge { background:#e9ecef; border-radius:12px; padding:2px 8px; font-size:0.85rem; }
</style>
"""

class MainPanel:
    """Основная панель в виде оглавления журнала с уникальными DOI"""

    def __init__(self):
        pass

    def render(self, publications: List[Dict[str, Any]], email_handler=None):
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

        # Подключаем CSS стили
        st.markdown(SECTION_DIVIDER_STYLE, unsafe_allow_html=True)

        # Группировка по DOI (уникальные карточки)
        unique_publications = self._group_by_unique_doi(publications)
        st.header(f"📚 Найдено публикаций: {len(unique_publications)}")

        # Лента карточек-оглавления
        for doi, pub_data in unique_publications.items():
            self._render_toc_card(pub_data, email_handler)

    # ===== ГРУППИРОВКА И АГРЕГАЦИЯ =====
    def _group_by_unique_doi(self, publications: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        grouped: Dict[str, Dict[str, Any]] = {}
        for pub in publications:
            doi = self._clean_doi(pub.get('doi', ''))
            if not doi:
                continue
            g = grouped.setdefault(doi, {
                'doi': doi,
                'title': '', 'type': '', 'year': '', 'journal': '',
                'first_author': '', 'last_author': '', 'authors': set(),
                'keywords': set(), 'abstract': '', 'notes': [],
                'volume': '', 'issue': '', 'pages': '', 'emails': []
            })
            # Фильтрация значений: не брать текст в [квадратных скобках] и html/mailto
            def acceptable(val):
                if not isinstance(val, str):
                    return True
                s = val.strip()
                if not s:
                    return False
                if s.startswith('[') and s.endswith(']'):
                    return False
                if s.startswith('href=') or s.startswith('mailto:'):
                    return False
                return True
            for field in ['title','journal','volume','issue','pages','abstract']:
                v = pub.get(field)
                if v and not g[field] and acceptable(v):
                    g[field] = v
            t = pub.get('type','')
            if t and not g['type'] and acceptable(t):
                g['type'] = t
            y = pub.get('year','')
            if y and not g['year'] and str(y).isdigit() and 1800 <= int(y) <= 2100:
                g['year'] = str(y)
            au = pub.get('authors', [])
            if isinstance(au, list):
                g['authors'].update([a for a in au if acceptable(a)])
                if au and not g['first_author']:
                    g['first_author'] = au[0]
                if len(au) > 1:
                    g['last_author'] = au[-1]
            elif isinstance(au, str) and acceptable(au):
                g['authors'].add(au)
                if not g['first_author']:
                    g['first_author'] = au
            kws = pub.get('keywords', [])
            if isinstance(kws, list):
                g['keywords'].update([k for k in kws if acceptable(k)])
            elif isinstance(kws, str) and acceptable(kws):
                g['keywords'].add(kws)
            note = pub.get('notes','')
            if isinstance(note, str) and acceptable(note) and note not in g['notes']:
                g['notes'].append(note)
            g['emails'].append({
                'folder': pub.get('folder',''), 'from': pub.get('from',''),
                'subject': pub.get('subject',''), 'date': pub.get('date',''), 'uid': pub.get('uid',''),
                'text': pub.get('text',''), 'html': pub.get('html','')
            })
        for g in grouped.values():
            g['authors'] = sorted(list(g['authors']))
            g['keywords'] = sorted(list(g['keywords']))
        return grouped

    def _clean_doi(self, doi: str) -> str:
        if not doi:
            return ''
        s = str(doi).strip()
        for pref in ('https://doi.org/','http://doi.org/','doi.org/','DOI:','doi:'):
            s = s.replace(pref,'')
        return s.strip()

    # ===== КАРТОЧКА-ОГЛАВЛЕНИЕ =====
    def _render_toc_card(self, pub_data: Dict[str, Any], email_handler=None):
        doi = pub_data['doi']
        title = pub_data.get('title') or 'Без названия'
        meta_bits = []
        if pub_data.get('type'): meta_bits.append(pub_data['type'])
        if pub_data.get('year'): meta_bits.append(pub_data['year'])
        if pub_data.get('journal'): meta_bits.append(pub_data['journal'])
        fa = pub_data.get('first_author')
        la = pub_data.get('last_author')
        if fa and la and fa != la:
            meta_bits.append(f"Авторы: {fa} – {la}")
        elif fa:
            meta_bits.append(f"Автор: {fa}")

        st.markdown("<div class='card-toc'>", unsafe_allow_html=True)
        st.markdown(f"**{title}**")
        meta_line = " • ".join([b for b in meta_bits if b])
        st.markdown(f"<div class='card-meta'>DOI: <code>{doi}</code> • {meta_line}</div>", unsafe_allow_html=True)

        # Разделитель со стрелкой и раскрытием деталей
        key = f"details_{doi}"
        is_open = st.toggle("Показать детали", key=key, value=False)
        arrow_class = "hr-toggle open" if is_open else "hr-toggle"
        st.markdown(f"<div class='{arrow_class}'><span class='arrow'>⬇️</span><span>Детали</span></div>", unsafe_allow_html=True)

        if is_open:
            st.markdown("<div class='details-pane'>", unsafe_allow_html=True)
            self._render_details_tabs(pub_data, email_handler)
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    # ===== ДЕТАЛИ =====
    def _render_details_tabs(self, pub_data: Dict[str, Any], email_handler=None):
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
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📝 Основные данные")
            authors = pub_data.get('authors', [])
            if authors:
                st.markdown("**Авторы (AU):**")
                for i, author in enumerate(authors[:10]):
                    st.markdown(f"{i+1}. {author}")
                if len(authors) > 10:
                    st.markdown(f"*...и еще {len(authors)-10} авторов*")
            for label, field in [("Том (VL)", 'volume'), ("Выпуск (IS)", 'issue'), ("Страницы (SP)", 'pages')]:
                v = pub_data.get(field)
                if v:
                    st.markdown(f"**{label}:** {v}")
        with col2:
            st.subheader("🏷️ Метаданные")
            keywords = pub_data.get('keywords', [])
            if keywords:
                st.markdown("**Ключевые слова (KW/DE):**")
                st.markdown(", ".join(keywords[:15]))
                if len(keywords) > 15:
                    st.markdown(f"*...и еще {len(keywords)-15} ключевых слов*")
            abstract = pub_data.get('abstract', '')
            if abstract:
                st.markdown("**Абстракт (AB):**")
                with st.expander("Показать абстракт"):
                    st.markdown(abstract)
            notes = pub_data.get('notes', [])
            if notes:
                st.markdown("**Заметки (N2/PA):**")
                for i, note in enumerate(notes, 1):
                    st.markdown(f"{i}. {note}")

    def _render_emails_tab(self, emails: List[Dict[str, Any]]):
        st.subheader(f"📧 Письма с этой публикацией ({len(emails)})")
        if not emails:
            st.info("Нет писем для отображения")
            return
        for i, email in enumerate(emails, 1):
            with st.expander(f"Письмо {i}: {email.get('subject','Без темы')[:60]}..."):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**📁 Папка:** {email.get('folder','Не указана')}")
                    st.markdown(f"**👤 От кого:** {email.get('from','Не указан')}")
                    st.markdown(f"**📅 Дата:** {self._format_date(email.get('date',''))}")
                with col2:
                    st.markdown(f"**🆔 UID:** {email.get('uid','Не указан')}")
                txt = email.get('text','')
                if txt:
                    prev = txt[:300] + ("..." if len(txt) > 300 else "")
                    st.markdown("**📄 Содержимое (превью):**")
                    st.markdown(f"```\n{prev}\n```")

    def _render_actions_tab(self, pub_data: Dict[str, Any], email_handler=None):
        st.subheader("🔗 Доступные действия")
        doi = pub_data.get('doi','')
        title = pub_data.get('title','')
        if not doi:
            st.warning("DOI не найден для выполнения действий")
            return
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if st.button("📋 Тип работы", key=f"m3_{doi}"):
                self._create_request_link("M3_REQUEST", doi, title, email_handler)
            if st.button("📚 PDF файл", key=f"pdf_{doi}"):
                self._create_request_link("PDF_REQUEST", doi, title, email_handler)
        with col2:
            if st.button("🎯 Ключевые слова", key=f"kw_{doi}"):
                self._create_request_link("KW_REQUEST", doi, title, email_handler)
            if st.button("📖 Цитирования", key=f"cits_{doi}"):
                self._create_request_link("CITS_REQUEST", doi, title, email_handler)
        with col3:
            st.markdown(f"[🔗 DOI.org](https://doi.org/{doi})")
            st.markdown(f"[🎓 Google Scholar](https://scholar.google.com/scholar?q={urllib.parse.quote(title)})")
        with col4:
            st.markdown(f"[📚 PubMed](https://pubmed.ncbi.nlm.nih.gov/?term={urllib.parse.quote(title)})")

    def _create_request_link(self, request_type: str, doi: str, title: str, email_handler=None):
        pattern = REQUEST_PATTERNS.get(request_type, "[request]")
        body = f"{pattern} https://doi.org/{doi}"
        mailto_link = f"mailto:{SCINET_CORE_EMAIL}?subject={urllib.parse.quote(title)}&body={urllib.parse.quote(body)}"
        st.success("🔗 Ссылка для запроса создана:")
        st.markdown(f"[📧 Открыть в почтовом клиенте]({mailto_link})")
        if email_handler and email_handler.connected:
            if st.button("📤 Отправить запрос", key=f"send_{request_type}_{doi}"):
                if email_handler.send_request_email(title, body):
                    st.success("✅ Запрос отправлен!")
                else:
                    st.error("❌ Ошибка отправки запроса")

    def _format_date(self, date_obj):
        if isinstance(date_obj, datetime):
            return date_obj.strftime('%Y-%m-%d %H:%M')
        elif isinstance(date_obj, str):
            return date_obj
        else:
            return str(date_obj) if date_obj else 'Не указана'
