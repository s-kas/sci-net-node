"""
Основная панель: улучшение отображения гиперссылок и добавление индексов CR/CITA.
- Скрытие HTML-скриптов, экранирование всего HTML, сохранение только реальных <a>
- Преобразование голых URL в кликабельные ссылки, как в письме
- Отображение кликабельной PDF-иконки только при наличии вложений
"""
import re
import streamlit as st
from typing import List, Dict, Any
from datetime import datetime
import base64
from html import escape

# Сохраняем только теги <a> и их содержимое, всё остальное экранируем
A_TAG_RE = re.compile(r"<a\b[^>]*>(.*?)</a>", re.IGNORECASE|re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")
URL_PATTERN = re.compile(r'(https?://[^\s<>"]+[^\s<>"\)\]\.,;:!\?])')

BG = "#fff"
TITLE_COLOR = "#1a1a1a"
AUTHOR_COLOR = "#333"
META_COLOR = "#555"
DOI_COLOR = "#1a0dab"
PDF_COLOR = "#0b8043"
HR_COLOR = "#e4e4e4"
BOX_COLOR = "#f8fafc"
INDEX_LABEL_COLOR = "#5f6368"
INDEX_VAL_COLOR = "#2d2d2d"


def _preserve_links_and_escape(text: str) -> str:
    """Экранирует HTML (включая скрипты/стили), но сохраняет реальные <a> ссылки как есть.
    Также превращает голые URL в ссылки.
    """
    if text is None:
        return ""
    s = str(text)

    # 1) Временно заменяем теги <a> на плейсхолдеры, чтобы не экранировать их
    placeholders = []
    def keep_anchor(m):
        placeholders.append(m.group(0))
        return f"@@A{len(placeholders)-1}@@"
    s_tmp = A_TAG_RE.sub(keep_anchor, s)

    # 2) Экранируем остальной HTML (скрываем «html-скрипты» и пр.)
    s_tmp = escape(s_tmp)

    # 3) Преобразуем голые URL в ссылки
    def url_to_link(m):
        url = m.group(1)
        return f'<a href="{url}" target="_blank">{url}</a>'
    s_tmp = URL_PATTERN.sub(url_to_link, s_tmp)

    # 4) Возвращаем сохранённые <a> теги на их места (как в письме)
    for i, ahtml in enumerate(placeholders):
        s_tmp = s_tmp.replace(f"@@A{i}@@", ahtml)

    return s_tmp


def _clean_doi(doi: str) -> str:
    if not doi:
        return ""
    s = str(doi).strip()
    for pref in ["https://doi.org/", "http://doi.org/", "doi.org/", "DOI:", "doi:"]:
        s = s.replace(pref, "")
    return s.strip()

def _create_pdf_download_link(pdf_data: str, filename: str) -> str:
    try:
        b64 = base64.b64encode(base64.b64decode(pdf_data)).decode()
        href = f'data:application/pdf;base64,{b64}'
        return f'<a href="{href}" download="{filename}" target="_blank" style="color:{PDF_COLOR};font-weight:700;text-decoration:none;margin-left:8px;">📄 PDF</a>'
    except Exception:
        return f'<span style="color:{PDF_COLOR};font-weight:700;margin-left:8px;">📄 PDF</span>'

class MainPanel:
    def render(self, publications: List[Dict[str, Any]], email_handler=None):
        if not publications:
            st.info("📭 Нет публикаций для отображения")
            return
        
        st.markdown(f"""
        <style>
        .gs-pub-item {{background:{BG}; padding:16px 12px 10px 12px; border-radius:8px; margin-bottom:12px; border:1px solid #e4e4e4;}}
        .gs-title {{font-size:1.08rem; font-weight:600; color:{TITLE_COLOR}; margin:2px 0; line-height:1.38;}}
        .gs-authors {{color:{AUTHOR_COLOR}; font-size:0.95rem; margin-bottom:2px;}}
        .gs-year, .gs-meta {{color:{META_COLOR}; font-size:0.96rem; display:inline;}}
        .gs-doi a {{color:{DOI_COLOR}; font-family:ui-monospace,Menlo,monospace; font-size:0.97rem; text-decoration:underline;}}
        .gs-details {{background:{BOX_COLOR}; border:1px solid #d0d7de; border-radius:8px; padding:13px 16px 12px 16px; margin:10px 0 8px;}}
        .gs-index-label {{color:{INDEX_LABEL_COLOR}; font-size:0.97rem; font-weight:600; margin-top:6px;}}
        .gs-index-val {{color:{INDEX_VAL_COLOR}; font-size:0.98rem;}}
        .gs-index-val a {{color:#1a0dab; text-decoration:underline;}}
        @media (prefers-color-scheme: dark) {{
            .gs-pub-item {{background:#1a1a1a; border:1px solid #404040; color:#e4e4e4;}}
            .gs-title {{color:#fff!important;}}
            .gs-authors {{color:#ccc!important;}}
            .gs-year, .gs-meta {{color:#999!important;}}
            .gs-details {{background:#2a2a2a; border:1px solid #505050;}}
            .gs-index-label {{color:#aaa!important;}}
            .gs-index-val {{color:#e4e4e4!important;}}
            .gs-index-val a {{color:#4fc3f7!important;}}
        }}
        </style>
        """, unsafe_allow_html=True)

        groups = self._group_by_doi(publications)
        st.header("📚 Найдено публикаций: " + str(len(groups)))

        first = True
        for doi, data in groups.items():
            if not first:
                st.markdown('<hr style="border:0;height:1px;background:#e4e4e4;margin:8px 0 10px"/>', unsafe_allow_html=True)
            self._render_publication_row(doi, data)
            first = False

    def _group_by_doi(self, pubs: List[Dict[str, Any]]):
        groups: Dict[str, Dict[str, Any]] = {}
        for p in pubs:
            doi = _clean_doi(p.get("doi") or p.get("DO"))
            if not doi:
                continue
            g = groups.setdefault(doi, {"doi": doi, "titles":[], "years":[], "journals":[], "authors":[], "pdf_attachments":[], "emails": []})
            if (t := p.get("title") or p.get("TI") or p.get("subject")):
                g["titles"].append(str(t))
            if (jr := p.get("journal") or p.get("T2")):
                g["journals"].append(str(jr))
            if (py := p.get("year") or p.get("PY")):
                g["years"].append(str(py))
            au = p.get("AU") or p.get("authors") or []
            if isinstance(au, str): au = [au]
            g["authors"].extend([str(a) for a in au if a])
            pdf_atts = p.get("pdf_attachments", [])
            if pdf_atts: g["pdf_attachments"].extend(pdf_atts)
            g["emails"].append({"date": p.get("date"), "order": len(g["emails"]), "raw": self._collect_raw_indices(p)})
        for g in groups.values():
            for k in ("titles","years","journals","authors"):
                seen=set(); uniq=[]
                for v in g[k]:
                    if v not in seen: uniq.append(v); seen.add(v)
                g[k]=uniq
        return groups

    def _collect_raw_indices(self, p: Dict[str, Any]) -> List[tuple[str,str]]:
        pairs = []
        for tag in ["DO","TI","M3","TY","PY","T2","VL","IS","SP","EP","AU","KW","DE","AB","N2","UR","L1","L2","CR","CITA"]:
            raw = p.get(tag) or p.get(tag.lower())
            if raw is None:
                continue
            if isinstance(raw, list):
                for v in raw:
                    val = _preserve_links_and_escape(v)
                    if val: pairs.append((tag, val))
            else:
                val = _preserve_links_and_escape(raw)
                if val: pairs.append((tag, val))
        return pairs

    def _render_publication_row(self, doi: str, data: Dict[str, Any]):
        title = (data["titles"][0] if data["titles"] else "Без названия")
        authors = data["authors"]
        fa = authors[0] if authors else ""; la = authors[-1] if len(authors)>1 else ""
        authors_part = fa + (", ... , " + la if la and la!=fa else "")
        journal = data["journals"][-1] if data["journals"] else ""
        year = data["years"][-1] if data["years"] else ""
        pdf_attachments = data.get("pdf_attachments", [])
        has_pdf = bool(pdf_attachments)

        st.markdown('<div class="gs-pub-item">', unsafe_allow_html=True)
        st.markdown(f'<div class="gs-title">{escape(title)}</div>', unsafe_allow_html=True)
        line = authors_part + ("  ·  " + journal if journal else "")
        if line:
            st.markdown(f'<div class="gs-authors">{escape(line)}</div>', unsafe_allow_html=True)

        meta = []
        if year: meta.append(f'<span class="gs-year">{escape(str(year))}</span>')
        meta.append(f'<span class="gs-doi"><a href="https://doi.org/{doi}" target="_blank">{doi}</a></span>')
        if has_pdf:
            first_pdf = pdf_attachments[0]
            meta.append(_create_pdf_download_link(first_pdf['data'], first_pdf['filename']))
        st.markdown('  ·  '.join(meta), unsafe_allow_html=True)

        exp_key = f"exp_{doi}"
        is_open = st.session_state.get(exp_key, False)
        arrow = "▲" if is_open else "▼"
        if st.button(arrow, key=f"btn_{doi}", help="Показать/скрыть детали публикации"):
            st.session_state[exp_key] = not is_open
            st.rerun()
        if st.session_state.get(exp_key, False):
            st.markdown('<div class="gs-details">', unsafe_allow_html=True)
            self._render_raw_details(data)
            st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    def _render_raw_details(self, data: Dict[str, Any]):
        emails = data.get("emails", [])
        def _key(e):
            d = e.get("date")
            try:
                if isinstance(d, str):
                    from dateutil import parser
                    d = parser.parse(d)
            except Exception:
                d = None
            return (d or datetime.min, -e.get("order", 0))
        emails_sorted = sorted(emails, key=_key, reverse=True)
        rows = []
        seen_values: Dict[str, set] = {}
        for e in emails_sorted:
            for tag, val in e.get("raw", []):
                if val not in seen_values:
                    seen_values[val] = {tag}
                    rows.append((tag, val))
                else:
                    seen_values[val].add(tag)
        printed = set()
        for tag, val in rows:
            if val in printed:
                continue
            printed.add(val)
            tags_joined = ",".join(sorted(seen_values.get(val, {tag})))
            st.markdown(
                f'<div><span class="gs-index-label">{tags_joined}:</span> '
                f'<span class="gs-index-val">{val}</span></div>',
                unsafe_allow_html=True
            )