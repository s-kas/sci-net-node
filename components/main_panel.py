"""
Основная панель: публикации с правками — формат авторов, DOI как ссылка, детальная панель с упорядочиванием и объединением значений
"""
import re
import streamlit as st
from typing import List, Dict, Any
from datetime import datetime

CLEAN_TAG_RE = re.compile(r"<[^>]+>")
LINK_SCRIPT_RE = re.compile(r"(?i)(javascript:)")  # допускаем href/mailto в деталях

BG = "#fff"
TITLE_COLOR = "#174ea6"
AUTHOR_COLOR = "#222"
META_COLOR = "#444"
DOI_COLOR = "#1a0dab"
PDF_COLOR = "#0b8043"
HR_COLOR = "#e4e4e4"
BOX_COLOR = "#f8fafc"
INDEX_LABEL_COLOR = "#5f6368"
INDEX_VAL_COLOR = "#2d2d2d"


def _clean_text(v: Any, strip_links: bool = True) -> str:
    if v is None:
        return ""
    s = str(v)
    s = CLEAN_TAG_RE.sub(" ", s)
    if strip_links:
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
        .gs-doi a {{ color:{DOI_COLOR}; font-family:ui-monospace,Menlo,monospace; font-size:0.97rem; text-decoration:underline; }}
        .gs-pdf {{ color:{PDF_COLOR}; font-weight:700; font-size:0.96rem; margin-left:8px; }}
        hr.gs-hr {{border:0;height:1px;background:{HR_COLOR};margin:8px 0 10px 0;}}
        .gs-details {{background:{BOX_COLOR}; border:1px solid #e4e4e4; border-radius:8px;padding:13px 16px 9px 16px;}}
        .gs-index-label {{color:{INDEX_LABEL_COLOR}; font-size:0.97rem; font-weight:600;margin-top:6px;}}
        .gs-index-val {{color:{INDEX_VAL_COLOR}; font-size:0.98rem;}}
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
            g = groups.setdefault(doi, {
                "doi": doi,
                "titles":[], "years":[], "journals":[], "authors":[], "pdfs":[],
                "all_indices": {},
                "emails": []
            })
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
            g["emails"].append({
                "date": p.get("date"),
                "order": len(g["emails"]),
                "indices": self._collect_indices_ordered(p)
            })
        # уникализация
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

    def _collect_indices_ordered(self, p: Dict[str, Any]) -> Dict[str, list]:
        # Возвращает индексы ровно в том порядке, как в письме (по ключам), без удаления ссылок (сохраняем href/mailto)
        ordered: Dict[str, list] = {}
        for tag in ["DO","TI","M3","TY","PY","T2","VL","IS","SP","EP","AU","KW","DE","AB","N2","UR","L1","L2"]:
            raw = p.get(tag) or p.get(tag.lower())
            if raw is None: 
                continue
            if isinstance(raw, list):
                cleaned = [_clean_text(v, strip_links=False) for v in raw if _clean_text(v, strip_links=False)]
            else:
                cleaned = [_clean_text(raw, strip_links=False)] if _clean_text(raw, strip_links=False) else []
            if cleaned:
                ordered[tag] = cleaned
        return ordered

    def _render_publication_row(self, doi: str, data: Dict[str, Any]):
        title = (data["titles"][0] if data["titles"] else "Без названия")
        authors = data["authors"]
        fa = authors[0] if authors else ""; la = authors[-1] if len(authors)>1 else ""
        # формат: Первый Автор, ..., Последний Автор  ·  Журнал
        authors_part = ", ... , ".join([fa, la]) if (fa and la and la!=fa) else fa
        journal = data["journals"][-1] if data["journals"] else ""
        year = data["years"][-1] if data["years"] else ""
        has_pdf = bool(data["pdfs"]) 

        st.markdown('<div class="gs-pub-item">', unsafe_allow_html=True)
        st.markdown(f'<div class="gs-title">{title}</div>', unsafe_allow_html=True)

        left = authors_part
        right = journal
        line = left + ("  ·  " + right if right else "")
        if line:
            st.markdown(f'<div class="gs-authors">{line}</div>', unsafe_allow_html=True)

        meta2 = []
        if year:
            meta2.append(f'<span class="gs-year">{year}</span>')
        meta2.append(f'<span class="gs-doi"><a href="https://doi.org/{doi}" target="_blank">https://doi.org/{doi}</a></span>')
        if has_pdf:
            meta2.append('<span class="gs-pdf">PDF</span>')
        st.markdown('  ·  '.join(meta2), unsafe_allow_html=True)

        exp_key = f"exp_{doi}"; is_open = st.session_state.get(exp_key, False)
        arrow = "▲" if is_open else "▼"
        if st.button(arrow, key=f"btn_{doi}", help="Показать/скрыть индексы", type="secondary"):
            st.session_state[exp_key] = not is_open; is_open = not is_open
        if is_open:
            st.markdown('<div class="gs-details">', unsafe_allow_html=True)
            self._render_indices_table_merged_ordered(data)
            st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    def _render_indices_table_merged_ordered(self, data: Dict[str, Any]):
        # Слияние значений с одинаковым текстом в одну строку; сортировка писем по дате (desc), затем по порядку появления
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

        # накапливаем пары (TAG, VALUE) в порядке писем и их тел
        pairs: list[tuple[str,str]] = []
        for e in emails_sorted:
            indices = e.get("indices", {})
            for tag in ["DO","TI","M3","TY","PY","T2","VL","IS","SP","EP","AU","KW","DE","AB","N2","UR","L1","L2"]:
                vals = indices.get(tag, [])
                for v in vals:
                    pairs.append((tag, v))

        if not pairs:
            st.markdown("_Для этой публикации не найдено детальных индексов._")
            return

        # Объединяем одинаковые значения в одну строку (независимо от тега), но сохраняем первый встретившийся тег как метку
        seen: Dict[str, list[str]] = {}
        tag_label: Dict[str, str] = {}
        for tag, val in pairs:
            key = val.strip()
            if key not in seen:
                seen[key] = [tag]
                tag_label[key] = tag
            else:
                if tag not in seen[key]:
                    seen[key].append(tag)

        # Выводим построчно в накопленном порядке
        for tag, val in pairs:
            key = val.strip()
            if key not in tag_label:
                continue
            label = tag_label.pop(key)  # печатаем только один раз
            tags_joined = ",".join(seen[key])
            # если значение похоже на ссылку, оставляем как есть (href/mailto сохранялись ранее)
            if re.search(r"https?://|mailto:", val, flags=re.I):
                value_html = val
            else:
                value_html = _clean_text(val, strip_links=False)
            st.markdown(f'<div><span class="gs-index-label">{label} ({tags_joined}):</span> <span class="gs-index-val">{value_html}</span></div>', unsafe_allow_html=True)
