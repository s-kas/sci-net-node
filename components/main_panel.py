"""
Основная панель с карточками публикаций для Sci.Net.Node
Оглавление журнала: карточки на сером фоне, детали по переключателю на светло‑серой вставке
"""

import streamlit as st
from typing import List, Dict, Any
import pandas as pd
from datetime import datetime
from config import REQUEST_PATTERNS, SCINET_CORE_EMAIL
import urllib.parse
import re

# Цвета и стили: карточки (серый), детали (светло‑серый);
# общая тёмная тема сохраняется базовой темой приложения
CUSTOM_CSS = """
<style>
.card-toc { background:#3a3a3a; border:1px solid #4a4a4a; border-radius:10px; padding:16px 18px; margin:14px 0; color:#e9e9e9; }
.card-toc:hover { box-shadow:0 2px 10px rgba(0,0,0,0.25); }
.card-title { font-weight:600; font-size:1.06rem; color:#ffffff; }
.card-meta  { color:#c7c7c7; font-size:0.92rem; }
.details-pane { background:#f2f3f5; border:1px solid #e0e0e0; border-radius:10px; padding:14px 16px; margin:8px 0 0 0; color:#212529; }
.badge { background:#e9ecef; border-radius:12px; padding:2px 8px; font-size:0.85rem; color:#343a40; }
.slider-hint { color:#c7c7c7; font-size:0.86rem; margin-top:6px; }
</style>
"""

HTML_TAG_RE = re.compile(r"<[^>]+>")
MAILTO_RE = re.compile(r"^(mailto:|href=)", re.IGNORECASE)
BRACKETS_RE = re.compile(r"^\s*\[.*\]\s*$")

