"""
Основная панель с карточками публикаций для Sci.Net.Node
Оглавление журнала с серым фоном; вертикальный слайдер раскрытия; очистка HTML-тегов в индексах
"""

import re
import streamlit as st
from typing import List, Dict, Any
import pandas as pd
from datetime import datetime
from config import REQUEST_PATTERNS, SCINET_CORE_EMAIL
import urllib.parse

# Стили: карточка-оглавление (серый), детали (светло-серый), боковые/прочие панели остаются темно-серыми через базовую тему
CUSTOM_CSS = """
<style>
.card-toc { background:#f1f3f5; border:1px solid #e0e0e0; border-radius:10px; padding:16px 18px; margin:14px 0; }
.card-toc:hover { box-shadow:0 2px 10px rgba(0,0,0,0.08); }
.card-title { font-weight:600; font-size:1.05rem; color:#212529; }
.card-meta  { color:#495057; font-size:0.92rem; }

.slider-vert { position:relative; height:36px; cursor:pointer; display:flex; align-items:center; gap:8px; color:#495057; }
.slider-rail { position:absolute; left:0; right:0; top:0; height:1px; background:#dee2e6; }
.slider-thumb { width:24px; height:24px; border-radius:50%; background:#ced4da; border:1px solid #adb5bd; display:flex; align-items:center; justify-content:center; z-index:1; }
.slider-icon { transform:rotate(90deg); font-size:14px; }

.details-pane { background:#fafbfc; border:1px solid #eceff1; border-radius:10px; padding:14px 16px; margin:8px 0 0 0; }
.badge { background:#e9ecef; border-radius:12px; padding:2px 8px; font-size:0.85rem; color:#343a40; }
</style>
"""

HTML_TAG_RE = re.compile(r"<[^>]+>")
MAILTO_RE = re.compile(r"^(mailto:|href=)", re.IGNORECASE)
BRACKETS_RE = re.compile(r"^\s*\[.*\]\s*$")

