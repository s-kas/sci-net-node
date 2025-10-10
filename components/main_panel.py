"""
Основная панель с карточками публикаций для Sci.Net.Node
Вид: оглавление журнала на сером фоне, раскрытие деталей через горизонтальный разделитель со стрелкой
"""

import streamlit as st
from typing import List, Dict, Any
import pandas as pd
from datetime import datetime
from config import REQUEST_PATTERNS, SCINET_CORE_EMAIL
import urllib.parse
import re

BRACKET_RE = re.compile(r"^\s*\[.*\]\s*$")
MAILTO_RE = re.compile(r"^(href=|mailto:)", re.IGNORECASE)

class MainPanel:
    def __init__(self):
        pass

    def render(self, publications: List[Dict[str, Any]], email_handler=None):
        if not publications:
            st.info("📭 Нет писем с DOI для отображения")
            return

        unique_publications = self._group_by_unique_doi(publications)

        # Глобальные стили под "оглавление журнала"
        st.markdown(
            """
            <style>
            .toc-card {background:#f0f0f0;border-radius:10px;padding:14px 18px;margin:10px 0;border:1px solid #e0e0e0}
            .toc-title {font-size:18px;font-weight:600;margin:0;color:#222}
            .toc-meta {color:#555;font-size:14px;margin-top:6px}
            .divider-toggle {display:flex;align-items:center;gap:8px;color:#444;cursor:pointer;margin:10px 0}
            .divider-line {flex:1;height:1px;background:#cfcfcf}
            .divider-arrow {font-size:16px}
            .details-box {background:#fafafa;border:1px solid #e6e6e6;border-radius:8px;padding:14px;margin:8px 0}
            </style>
            """,
            unsafe_allow_html=True,
        )

        st.header(f"📚 Найдено публикаций: {len(unique_publications)}")

        for doi, pub in unique_publications.items():
            self._render_toc_card(pub, email_handler)

    def _group_by_unique_doi(self, publications: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        grouped: Dict[str, Dict[str, Any]] = {}
        for p in publications:
            doi = self._clean_doi(p.get("doi", ""))
            if not doi:
                continue
            g = grouped.setdefault(
                doi,
                {
                    "doi": doi,
                    "title": "",
                    "type": "",
                    "year": "",
                    "journal": "",
                    "first_author": "",
                    "last_author": "",
                    "authors": set(),
                    "keywords": set(),
                    "notes": [],
                    "emails": [],
                },
            )
            # присваиваем первое валидное значение, исключая [] и mailto/html
            def pick(field, value):
                if g[field]:
                    return
                if not value:
                    return
                if isinstance(value, str):
                    v = value.strip()
                    if BRACKET_RE.match(v):
                        return
                    if field == "type" and MAILTO_RE.match(v):
                        return
                    g[field] = v
                else:
                    g[field] = value

            pick("title", p.get("title"))
            pick("journal", p.get("journal"))
            pick("year", p.get("year"))
            pt = p.get("type")
            if pt and isinstance(pt, str) and not MAILTO_RE.match(pt) and not BRACKET_RE.match(pt.strip()):
                if not g["type"]:
                    g["type"] = pt

            # авторы
            authors = p.get("authors", [])
            if isinstance(authors, list):
                for a in authors:
                    if a:
                        g["authors"].add(str(a))
            elif authors:
                g["authors"].add(str(authors))

            if not g["first_author"]:
                if isinstance(authors, list) and authors:
                    g["first_author"] = authors[0]
                elif isinstance(authors, str):
                    g["first_author"] = authors

            if isinstance(authors, list) and len(authors) > 1:
                g["last_author"] = authors[-1]

            # ключевые слова
            kws = p.get("keywords", [])
            if isinstance(kws, list):
                for k in kws:
                    if k and not BRACKET_RE.match(str(k).strip()):
                        g["keywords"].add(str(k))
            elif kws:
                if not BRACKET_RE.match(str(kws).strip()):
                    g["keywords"].add(str(kws))

            n = p.get("notes", "")
            if n and not BRACKET_RE.match(str(n).strip()):
                g["notes"].append(str(n))

            g["emails"].append(
                {
                    "folder": p.get("folder", ""),
                    "from": p.get("from", ""),
                    "subject": p.get("subject", ""),
                    "date": p.get("date", ""),
                    "uid": p.get("uid", ""),
                }
            )

        for v in grouped.values():
            v["authors"] = sorted(list(v["authors"]))
            v["keywords"] = sorted(list(v["keywords"]))
        return grouped

    def _clean_doi(self, doi: str) -> str:
        if not doi:
            return ""
        d = str(doi).strip()
        for pref in ("https://doi.org/", "http://doi.org/", "doi.org/", "DOI:", "doi:"):
            if d.startswith(pref):
                d = d[len(pref):]
        return d.strip()

    def _render_toc_card(self, pub: Dict[str, Any], email_handler=None):
        doi = pub.get("doi", "")
        title = pub.get("title", "Без названия")
        year = pub.get("year", "Не указан")
        journal = pub.get("journal", "Не указан")
        ptype = pub.get("type", "Не указан")
        first_author = pub.get("first_author", "")
        last_author = pub.get("last_author", "")

        with st.container():
            st.markdown('<div class="toc-card">', unsafe_allow_html=True)
            st.markdown(f'<div class="toc-title">{title}</div>', unsafe_allow_html=True)
            meta = []
            meta.append(f"DOI: <code>{doi}</code>")
            if ptype:
                meta.append(f"Тип: {ptype}")
            if year:
                meta.append(f"Год: {year}")
            if journal:
                meta.append(f"Журнал: {journal}")
            if first_author:
                tail = f" – {last_author}" if (last_author and last_author != first_author) else ""
                meta.append(f"Авторы: {first_author}{tail}")
            st.markdown(f'<div class="toc-meta">' + " • ".join(meta) + '</div>', unsafe_allow_html=True)

            # Горизонтальный разделитель со стрелкой
            key = f"toggle_{doi}"
            cols = st.columns([1, 10, 1])
            with cols[0]:
                pass
            with cols[1]:
                clicked = st.button("Показать детали", key=key)
            with cols[2]:
                st.markdown('<span class="divider-arrow">⬇️</span>', unsafe_allow_html=True)
            st.markdown('<div class="divider-line"></div>', unsafe_allow_html=True)

            # Состояние раскрытия (персистентность через session_state)
            if key not in st.session_state:
                st.session_state[key] = False
            if clicked:
                st.session_state[key] = not st.session_state[key]

            if st.session_state[key]:
                with st.container():
                    st.markdown('<div class="details-box">', unsafe_allow_html=True)
                    self._render_details(pub, email_handler)
                    st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('</div>', unsafe_allow_html=True)

    def _render_details(self, pub: Dict[str, Any], email_handler=None):
        tab1, tab2, tab3 = st.tabs(["📧 Письма", "📋 Данные", "🔗 Действия"])

        with tab1:
            self._render_emails_tab(pub.get("emails", []))
        with tab2:
            self._render_publication_data_tab(pub)
        with tab3:
            self._render_actions_tab(pub, email_handler)

    def _render_publication_data_tab(self, pub: Dict[str, Any]):
        col1, col2 = st.columns(2)
        with col1:
            authors = pub.get("authors", [])
            if authors:
                st.markdown("**Авторы (AU):**")
                for i, a in enumerate(authors[:12]):
                    st.markdown(f"{i+1}. {a}")
                if len(authors) > 12:
                    st.markdown(f"*...и еще {len(authors)-12}*")
        with col2:
            keywords = pub.get("keywords", [])
            if keywords:
                st.markdown("**Ключевые слова (KW/DE):**")
                st.markdown(", ".join(keywords[:20]))

    def _render_emails_tab(self, emails: List[Dict[str, Any]]):
        st.subheader(f"Писем: {len(emails)}")
        rows = []
        for e in emails:
            rows.append(
                {
                    "Папка": e.get("folder", ""),
                    "От кого": e.get("from", ""),
                    "Тема": (e.get("subject", "") or "")[:70] + ("…" if len(e.get("subject", "")) > 70 else ""),
                    "Дата": e.get("date", ""),
                    "UID": e.get("uid", ""),
                }
            )
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("Нет писем для отображения")

    def _render_actions_tab(self, pub: Dict[str, Any], email_handler=None):
        doi = pub.get("doi", "")
        title = pub.get("title", "")
        if not doi:
            st.warning("DOI отсутствует")
            return
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("Запросить M3"):
                self._request("M3_REQUEST", doi, title, email_handler)
            if st.button("Запросить PDF"):
                self._request("PDF_REQUEST", doi, title, email_handler)
        with col2:
            if st.button("Запросить KW"):
                self._request("KW_REQUEST", doi, title, email_handler)
            if st.button("Запросить CITS"):
                self._request("CITS_REQUEST", doi, title, email_handler)
        with col3:
            st.markdown(f"[DOI.org](https://doi.org/{doi})  ")
            st.markdown(f"[Google Scholar](https://scholar.google.com/scholar?q={urllib.parse.quote(title)})  ")
            st.markdown(f"[PubMed](https://pubmed.ncbi.nlm.nih.gov/?term={urllib.parse.quote(title)})")

    def _request(self, req: str, doi: str, title: str, email_handler=None):
        pattern = REQUEST_PATTERNS.get(req, "[request]")
        body = f"{pattern} https://doi.org/{doi}"
        mailto_link = f"mailto:{SCINET_CORE_EMAIL}?subject={urllib.parse.quote(title)}&body={urllib.parse.quote(body)}"
        st.markdown(f"[📧 Открыть почтовый клиент]({mailto_link})")
        if email_handler and email_handler.connected:
            if st.button("📤 Отправить сейчас"):
                if email_handler.send_request_email(title, body):
                    st.success("Отправлено")
                else:
                    st.error("Ошибка отправки")