class MainPanel:
    """Основная панель: лента карточек (оглавление) только по уникальным DOI"""

    def render(self, publications: List[Dict[str, Any]], email_handler=None):
        if not publications:
            st.info("📭 Нет писем с DOI для отображения")
            st.markdown("""
            1. Подключитесь к почте → Загрузите письма
            2. Выберите папки и период → Нажмите «Загрузить письма»
            3. Используйте фильтры
            """)
            return

        st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

        unique = self._group_by_unique_doi(publications)
        st.header(f"📚 Найдено публикаций: {len(unique)}")

        for doi, pub in unique.items():
            self._render_toc_card(pub, email_handler)

    # ===== Группировка и агрегация =====
    def _group_by_unique_doi(self, publications: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        grouped: Dict[str, Dict[str, Any]] = {}
        for p in publications:
            doi = self._clean_doi(p.get('doi',''))
            if not doi:
                continue
            g = grouped.setdefault(doi, {
                'doi': doi,
                'title':'', 'type':'', 'year':'', 'journal':'',
                'first_author':'', 'last_author':'', 'authors': [], 'keywords': [],
                'volume':'', 'issue':'', 'pages':'', 'abstract':'', 'notes': [],
                'emails': []
            })
            # Одиночные поля: первое валидное значение без HTML и без [ ... ]
            for field in ['title','journal','volume','issue','pages','abstract','type','year']:
                v = p.get(field, '')
                if v and not g[field] and self._acceptable(v):
                    g[field] = self._strip_html(v)
            # Авторы/ключевые слова — агрегируем уникально
            au = p.get('authors', [])
            if isinstance(au, list):
                for a in au:
                    if self._acceptable(a):
                        g['authors'].append(self._strip_html(a))
            elif au and self._acceptable(au):
                g['authors'].append(self._strip_html(au))
            # Первый/последний автор
            if g['authors']:
                g['first_author'] = g['first_author'] or g['authors'][0]
                if len(g['authors'])>1:
                    g['last_author'] = g['authors'][-1]
            # Ключевые слова
            kws = p.get('keywords', [])
            if isinstance(kws, list):
                for k in kws:
                    if self._acceptable(k):
                        g['keywords'].append(self._strip_html(k))
            elif kws and self._acceptable(kws):
                g['keywords'].append(self._strip_html(kws))
            # Заметки
            note = p.get('notes','')
            if note and self._acceptable(note):
                g['notes'].append(self._strip_html(note))
            # Письма
            g['emails'].append({
                'folder': p.get('folder',''), 'from': p.get('from',''),
                'subject': self._strip_html(p.get('subject','')), 'date': p.get('date',''), 'uid': p.get('uid',''),
                'text': self._strip_html(p.get('text',''))
            })
        # Уникализация списков
        for g in grouped.values():
            g['authors'] = list(dict.fromkeys(g['authors']))
            g['keywords'] = list(dict.fromkeys(g['keywords']))
        return grouped

    # ===== Карточка оглавления и детали =====
    def _render_toc_card(self, pub: Dict[str, Any], email_handler=None):
        doi = pub['doi']
        title = pub.get('title') or 'Без названия'
        pub_type = pub.get('type') or 'Не указан'
        year = pub.get('year') or 'Не указан'
        journal = pub.get('journal') or 'Не указан'
        fa = pub.get('first_author'); la = pub.get('last_author')
        authors_line = ''
        if fa and la and fa!=la:
            authors_line = f"Авторы: {fa} – {la}"
        elif fa:
            authors_line = f"Автор: {fa}"

        st.markdown("<div class='card-toc'>", unsafe_allow_html=True)
        st.markdown(f"<div class='card-title'>{self._strip_html(title)}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='card-meta'>DOI: <code>{doi}</code> • {self._strip_html(pub_type)} • {self._strip_html(str(year))} • {self._strip_html(journal)}</div>", unsafe_allow_html=True)
        if authors_line:
            st.markdown(f"<div class='card-meta'>{self._strip_html(authors_line)}</div>", unsafe_allow_html=True)

        expanded = st.toggle("Детали", key=f"details_{doi}")
        st.markdown("<div class='slider-hint'>Потяните вниз, чтобы раскрыть</div>", unsafe_allow_html=True)
        if expanded:
            st.markdown("<div class='details-pane'>", unsafe_allow_html=True)
            self._render_details_tabs(pub, email_handler)
            st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    def _render_details_tabs(self, d: Dict[str, Any], email_handler=None):
        tab1, tab2, tab3, tab4 = st.tabs(["📋 Данные", "📧 Письма", "🔗 Действия", "📊 Статистика"])
        with tab1:
            self._render_publication_data_tab(d)
        with tab2:
            self._render_emails_tab(d.get('emails', []))
        with tab3:
            self._render_actions_tab(d, email_handler)
        with tab4:
            self._render_stats_tab(d)

    def _render_publication_data_tab(self, d: Dict[str, Any]):
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📝 Основные данные")
            authors = d.get('authors', [])
            if authors:
                st.markdown("**Авторы (AU):**")
                for i, a in enumerate(authors[:12]):
                    st.markdown(f"{i+1}. {a}")
                if len(authors)>12:
                    st.markdown(f"…и еще {len(authors)-12} авторов")
            for label, key in [("Том (VL)", 'volume'), ("Выпуск (IS)", 'issue'), ("Страницы (SP)", 'pages')]:
                v = d.get(key, '')
                if v:
                    st.markdown(f"**{label}:** {v}")
        with col2:
            st.subheader("🏷️ Метаданные")
            kws = d.get('keywords', [])
            if kws:
                st.markdown("**Ключевые слова (KW/DE):**")
                st.markdown(", ".join(kws[:20]))
                if len(kws)>20:
                    st.markdown(f"…и еще {len(kws)-20} ключевых слов")
            if d.get('abstract'):
                with st.expander("Показать абстракт"):
                    st.markdown(d['abstract'])
            notes = d.get('notes', [])
            if notes:
                st.markdown("**Заметки (N2/PA):**")
                for i, n in enumerate(notes,1):
                    st.markdown(f"{i}. {n}")

    def _render_emails_tab(self, emails: List[Dict[str, Any]]):
        st.subheader(f"📧 Письма ({len(emails)})")
        if not emails:
            st.info("Нет писем для отображения")
            return
        for i, e in enumerate(emails, 1):
            with st.expander(f"Письмо {i}: {e.get('subject','Без темы')[:70]}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**📁 Папка:** {e.get('folder','')}")
                    st.markdown(f"**👤 От кого:** {e.get('from','')}")
                    st.markdown(f"**📅 Дата:** {self._format_date(e.get('date',''))}")
                with col2:
                    st.markdown(f"**🆔 UID:** {e.get('uid','')}")
                if e.get('text'):
                    preview = e['text'][:500] + ("…" if len(e['text'])>500 else "")
                    st.markdown("**📄 Предпросмотр:**")
                    st.code(preview)

    def _render_actions_tab(self, d: Dict[str, Any], email_handler=None):
        st.subheader("🔗 Доступные действия")
        doi = d.get('doi',''); title = d.get('title','')
        if not doi:
            st.warning("DOI не найден")
            return
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("📋 Тип работы", key=f"m3_{doi}"):
                self._create_request_link("M3_REQUEST", doi, title, email_handler)
            if st.button("📚 PDF файл", key=f"pdf_{doi}"):
                self._create_request_link("PDF_REQUEST", doi, title, email_handler)
            if st.button("🔬 PubMed ID", key=f"pmid_{doi}"):
                self._create_request_link("PMID_REQUEST", doi, title, email_handler)
        with c2:
            if st.button("🎯 Ключевые слова", key=f"kw_{doi}"):
                self._create_request_link("KW_REQUEST", doi, title, email_handler)
            if st.button("📖 Цитирования", key=f"cits_{doi}"):
                self._create_request_link("CITS_REQUEST", doi, title, email_handler)
        with c3:
            st.markdown(f"[DOI](https://doi.org/{doi})  |  [Scholar](https://scholar.google.com/scholar?q={urllib.parse.quote(title)})  |  [PubMed](https://pubmed.ncbi.nlm.nih.gov/?term={urllib.parse.quote(title)})  |  [Crossref](https://search.crossref.org/?q={urllib.parse.quote(title)})")

    # ===== Вспомогательные =====
    def _clean_doi(self, doi: str) -> str:
        if not doi: return ''
        s = str(doi).strip()
        for pref in ['https://doi.org/','http://doi.org/','doi.org/','DOI:','doi:']:
            s = s.replace(pref,'')
        return s.strip()

    def _strip_html(self, s: Any) -> str:
        if s is None: return ''
        s = str(s)
        s = HTML_TAG_RE.sub('', s)
        s = s.replace('mailto:','').replace('href=','')
        return s.strip()

    def _acceptable(self, v: Any) -> bool:
        if v is None: return False
        if isinstance(v, str):
            s = v.strip()
            if not s: return False
            if BRACKETS_RE.match(s): return False
            if MAILTO_RE.match(s): return False
        return True

    def _format_date(self, dt):
        if isinstance(dt, datetime):
            return dt.strftime('%Y-%m-%d %H:%M')
        return str(dt)

    def _create_request_link(self, request_type: str, doi: str, title: str, email_handler=None):
        pattern = REQUEST_PATTERNS.get(request_type, "[request]")
        body = f"{pattern} https://doi.org/{doi}"
        mailto_link = f"mailto:{SCINET_CORE_EMAIL}?subject={urllib.parse.quote(title)}&body={urllib.parse.quote(body)}"
        st.markdown(f"[📧 Открыть письмо]({mailto_link})")
        if email_handler and email_handler.connected and st.button("📤 Отправить", key=f"send_{request_type}_{doi}"):
            if email_handler.send_request_email(title, body):
                st.success("✅ Отправлено")
            else:
                st.error("❌ Ошибка отправки")
