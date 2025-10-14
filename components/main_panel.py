"""
Основная панель: исправление логики кнопки и отображения индексов внутри серого блока.
- Надёжное переключение стрелки по состоянию exp_key
- Отрисовка деталей строго внутри панели
- Сохранение HTML ссылок в значениях индексов
- Поддержка кликабельных PDF вложений
"""
import re
import streamlit as st
from typing import List, Dict, Any
from datetime import datetime
import base64

CLEAN_TAG_RE = re.compile(r"<(?!/?a\b)[^>]+>")  # Сохраняем только теги <a>
LINK_SCRIPT_RE = re.compile(r"(?i)(javascript:)" )
URL_PATTERN = re.compile(r'https?://[^\s<>"]+[^\s<>".!?)]')

BG = "#fff"
TITLE_COLOR = "#1a1a1a"  # Темнее для лучшей читаемости
AUTHOR_COLOR = "#333"
META_COLOR = "#555"
DOI_COLOR = "#1a0dab"
PDF_COLOR = "#0b8043"
HR_COLOR = "#e4e4e4"
BOX_COLOR = "#f8fafc"
INDEX_LABEL_COLOR = "#5f6368"
INDEX_VAL_COLOR = "#2d2d2d"


def _clean_text(v: Any, strip_links: bool = False) -> str:
    """Очистка текста с опциональным сохранением ссылок"""
    if v is None:
        return ""
    s = str(v)
    if strip_links:
        s = CLEAN_TAG_RE.sub(" ", s)
        s = LINK_SCRIPT_RE.sub("", s)
    else:
        # Удаляем все теги кроме ссылок <a>
        s = re.sub(r'<(?!/?a\b)[^>]*>', ' ', s)
    return s.strip()


def _convert_urls_to_links(text: str) -> str:
    """Преобразование URL-ов в кликабельные ссылки"""
    if not text:
        return text
        
    def replace_url(match):
        url = match.group(0)
        # Проверяем, не находится ли URL уже внутри тега <a>
        if '<a ' in text[:match.start()] and '</a>' in text[match.end():]:
            return url  # Уже в ссылке
        return f'<a href="{url}" target="_blank">{url}</a>'
    
    return URL_PATTERN.sub(replace_url, text)


def _clean_doi(doi: str) -> str:
    if not doi:
        return ""
    s = str(doi).strip()
    for pref in ["https://doi.org/", "http://doi.org/", "doi.org/", "DOI:", "doi:"]:
        s = s.replace(pref, "")
    return s.strip()

def _create_pdf_download_link(pdf_data: str, filename: str) -> str:
    """Создание ссылки для скачивания PDF"""
    try:
        b64 = base64.b64encode(base64.b64decode(pdf_data)).decode()
        href = f'data:application/pdf;base64,{b64}'
        return f'<a href="{href}" download="{filename}" target="_blank" style="color:{PDF_COLOR};font-weight:700;text-decoration:none;margin-left:8px;">📄 PDF</a>'
    except:
        return f'<span style="color:{PDF_COLOR};font-weight:700;margin-left:8px;">📄 PDF</span>'

