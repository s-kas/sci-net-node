"""
Основная панель: добавлены чекбоксы выбора публикаций (включены по умолчанию), общий чекбокс "Все выбраны" и меню действий (три полоски) с опцией выгрузки RIS.
Выгружается txt только по выбранным публикациям: индексы и значения, исключая значения в квадратных скобках и html-скрипты.
"""
import re
import streamlit as st
from typing import List, Dict, Any
from datetime import datetime
import base64
from html import escape

BG = "#fff"; TITLE_COLOR = "#1a1a1a"; AUTHOR_COLOR = "#333"; META_COLOR = "#555"; DOI_COLOR = "#1a0dab"; PDF_COLOR = "#0b8043"; HR_COLOR = "#e4e4e4"; BOX_COLOR = "#f8fafc"; INDEX_LABEL_COLOR = "#5f6368"; INDEX_VAL_COLOR = "#2d2d2d"

HREF_PREFIX = 'href='

EXCLUDE_BRACKET_VALUE_RE = re.compile(r"\[[^\]]*\]")
STRIP_HTML_TAGS_RE = re.compile(r"<[^>]+>")


def _add_anchor_prefix(text: str) -> str:
    if text is None:
        return ""
    s = str(text)
    s = s.replace(HREF_PREFIX, '<a href=')
    s = s.replace(']', ']</a>')
    return s


def _clean_doi(doi: str) -> str:
    if not doi: return ""
    s = str(doi).strip()
    for pref in ("https://doi.org/","http://doi.org/","doi.org/","DOI:","doi:"):
        s = s.replace(pref, "")
    return s.strip()


def _pdf_link(pdf_data: str, filename: str) -> str:
    try:
        b64 = base64.b64encode(base64.b64decode(pdf_data)).decode()
        return f'<a href="data:application/pdf;base64,{b64}" download="{escape(filename)}" target="_blank" style="color:{PDF_COLOR};font-weight:700;text-decoration:none;margin-left:8px;">📄 PDF</a>'
    except Exception:
        return f'<span style="color:{PDF_COLOR};font-weight:700;margin-left:8px;">📄 PDF</span>'

