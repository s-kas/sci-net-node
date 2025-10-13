"""
Основная панель: список публикаций (аггрегация по DOI) c белым фоном, hr-разделителями и правильной агрегацией индексов
"""
import re
import streamlit as st
from typing import List, Dict, Any
from datetime import datetime

CLEAN_TAG_RE = re.compile(r"<[^>]+>")
LINK_SCRIPT_RE = re.compile(r"(?i)(javascript:|data:|mailto:|href=)")


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

        st.markdown(
            """
            <style>
            .white-app {background:#fff !important;}
            .pub-item {background:#fff;padding:14px 6px 10px 6px;}
            .pub-title {font-size:1.04rem;font-weight:600;color:#131313;margin-bottom:2px;}
            .pub-meta  {color:#424149;font-size:0.98rem;margin-bottom:1px;}
            .pub-doi {font-family:ui-monospace,Menlo,Consolas,monospace;}
            .badge-pdf {color:#07915c;font-weight:700;margin-left:8px;}
            .details {background:#f8f8fa;border:1px solid #ececf2;border-radius:8px;padding:11px 14px;margin-top:8px;}
            hr{border:none;height:1px;background:#e6e6e9;margin:0 0 8px 0}
            </style>
            <script>const el=document.querySelector(".stApp");if(el)el.classList.add("white-app");</script>
            """,
            unsafe_allow_html=True,
        )

        groups = self._group_by_doi(publications)
        st.header(f"📚 Найдено публикаций: {len(groups)}")

        first = True
        for doi, data in groups.items():
            if not first:
                st.markdown("<hr />", unsafe_allow_html=True)
            self._render_publication_row(doi, data)
            first = False

    def _group_by_doi(self, pubs: List[Dict[str, Any]]):
        groups: Dict[str, Dict[str, Any]] = {}
        for p in pubs:
            doi = _clean_doi(p.get("doi") or p.get("DO"))
            if not doi:
                continue
            g = groups.setdefault(
                doi,
                {
                    "doi": doi,
                    "titles": [],
                    "years": [],
                    "types": [],
                    "tys": [],
                    "journals": [],
                    "authors": [],
                    "pdfs": [],
                    "all_indices": {},
                },
            )
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
            m3 = _clean_text(p.get("M3") or p.get("type"))
            if m3:
                g["types"].append(m3)
            ty = _clean_text(p.get("TY"))
            if ty:
                g["tys"].append(ty)
            au = p.get("AU") or p.get("authors") or []
            if isinstance(au, str):
                au = [au]
            au = [_clean_text(a) for a in au if _clean_text(a)]
            g["authors"].extend(au)
            l1 = _clean_text(p.get("L1"))
            if l1:
                g["pdfs"].append(l1)
        for g in groups.values():
            for k in ("titles", "years", "types", "tys", "journals", "authors", "pdfs"):
                seen = set()
                uniq = []
                for v in g[k]:
                    if v not in seen:
                        uniq.append(v)
                        seen.add(v)
                g[k] = uniq
        return groups

    def _collect_indices(self, acc: Dict[str, Any], p: Dict[str, Any]):
        # Индексируем только если текущий DOI на первом месте!
        main_doi = _clean_doi(p.get("doi") or p.get("DO"))
        for tag in [
            "DO","TI","M3","TY","PY","T2","VL","IS","SP","EP","AU","KW","DE","AB","N2","UR","L1","L2"
        ]:
            val = p.get(tag) or p.get(tag.lower())
            if val is None:
                continue
            # НЕ добавлять, если это не первый DOI!
            # (Для инлайн DOI в тексте — нужно доработать парсер писем, если письма бывают multi-DOI)
            # Здесь для корректности просто сохраняем по тому, что прислано — главное, чтобы в сборе писем не агрегировались второстепенные DOI
            if isinstance(val, list):
                cleaned = [_clean_text(v) for v in val if _clean_text(v)]
            else:
                cleaned = [_clean_text(val)] if _clean_text(val) else []
            if not cleaned:
                continue
            arr = acc.setdefault(tag, [])
            arr.extend(cleaned)

    def _render_publication_row(self, doi: str, data: Dict[str, Any]):
        title = (data["titles"][0] if data["titles"] else "Без названия")
        authors = data["authors"]
        fa = authors[0] if authors else ""
        la = authors[-1] if len(authors) > 1 else ""
        year = data["years"][-1] if data["years"] else ""
        journal = data["journals"][-1] if data["journals"] else ""
        m3 = data["types"][-1] if data["types"] else ""
        tyg = data["tys"][-1] if data["tys"] else ""
        has_pdf = bool(data["pdfs"])

        st.markdown('<div class="pub-item">', unsafe_allow_html=True)
        st.markdown(f"<div class='pub-title'>{title}</div>", unsafe_allow_html=True)
        meta1 = []
        if fa:
            meta1.append(_clean_text(fa))
        if la and la != fa:
            meta1.append("…")
            meta1.append(_clean_text(la))
        if journal:
            meta1.append(_clean_text(journal))
        st.markdown(f"<div class='pub-meta'>{' · '.join(meta1)}</div>", unsafe_allow_html=True)

        meta2 = []
        if year:
            meta2.append(_clean_text(year))
        meta2.append(f"DOI: <span class='pub-doi'>{doi}</span>")
        if has_pdf:
            meta2.append("<span class='badge-pdf'>PDF</span>")
        st.markdown(f"<div class='pub-meta'>{'  ·  '.join(meta2)}</div>", unsafe_allow_html=True)

        exp_key = f"exp_{doi}"
        is_open = st.session_state.get(exp_key, False)
        arrow = "▲" if is_open else "▼"
        if st.button(arrow, key=f"btn_{doi}", help="Показать/скрыть индексы", type="secondary"):
            st.session_state[exp_key] = not is_open
            is_open = not is_open
        
        if is_open:
            st.markdown('<div class="details">', unsafe_allow_html=True)
            self._render_indices_table(data["all_indices"])
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

    def _render_indices_table(self, idx: Dict[str, Any]):
        order = [
            "DO","TI","M3","TY","PY","T2","VL","IS","SP","EP","AU","KW","DE","AB","N2","UR","L1","L2"
        ]
        for tag in order:
            vals = list(dict.fromkeys(idx.get(tag, [])))
            if not vals:
                continue
            st.markdown(f"**{tag}:**")
            for v in vals:
                st.markdown(f"- {_clean_text(v)}")