class MainPanel:
    def render(self, publications: List[Dict[str, Any]], email_handler=None):
        if not publications:
            st.info("📭 Нет публикаций для отображения")
            return
        
        st.markdown(f"""
        <style>
        .gs-pub-item {{ 
            background:{BG}; 
            padding:16px 12px 10px 12px; 
            border-radius:8px; 
            margin-bottom:12px; 
            border: 1px solid #e4e4e4;
        }}
        .gs-title {{ 
            font-size:1.08rem; 
            font-weight:600; 
            color:{TITLE_COLOR}; 
            margin-bottom:2px; 
            margin-top:2px; 
            line-height:1.38; 
        }}
        .gs-authors {{ 
            color:{AUTHOR_COLOR}; 
            font-size:0.95rem; 
            margin-bottom:2px; 
        }}
        .gs-meta, .gs-year {{ 
            color:{META_COLOR}; 
            font-size:0.96rem; 
            display:inline;
        }}
        .gs-doi a {{ 
            color:{DOI_COLOR}; 
            font-family:ui-monospace,Menlo,monospace; 
            font-size:0.97rem; 
            text-decoration:underline; 
        }}
        .gs-pdf {{ 
            color:{PDF_COLOR}; 
            font-weight:700; 
            font-size:0.96rem; 
            margin-left:8px; 
        }}
        .gs-pdf a {{
            color:{PDF_COLOR};
            text-decoration:none;
        }}
        .gs-pdf a:hover {{
            text-decoration:underline;
        }}
        hr.gs-hr {{
            border:0;
            height:1px;
            background:{HR_COLOR};
            margin:8px 0 10px 0;
        }}
        .gs-details {{
            background:{BOX_COLOR}; 
            border:1px solid #d0d7de; 
            border-radius:8px;
            padding:13px 16px 12px 16px;
            margin-top:10px;
            margin-bottom:8px;
        }}
        .gs-index-label {{
            color:{INDEX_LABEL_COLOR}; 
            font-size:0.97rem; 
            font-weight:600;
            margin-top:6px;
        }}
        .gs-index-val {{
            color:{INDEX_VAL_COLOR}; 
            font-size:0.98rem;
        }}
        .gs-index-val a {{
            color:#1a0dab;
            text-decoration:underline;
        }}
        .gs-arrow-btn {{
            background:#eef2f7;
            border:1px solid #dbe2ea;
            border-radius:8px;
            color:#333;
            padding:2px 10px; 
            min-width:40px; 
            text-align:center;
        }}
        .gs-arrow-btn:hover {{
            background:#e6ebf2
        }}
        
        /* Улучшение контрастности для темной темы */
        @media (prefers-color-scheme: dark) {{
            .gs-pub-item {{
                background: #1a1a1a;
                border: 1px solid #404040;
                color: #e4e4e4;
            }}
            .gs-title {{
                color: #ffffff !important;
            }}
            .gs-authors {{
                color: #cccccc !important;
            }}
            .gs-meta, .gs-year {{
                color: #999999 !important;
            }}
            .gs-details {{
                background: #2a2a2a;
                border: 1px solid #505050;
            }}
            .gs-index-label {{
                color: #aaaaaa !important;
            }}
            .gs-index-val {{
                color: #e4e4e4 !important;
            }}
            .gs-index-val a {{
                color: #4fc3f7 !important;
            }}
        }}
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
                "pdf_attachments": [],  # Добавляем PDF вложения
                "emails": []
            })
            ti = _clean_text(p.get("title") or p.get("TI") or p.get("subject"), strip_links=True)
            if ti: g["titles"].append(ti)
            jr = _clean_text(p.get("journal") or p.get("T2"), strip_links=True)
            if jr: g["journals"].append(jr)
            py = _clean_text(p.get("year") or p.get("PY"), strip_links=True)
            if py: g["years"].append(py)
            au = p.get("AU") or p.get("authors") or []
            if isinstance(au, str): au = [au]
            au = [_clean_text(a, strip_links=True) for a in au if _clean_text(a, strip_links=True)]
            g["authors"].extend(au)
            l1 = _clean_text(p.get("L1"), strip_links=True)
            if l1: g["pdfs"].append(l1)
            
            # Добавляем PDF вложения
            pdf_attachments = p.get("pdf_attachments", [])
            if pdf_attachments:
                g["pdf_attachments"].extend(pdf_attachments)
            
            g["emails"].append({
                "date": p.get("date"),
                "order": len(g["emails"]),
                "raw": self._collect_raw_indices(p)
            })
        
        for g in groups.values():
            for k in ("titles", "years", "journals", "authors", "pdfs"):
                seen=set(); uniq=[]
                for v in g[k]:
                    if v not in seen: uniq.append(v); seen.add(v)
                g[k]=uniq
        return groups

    def _collect_raw_indices(self, p: Dict[str, Any]) -> list[tuple[str,str]]:
        """Сбор всех RIS индексов без обработки (сохраняя HTML ссылки)"""
        pairs = []
        for tag in ["DO","TI","M3","TY","PY","T2","VL","IS","SP","EP","AU","KW","DE","AB","N2","UR","L1","L2"]:
            raw = p.get(tag) or p.get(tag.lower())
            if raw is None: continue
            if isinstance(raw, list):
                for v in raw:
                    val = _clean_text(v, strip_links=False)  # Сохраняем ссылки
                    val = _convert_urls_to_links(val)  # Преобразуем URL в ссылки
                    if val: pairs.append((tag, val))
            else:
                val = _clean_text(raw, strip_links=False)  # Сохраняем ссылки
                val = _convert_urls_to_links(val)  # Преобразуем URL в ссылки
                if val: pairs.append((tag, val))
        return pairs

    def _render_publication_row(self, doi: str, data: Dict[str, Any]):
        """Отображение строки публикации с раскрывающимися деталями"""
        title = (data["titles"][0] if data["titles"] else "Без названия")
        authors = data["authors"]
        fa = authors[0] if authors else ""; la = authors[-1] if len(authors)>1 else ""
        authors_part = fa + (", ... , " + la if la and la!=fa else "")
        journal = data["journals"][-1] if data["journals"] else ""
        year = data["years"][-1] if data["years"] else ""
        
        # Проверяем наличие PDF вложений
        pdf_attachments = data.get("pdf_attachments", [])
        has_pdf = bool(pdf_attachments)

        # Контейнер для всей публикации
        st.markdown('<div class="gs-pub-item">', unsafe_allow_html=True)
        
        st.markdown(f'<div class="gs-title">{title}</div>', unsafe_allow_html=True)
        line = authors_part + ("  ·  " + journal if journal else "")
        if line: st.markdown(f'<div class="gs-authors">{line}</div>', unsafe_allow_html=True)

        meta2 = []
        if year: meta2.append(f'<span class="gs-year">{year}</span>')
        meta2.append(f'<span class="gs-doi"><a href="https://doi.org/{doi}" target="_blank">{doi}</a></span>')
        
        # Отображаем кликабельную PDF иконку только если есть вложения
        if has_pdf and pdf_attachments:
            # Берем первое PDF вложение
            first_pdf = pdf_attachments[0]
            pdf_link = _create_pdf_download_link(first_pdf['data'], first_pdf['filename'])
            meta2.append(pdf_link)
        
        st.markdown('  ·  '.join(meta2), unsafe_allow_html=True)

        exp_key = f"exp_{doi}"
        is_open = st.session_state.get(exp_key, False)
        # ИСПРАВЛЕНО: правильное направление стрелки
        arrow = "▲" if is_open else "▼"  # ▼ когда закрыто (показать детали), ▲ когда открыто (скрыть детали)
        
        if st.button(arrow, key=f"btn_{doi}", help="Показать/скрыть детали публикации"):
            st.session_state[exp_key] = not is_open
            st.rerun()
            
        # ИСПРАВЛЕНО: Отображение деталей ВНУТРИ блока публикации
        if st.session_state.get(exp_key, False):
            st.markdown('<div class="gs-details">', unsafe_allow_html=True)
            self._render_raw_details(data)
            st.markdown('</div>', unsafe_allow_html=True)
            
        # Закрытие контейнера публикации
        st.markdown('</div>', unsafe_allow_html=True)

    def _render_raw_details(self, data: Dict[str, Any]):
        """Отображение необработанных деталей индексов из всех писем"""
        emails = data.get("emails", [])
        
        # Сортировка писем по дате (новые сначала)
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
        seen_values: dict[str, set[str]] = {}
        
        # Сбор всех уникальных значений с тегами
        for e in emails_sorted:
            for tag, val in e.get("raw", []):
                if val not in seen_values:
                    seen_values[val] = {tag}
                    rows.append((tag, val))
                else:
                    seen_values[val].add(tag)
        
        # Отображение индексов с сохранением HTML ссылок
        printed = set()
        for tag, val in rows:
            if val in printed: 
                continue
            printed.add(val)
            tags_joined = ",".join(sorted(seen_values.get(val, {tag})))
            # Используем unsafe_allow_html=True для отображения HTML ссылок
            st.markdown(
                f'<div><span class="gs-index-label">{tags_joined}:</span> '
                f'<span class="gs-index-val">{val}</span></div>', 
                unsafe_allow_html=True
            )
            
        # Отображаем информацию о PDF вложениях если есть
        pdf_attachments = data.get("pdf_attachments", [])
        if pdf_attachments:
            st.markdown('<div style="margin-top:12px;"><span class="gs-index-label">PDF вложения:</span></div>', unsafe_allow_html=True)
            for pdf in pdf_attachments:
                pdf_link = _create_pdf_download_link(pdf['data'], pdf['filename'])
                size_mb = round(pdf['size'] / (1024*1024), 2)
                st.markdown(
                    f'<div style="margin-left:20px;"><span class="gs-index-val">{pdf["filename"]} ({size_mb} MB) {pdf_link}</span></div>',
                    unsafe_allow_html=True
                )