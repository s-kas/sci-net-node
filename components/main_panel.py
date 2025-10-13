"""
Основная панель: список публикаций (аггрегация по DOI) в стиле Google Scholar/журнального TOC
- Шапка строки: Заголовок, авторы (сокращённо), год, журнал, DOI, индикатор PDF (если L1 есть)
- Кнопка стрелка ▼/▲ для раскрытия сводных индексов из всех писем этой публикации (без скриптов ссылок)
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
            .pub-item {border-top:1px solid #e6e6e9; padding:14px 6px; background:#fff;}
            .pub-head {display:flex; align-items:flex-start; gap:10px;}
            .pub-title {font-size:1.02rem; font-weight:600; color:#111;}
            .pub-meta  {color:#4a4f56; font-size:0.95rem;}
            .pub-doi {font-family:ui-monospace,Menlo,Consolas,monospace;}
            .pub-aux {display:flex; gap:14px; align-items:center; margin-top:6px;}
            .exp-btn {background:none; border:none; cursor:pointer; font-size:1.1rem; color:#4a4f56;}
            .exp-btn:hover {color:#111}
            .details {background:#f4f5f7; border:1px solid #e4e5ea; border-radius:8px; padding:10px 12px; margin-top:8px;}
            .badge-pdf {color:#07915c; font-weight:700; margin-left:8px;}
            </style>
            """,
            unsafe_allow_html=True,
        )

        # Группировка по DOI с агрегацией индексов из всех писем
        groups = self._group_by_doi(publications)
        st.header(f"📚 Найдено публикаций: {len(groups)}")

        for doi, data in groups.items():
            self._render_publication_row(doi, data)

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
                    "emails": [],
                    "pdfs": [],
                    "all_indices": {},
                },
            )
            # Копим все индексы
            self._collect_indices(g["all_indices"], p)

            # Заголовок/журнал/год/тип
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
            # Авторы (список)
            au = p.get("AU") or p.get("authors") or []
            if isinstance(au, str):
                au = [au]
            au = [_clean_text(a) for a in au if _clean_text(a)]
            g["authors"].extend(au)
            # PDF
            l1 = _clean_text(p.get("L1"))
            if l1:
                g["pdfs"].append(l1)
            # Emails list for details
            g["emails"].append(
                {
                    "folder": p.get("folder", ""),
                    "from": p.get("from", ""),
                    "subject": _clean_text(p.get("subject", "")),
                    "date": p.get("date", ""),
                }
            )

        # Нормализация списков
        for g in groups.values():
            for k in ("titles", "years", "types", "tys", "journals", "authors", "pdfs"):
                # сохраняем порядок появления, удаляя дубликаты
                seen = set()
                uniq = []
                for v in g[k]:
                    if v not in seen:
                        uniq.append(v)
                        seen.add(v)
                g[k] = uniq
        return groups

    def _collect_indices(self, acc: Dict[str, Any], p: Dict[str, Any]):
        # Берём индексы из письма, чистим, добавляем в массивы
        for tag in [
            "DO","TI","M3","TY","PY","T2","VL","IS","SP","EP","AU","KW","DE","AB","N2","UR","L1","L2"
        ]:
            val = p.get(tag) or p.get(tag.lower())
            if val is None:
                continue
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
        # Авторы: показать коротко X … , Y (первый и последний)
        authors = data["authors"]
        fa = authors[0] if authors else ""
        la = authors[-1] if len(authors) > 1 else ""
        year = data["years"][-1] if data["years"] else ""
        journal = data["journals"][-1] if data["journals"] else ""
        m3 = data["types"][-1] if data["types"] else ""
        tyg = data["tys"][-1] if data["tys"] else ""
        typeline = m3 or tyg or ""
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

        # Кнопка стрелки ▼/▲
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
        # Показать все встреченные значения индексов по письмам (без скриптов ссылок)
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