class MainPanel:
    """Основная панель в виде оглавления журнала с уникальными DOI"""

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

        # Подключаем CSS
        st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

        # Группируем по уникальным DOI и агрегируем
        unique_map = self._group_by_unique_doi(publications)
        st.header(f"📚 Найдено публикаций: {len(unique_map)}")

        # Лента карточек
        for doi, pub in unique_map.items():
            self._render_toc_card(pub, email_handler)

    # ===== Служебные методы очистки =====
    def _clean_html(self, s: Any) -> str:
        if s is None:
            return ""
        s = str(s)
        s = HTML_TAG_RE.sub("", s)
        return s.strip()

    def _acceptable(self, val: Any) -> bool:
        if val is None:
            return False
        if not isinstance(val, str):
            return True
        s = val.strip()
        if not s:
            return False
        if BRACKETS_RE.match(s):
            return False
        if MAILTO_RE.match(s):
            return False
        return True

    def _clean_doi(self, doi: str) -> str:
        if not doi:
            return ''
        s = str(doi).strip()
        for p in ('https://doi.org/','http://doi.org/','doi.org/','DOI:','doi:'):
            s = s.replace(p,'')
        return s.strip()

    # ===== Группировка и агрегация =====
    def _group_by_unique_doi(self, publications: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        grouped: Dict[str, Dict[str, Any]] = {}
        for pub in publications:
            doi = self._clean_doi(pub.get('doi',''))
            if not doi:
                continue
            g = grouped.setdefault(doi, {
                'doi': doi, 'title':'', 'type':'', 'year':'', 'journal':'',
                'first_author':'', 'last_author':'', 'authors': set(), 'keywords': set(),
                'abstract':'', 'notes': [], 'volume':'', 'issue':'', 'pages':'', 'emails': []
            })
            # Поля одиночные — первое пригодное значение, очищаем HTML
            for field in ['title','journal','volume','issue','pages','abstract']:
                v = pub.get(field)
                if v and not g[field] and self._acceptable(v):
                    g[field] = self._clean_html(v)
            t = pub.get('type','')
            if t and not g['type'] and self._acceptable(t):
                g['type'] = self._clean_html(t)
            y = pub.get('year','')
            if y and not g['year'] and str(y).isdigit() and 1800 <= int(y) <= 2100:
                g['year'] = str(y)
            # Авторы/ключевые слова
            au = pub.get('authors', [])
            if isinstance(au, list):
                for a in au:
                    if self._acceptable(a):
                        g['authors'].add(self._clean_html(a))
                if au and not g['first_author']:
                    g['first_author'] = self._clean_html(au[0])
                if len(au) > 1:
                    g['last_author'] = self._clean_html(au[-1])
            elif isinstance(au, str) and self._acceptable(au):
                g['authors'].add(self._clean_html(au))
                if not g['first_author']:
                    g['first_author'] = self._clean_html(au)
            kws = pub.get('keywords', [])
            if isinstance(kws, list):
                for k in kws:
                    if self._acceptable(k):
                        g['keywords'].add(self._clean_html(k))
            elif isinstance(kws, str) and self._acceptable(kws):
                g['keywords'].add(self._clean_html(kws))
            note = pub.get('notes','')
            if isinstance(note, str) and self._acceptable(note) and note not in g['notes']:
                g['notes'].append(self._clean_html(note))
            # Письма
            g['emails'].append({
                'folder': pub.get('folder',''), 'from': pub.get('from',''),
                'subject': pub.get('subject',''), 'date': pub.get('date',''), 'uid': pub.get('uid',''),
                'text': pub.get('text',''), 'html': pub.get('html','')
            })
        for g in grouped.values():
            g['authors'] = sorted(list(g['authors']))
            g['keywords'] = sorted(list(g['keywords']))
        return grouped

    # ===== Рендер карточки-оглавления =====
    def _render_toc_card(self, pub: Dict[str, Any], email_handler=None):
        doi = pub['doi']
        title = pub.get('title') or 'Без названия'
        st.markdown("<div class='card-toc'>", unsafe_allow_html=True)
        st.markdown(f"<div class='card-title'>{self._clean_html(title)}</div>", unsafe_allow_html=True)
        # Металиния
        meta = []
        if pub.get('type'): meta.append(self._clean_html(pub['type']))
        if pub.get('year'): meta.append(self._clean_html(pub['year']))
        if pub.get('journal'): meta.append(self._clean_html(pub['journal']))
        fa, la = pub.get('first_author'), pub.get('last_author')
        if fa and la and fa != la:
            meta.append(f"Авторы: {self._clean_html(fa)} – {self._clean_html(la)}")
        elif fa:
            meta.append(f"Автор: {self._clean_html(fa)}")
        meta_line = " • ".join(meta)
        st.markdown(f"<div class='card-meta'>DOI: <code>{doi}</code>{' • ' + meta_line if meta_line else ''}</div>", unsafe_allow_html=True)

        # Вертикальный слайдер (визуальный): имитируем движок через toggle + оформленный ползунок
        open_key = f"open_{doi}"
        is_open = st.toggle("Детали", key=open_key, value=False)
        st.markdown("<div class='slider-vert'><div class='slider-rail'></div><div class='slider-thumb'><span class='slider-icon'>➜</span></div><span>Потяните вниз, чтобы раскрыть</span></div>", unsafe_allow_html=True)

        if is_open:
            st.markdown("<div class='details-pane'>", unsafe_allow_html=True)
            self._render_details_tabs(pub, email_handler)
            st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # ===== Детали =====
    def _render_details_tabs(self, pub: Dict[str, Any], email_handler=None):
        tab1, tab2, tab3, tab4 = st.tabs(["📋 Данные", "📧 Письма", "🔗 Действия", "📊 Статистика"])
        with tab1:
            self._render_publication_data_tab(pub)
        with tab2:
            self._render_emails_tab(pub.get('emails', []))
        with tab3:
            self._render_actions_tab(pub, email_handler)
        with tab4:
            self._render_stats_tab(pub)

    def _render_publication_data_tab(self, pub: Dict[str, Any]):
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📝 Основные данные")
            authors = pub.get('authors', [])
            if authors:
                st.markdown("**Авторы (AU):**")
                for i, a in enumerate(authors[:10]):
                    st.markdown(f"{i+1}. {self._clean_html(a)}")
                if len(authors) > 10:
                    st.markdown(f"*...и еще {len(authors)-10} авторов*")
            for label, field in [("Том (VL)", 'volume'), ("Выпуск (IS)", 'issue'), ("Страницы (SP)", 'pages')]:
                v = pub.get(field)
                if v:
                    st.markdown(f"**{label}:** {self._clean_html(v)}")
        with col2:
            st.subheader("🏷️ Метаданные")
            keywords = pub.get('keywords', [])
            if keywords:
                st.markdown("**Ключевые слова (KW/DE):**")
                st.markdown(", ".join([self._clean_html(k) for k in keywords[:15]]))
                if len(keywords) > 15:
                    st.markdown(f"*...и еще {len(keywords)-15} ключевых слов*")
            abstract = pub.get('abstract', '')
            if abstract:
                st.markdown("**Абстракт (AB):**")
                with st.expander("Показать абстракт"):
                    st.markdown(self._clean_html(abstract))
            notes = pub.get('notes', [])
            if notes:
                st.markdown("**Заметки (N2/PA):**")
                for i, note in enumerate(notes, 1):
                    st.markdown(f"{i}. {self._clean_html(note)}")

    def _render_emails_tab(self, emails: List[Dict[str, Any]]):
        st.subheader(f"📧 Письма с этой публикацией ({len(emails)})")
        if not emails:
            st.info("Нет писем для отображения")
            return
        for i, email in enumerate(emails, 1):
            with st.expander(f"Письмо {i}: {self._clean_html(email.get('subject','Без темы'))[:60]}..."):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**📁 Папка:** {self._clean_html(email.get('folder','Не указана'))}")
                    st.markdown(f"**👤 От кого:** {self._clean_html(email.get('from','Не указан'))}")
                    st.markdown(f"**📅 Дата:** {self._format_date(email.get('date',''))}")
                with col2:
                    st.markdown(f"**🆔 UID:** {self._clean_html(email.get('uid','Не указан'))}")
                txt = email.get('text','')
                if txt:
                    prev = self._clean_html(txt)[:300] + ("..." if len(txt) > 300 else "")
                    st.markdown("**📄 Содержимое (превью):**")
                    st.markdown(f"```\n{prev}\n```")

    def _render_actions_tab(self, pub: Dict[str, Any], email_handler=None):
        st.subheader("🔗 Доступные действия")
        doi = pub.get('doi','')
        title = pub.get('title','')
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
