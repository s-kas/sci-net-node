"""
Основная панель: список публикаций с цветовой схемой Google Scholar (как на скриншоте)
"""
import re
import streamlit as st
from typing import List, Dict, Any

CLEAN_TAG_RE = re.compile(r"<[^>]+>")
LINK_SCRIPT_RE = re.compile(r"(?i)(javascript:|data:|mailto:|href=)")

# Цвета из Google Scholar (светлый фон/grey/light blue/font/hover):
BG = "#fff"
TITLE_COLOR = "#174ea6"   # Google Scholar синий для заголовка
AUTHOR_COLOR = "#222"
META_COLOR = "#444"
DOI_COLOR = "#1a0dab"      # Google Scholar синий для ссылок
PDF_COLOR = "#0b8043"      # Google Scholar зеленый для PDF бейджа
HR_COLOR = "#e4e4e4"
BOX_COLOR = "#f8fafc"
INDEX_LABEL_COLOR = "#5f6368"
INDEX_VAL_COLOR = "#2d2d2d"


def _clean_text(v: Any) -> str:
    if v is None:
        return ""
    s = str(v)
    s = CLEAN_TAG_RE.sub(" ", s)
    s = LINK_SCRIPT_RE.sub("", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _clean_doi(doi: str) -> str:
    if not doi:
        return ""
    s = str(doi).strip()
    for pref in ["https://doi.org/", "http://doi.org/", "doi.org/", "DOI:", "doi:"]:
        s = s.replace(pref, "")
    return s.strip()

class MainPanel:
    def render(self, publications: List[Dict[str, Any]], email_handler=None):
        if not publications:
            st.info("📭 Нет публикаций для отображения")
            return
        st.markdown(f"""
        <style>
        .gs-pub-item {{ background:{BG}; padding:16px 12px 10px 12px; }}
        .gs-title {{ font-size:1.08rem; font-weight:600; color:{TITLE_COLOR}; margin-bottom:2px; margin-top:2px; line-height:1.38; }}
        .gs-authors  {{ color:{AUTHOR_COLOR}; font-size:0.95rem; margin-bottom:2px; }}
        .gs-meta, .gs-year {{ color:{META_COLOR}; font-size:0.96rem; display:inline;}}
        .gs-doi {{ color:{DOI_COLOR}; font-family:ui-monospace,Menlo,monospace; font-size:0.97rem; text-decoration:underline; }}
        .gs-pdf {{ color:{PDF_COLOR}; font-weight:700; font-size:0.96rem; margin-left:8px; }}
        hr.gs-hr {{border:0;height:1px;background:{HR_COLOR};margin:8px 0 10px 0;}}
        .gs-details {{background:{BOX_COLOR}; border:1px solid #e4e4e4; border-radius:8px;padding:13px 16px 9px 16px;}}
        .gs-index-label {{color:{INDEX_LABEL_COLOR}; font-size:0.97rem; font-weight:400;margin-top:3px;}}
        .gs-index-val {{color:{INDEX_VAL_COLOR}; font-size:0.98rem;}}
        .gs-arrow-btn {{background:none;border:none;color:#555;font-size:1.13rem;padding:0 8px;cursor:pointer;vertical-align:middle;}}
        .gs-arrow-btn:focus,.gs-arrow-btn:hover {{color:{TITLE_COLOR};}}
        </style>
        """, unsafe_allow_html=True)
        groups = self._group_by_doi(publications)
        st.header("📚 Найдено публикаций: " + str(len(groups)))
        first = True
        for doi, data in groups.items():
            if not first:
                st.markdown(f'<hr class="gs-hr" />', unsafe_allow_html=True)
            self._render_publication_row(doi, data)
            first = False
    def _group_by_doi(self, pubs: List[Dict[str, Any]]):
        groups: Dict[str, Dict[str, Any]] = {}
        for p in pubs:
            doi = _clean_doi(p.get("doi") or p.get("DO"))
            if not doi:
                continue
            g = groups.setdefault(doi, {"doi": doi, "titles":[], "years":[], "journals":[], "authors":[], "pdfs":[], "all_indices":{}})
            self._collect_indices(g["all_indices"], p)
            ti = _clean_text(p.get("title") or p.get("TI") or p.get("subject"))
            if ti:
                g["titles"].append(ti)
            jr = _clean_text(p.get("journal") or p.get("T2"))
            if jr:
                g["journals"].append(jr)
            py = _clean_text(p.get("year") or p.get("PY"))
            if py:
                g["years"].append(py)
            au = p.get("AU") or p.get("authors") or []
            if isinstance(au, str):
                au = [au]
            au = [_clean_text(a) for a in au if _clean_text(a)]
            g["authors"].extend(au)
            l1 = _clean_text(p.get("L1"))
            if l1:
                g["pdfs"].append(l1)
        for g in groups.values():
            for k in ("titles", "years", "journals", "authors", "pdfs"):
                seen = set(); uniq = []
                for v in g[k]:
                    if v not in seen:
                        uniq.append(v); seen.add(v)
                g[k] = uniq
        return groups
    def _collect_indices(self, acc: Dict[str, Any], p: Dict[str, Any]):
        for tag in ["DO","TI","M3","TY","PY","T2","VL","IS","SP","EP","AU","KW","DE","AB","N2","UR","L1","L2"]:
            val = p.get(tag) or p.get(tag.lower())
            if val is None:
                continue
            if isinstance(val, list):
                cleaned = [_clean_text(v) for v in val if _clean_text(v)]
            else:
                cleaned = [_clean_text(val)] if _clean_text(val) else []
            if not cleaned:
                continue
            acc.setdefault(tag, []).extend(cleaned)
    def _render_publication_row(self, doi: str, data: Dict[str, Any]):
        title = (data["titles"][0] if data["titles"] else "Без названия")
        authors = data["authors"]
        fa = authors[0] if authors else ""
        la = authors[-1] if len(authors)>1 else ""
        year = data["years"][-1] if data["years"] else ""
        journal = data["journals"][-1] if data["journals"] else ""
        has_pdf = bool(data["pdfs"])
        st.markdown('<div class="gs-pub-item">', unsafe_allow_html=True)
        st.markdown(f'<div class="gs-title">{title}</div>', unsafe_allow_html=True)
        meta1 = []
        if fa:
            meta1.append(_clean_text(fa))
        if la and la != fa:
            meta1.append("…")
            meta1.append(_clean_text(la))
        if journal:
            meta1.append(_clean_text(journal))
        authors_line = ' · '.join(meta1)
        if authors_line:
            st.markdown(f'<div class="gs-authors">{authors_line}</div>', unsafe_allow_html=True)
        meta2 = []
        if year:
            meta2.append(f'<span class="gs-year">{_clean_text(year)}</span>')
        meta2.append(f'DOI: <span class="gs-doi">{doi}</span>')
        if has_pdf:
            meta2.append('<span class="gs-pdf">PDF</span>')
        st.markdown('  ·  '.join(meta2), unsafe_allow_html=True)
        exp_key = f"exp_{doi}"; is_open = st.session_state.get(exp_key, False)
        arrow = "▲" if is_open else "▼"
        if st.button(arrow, key=f"btn_{doi}", help="Показать/скрыть индексы", type="secondary"):
            st.session_state[exp_key] = not is_open; is_open = not is_open
        if is_open:
            st.markdown('<div class="gs-details">', unsafe_allow_html=True)
            self._render_indices_table(data.get("all_indices", {}))
            st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    def _render_indices_table(self, idx: Dict[str, Any]):
        order = ["DO","TI","M3","TY","PY","T2","VL","IS","SP","EP","AU","KW","DE","AB","N2","UR","L1","L2"]
        any_output = False
        for tag in order:
            vals = list(dict.fromkeys(idx.get(tag, [])))
            if not vals:
                continue
            any_output = True
            st.markdown(f'<span class="gs-index-label">{tag}:</span>', unsafe_allow_html=True)
            for v in vals:
                st.markdown(f'<div class="gs-index-val">{_clean_text(v)}</div>', unsafe_allow_html=True)
        if not any_output:
            st.markdown("_Для этой публикации не найдено детальных индексов._")