class MainPanel:
    def render(self, publications: List[Dict[str, Any]], email_handler=None):
        if not publications:
            st.info("📭 Нет публикаций для отображения"); return

        # Инициализация состояния выбранности
        if 'select_all' not in st.session_state:
            st.session_state.select_all = True
        if 'selected_pubs' not in st.session_state:
            st.session_state.selected_pubs = {}

        # Верхняя панель: чекбокс "Все выбраны" и кнопка меню (три полоски)
        top_cols = st.columns([0.08, 0.74, 0.18])
        with top_cols[0]:
            all_checked = st.checkbox("", value=st.session_state.select_all, key="master_cb", help="Все выбраны")
        with top_cols[1]:
            st.markdown(f"<h2 style='margin:0'>Найдено публикаций: {len(publications)}</h2>", unsafe_allow_html=True)
        with top_cols[2]:
            action = st.popover("≡", use_container_width=True)
            with action:
                st.markdown("### Действия")
                if st.button("Выгрузить все RIS в .txt", use_container_width=True):
                    self._export_ris_txt(publications)

        # Логика синхронизации master -> items
        if all_checked != st.session_state.select_all:
            st.session_state.select_all = all_checked
            # Обновить все чекбоксы
            for doi in self._doi_order(publications):
                st.session_state.selected_pubs[doi] = all_checked

        # Отрисовка карточек с чекбоксами слева
        for i, (doi, data) in enumerate(self._group_by_doi(publications).items()):
            if doi not in st.session_state.selected_pubs:
                st.session_state.selected_pubs[doi] = True

            row_cols = st.columns([0.06, 0.94])
            with row_cols[0]:
                val = st.checkbox("", value=st.session_state.selected_pubs[doi], key=f"cb_{doi}")
                # Если пользователь изменил чекбокс
                if val != st.session_state.selected_pubs[doi]:
                    st.session_state.selected_pubs[doi] = val
            with row_cols[1]:
                self._row(doi, data)

        # Логика items -> master
        values = list(st.session_state.selected_pubs.values())
        if values and all(values):
            st.session_state.select_all = True
        elif any(v is False for v in values):
            st.session_state.select_all = False

        # Обновить видимое состояние master чекбокса
        st.session_state["master_cb"] = st.session_state.select_all

    def _doi_order(self, pubs: List[Dict[str, Any]]):
        order = []
        for p in pubs:
            doi = _clean_doi(p.get('doi') or p.get('DO'))
            if doi: order.append(doi)
        return order

    def _group_by_doi(self, pubs: List[Dict[str, Any]]):
        groups: Dict[str, Dict[str, Any]] = {}
        for p in pubs:
            doi = _clean_doi(p.get('doi') or p.get('DO'))
            if not doi: continue
            g = groups.setdefault(doi, {"doi":doi, "titles":[], "years":[], "journals":[], "authors":[], "pdf_attachments":[], "emails":[]})
            if (t:=p.get('title') or p.get('TI') or p.get('subject')): g['titles'].append(str(t))
            if (jr:=p.get('journal') or p.get('T2')): g['journals'].append(str(jr))
            if (py:=p.get('year') or p.get('PY')): g['years'].append(str(py))
            au=p.get('AU') or p.get('authors') or []; au=[au] if isinstance(au,str) else au
            g['authors'].extend([str(a) for a in au if a])
            if p.get('pdf_attachments'): g['pdf_attachments'].extend(p['pdf_attachments'])
            g['emails'].append({"date":p.get('date'),"order":len(g['emails']),"raw":self._collect_raw_indices(p)})
        for g in groups.values():
            for k in ('titles','years','journals','authors'):
                seen=set(); uniq=[]
                for v in g[k]:
                    if v not in seen: uniq.append(v); seen.add(v)
                g[k]=uniq
        return groups

    def _collect_raw_indices(self, p: Dict[str, Any]) -> List[tuple[str,str]]:
        pairs=[]
        for tag in ["DO","TI","M3","TY","PY","T2","VL","IS","SP","EP","AU","KW","DE","AB","N2","UR","L1","L2","CR","CITA"]:
            raw = p.get(tag) or p.get(tag.lower())
            if raw is None: continue
            vals = raw if isinstance(raw,list) else [raw]
            for v in vals:
                s = _add_anchor_prefix(str(v))
                pairs.append((tag,s))
        return pairs

    def _row(self, doi:str, data:Dict[str,Any]):
        title = (data['titles'][0] if data['titles'] else 'Без названия')
        authors=data['authors']; fa=authors[0] if authors else ''; la=authors[-1] if len(authors)>1 else ''
        line = fa + (", ... , "+la if la and la!=fa else '')
        journal = data['journals'][-1] if data['journals'] else ''
        year = data['years'][-1] if data['years'] else ''
        pdf_attachments = data.get('pdf_attachments', [])
        st.markdown('<div class="gs-pub-item">', unsafe_allow_html=True)
        st.markdown(f'<div class="gs-title">{escape(title)}</div>', unsafe_allow_html=True)
        if line or journal:
            st.markdown(f'<div class="gs-authors">{escape(line + ("  ·  "+journal if journal else ""))}</div>', unsafe_allow_html=True)
        meta=[]
        if year: meta.append(f'<span class="gs-year">{escape(str(year))}</span>')
        meta.append(f'<span class="gs-doi"><a href="https://doi.org/{doi}" target="_blank">{doi}</a></span>')
        if pdf_attachments:
            meta.append(_pdf_link(pdf_attachments[0]['data'], pdf_attachments[0]['filename']))
        st.markdown('  ·  '.join(meta), unsafe_allow_html=True)
        exp_key=f'exp_{doi}'; is_open=st.session_state.get(exp_key, False)
        if st.button('▲' if is_open else '▼', key=f'btn_{doi}', help='Показать/скрыть детали публикации'):
            st.session_state[exp_key]=not is_open; st.rerun()
        if st.session_state.get(exp_key, False):
            st.markdown('<div class="gs-details">', unsafe_allow_html=True)
            self._details(data)
            st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    def _details(self, data:Dict[str,Any]):
        emails=data.get('emails', [])
        def _key(e):
            d=e.get('date')
            try:
                if isinstance(d,str):
                    from dateutil import parser; d=parser.parse(d)
            except Exception: d=None
            return (d or datetime.min, -e.get('order',0))
        emails_sorted=sorted(emails, key=_key, reverse=True)
        rows=[]; seen:Dict[str,set]={}
        for e in emails_sorted:
            for tag,val in e.get('raw', []):
                if val not in seen: seen[val]={tag}; rows.append((tag,val))
                else: seen[val].add(tag)
        printed=set()
        for tag,val in rows:
            if val in printed: continue
            printed.add(val)
            tags=",".join(sorted(seen.get(val,{tag})))
            st.markdown(f'<div><span class="gs-index-label">{tags} - </span><span class="gs-index-val">{val}</span></div>', unsafe_allow_html=True)

    def _export_ris_txt(self, pubs: List[Dict[str, Any]]):
        # Фильтруем только выбранные публикации
        selected = {doi for doi, v in st.session_state.selected_pubs.items() if v}
        if not selected:
            st.warning("Не выбрано ни одной публикации для выгрузки")
            return
        groups = self._group_by_doi(pubs)
        lines = []
        for doi, data in groups.items():
            if doi not in selected:
                continue
            # Собираем все пары из emails.raw
            all_pairs = []
            for e in data.get('emails', []):
                all_pairs.extend(e.get('raw', []))
            # Уникальные строки по порядку появления
            seen = set()
            for tag, val in all_pairs:
                # Исключаем значения в квадратных скобках и html-скрипты
                if EXCLUDE_BRACKET_VALUE_RE.search(val):
                    continue
                # Удаляем html теги целиком
                clean = STRIP_HTML_TAGS_RE.sub('', val)
                clean = clean.strip()
                if not clean:
                    continue
                line = f"{tag}  - {clean}"
                if line not in seen:
                    seen.add(line)
                    lines.append(line)
            # Разделитель между публикациями
            lines.append("ER  -")
        content = "\n".join(lines)
        st.download_button("Скачать RIS .txt", data=content, file_name="export_ris.txt", mime="text/plain")
