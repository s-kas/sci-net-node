"""
Основная панель: карточки писем после фильтров, стиль оглавления журнала, раскр. по кнопке Подробнее, очистка HTML
"""
import re
import streamlit as st
from typing import List, Dict, Any
from datetime import datetime
from config import REQUEST_PATTERNS, SCINET_CORE_EMAIL
import urllib.parse

CLEAN_TAG_RE = re.compile(r"<[^>]+>")
MAILTO_RE = re.compile(r"^(mailto:|href=)", re.IGNORECASE)
BRACKETS_RE = re.compile(r"^\s*\[.*\]\s*$")

def clean_val(val):
    if val is None:
        return ''
    val = str(val)
    val = CLEAN_TAG_RE.sub('', val)
    val = re.sub(r"mailto:|href=", '', val)
    val = val.strip()
    return val

class MainPanel:
    """Основная панель: карточки для каждого письма после применения фильтров"""
    def __init__(self):
        pass

    def render(self, publications: List[Dict[str, Any]], email_handler=None):
        st.markdown(
            '''<style>
                .stApp {background-color: #23242a;}
                section[data-testid="stSidebar"] {background-color: #262833;}
                .card {background:#e8e9ea; border-radius: 10px; padding:16px 18px; margin:16px 0 0 0;}
                .toc-main {display:flex;gap:10px;align-items:center; color:#222; font-size:1.1rem;}
                .toc-doi {font-family:ui-monospace,SFMono-Regular,Menlo,monospace;background:#f1f3f6;padding:1px 7px 1px 7px;border-radius:6px;font-size:0.97rem;letter-spacing:0.03em;}
                .toc-ti {font-weight:700; word-break:break-word;flex-grow:1;}
                .toc-meta {color:#3a444e; font-size:0.98rem;}
                .btn-more {width:100%; display:block; text-align:center; letter-spacing:0.01em; background:#cfd1d6;border:1px solid #b9bac1;border-radius:20px;padding:6px 0 6px 0; cursor:pointer; font-size:1.02rem;}
                .btn-more:hover {background:#b1b2b7;}
                .details-pane {background:#f7f7fa; border-radius:10px; margin-top:2px; padding:18px 18px 10px 18px;}
            </style>''', unsafe_allow_html=True)

        if not publications:
            st.info("📭 Нет писем с публикациями для отображения")
            return

        st.header(f"📚 Найдено писем: {len(publications)}")

        for idx, pub in enumerate(publications, 1):
            self._render_letter_card(pub, key=f"letter_{idx}")

    def _get_last(self, v):
        if isinstance(v, list) and v:
            return v[-1]
        return v if v else ''

    def _render_letter_card(self, pub: Dict[str, Any], key: str):
        # TI (или тема письма если пусто)
        ti = clean_val(pub.get('title') or pub.get('TI') or pub.get('subject') or '')
        doi = self._clean_doi(pub.get('doi',''))
        # M3 или, если нет, TY, иначе "Не указан"
        pub_type = clean_val(pub.get('M3') or pub.get('type') or pub.get('TY') or 'Не указан')
        # PY
        year = clean_val(self._get_last(pub.get('PY') or pub.get('year')) or 'Не указан')
        # AU: показать первый и последний
        au = pub.get('AU') or pub.get('authors') or []
        if isinstance(au, str):
            au = [au]
        au = [clean_val(x) for x in au if x and not BRACKETS_RE.match(str(x))]
        fa = au[0] if au else ''
        la = au[-1] if au and len(au)>1 else (fa if fa else '')
        # CARD
        st.markdown('<div class="card">', unsafe_allow_html=True)
        header = f"""
          <div class='toc-main'>
            <span class='toc-ti'>{ti}</span>
            <span class='toc-doi'>DOI: {doi}</span>
            <span class='toc-meta'>• {pub_type} • {year}</span>
            <span class='toc-meta'>• {fa}{' – ' + la if la and fa and la != fa else ''}</span>
          </div>
        """
        st.markdown(header, unsafe_allow_html=True)
        # Toggle-кнопка Подробнее/Скрыть
        exp_state = st.session_state.get(f"exp_{key}", False)
        label = "Скрыть ▲" if exp_state else "Подробнее ▼"
        if st.button(label, key=f"btn_{key}", use_container_width=True):
            st.session_state[f"exp_{key}"] = not exp_state
            exp_state = not exp_state
        if exp_state:
            st.markdown('<div class="details-pane">', unsafe_allow_html=True)
            self._render_details(pub)
            st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    def _render_details(self, pub: Dict[str, Any]):
        def show(val):
            if isinstance(val,list):
                for v in val:
                    v = clean_val(v)
                    if v: st.markdown(f"- {v}")
            else:
                v = clean_val(val)
                if v: st.markdown(f"{v}")
        indices = [
            ('DOI', pub.get('doi') or pub.get('DO')), ('TI', pub.get('title') or pub.get('TI')),
            ('M3', pub.get('M3') or pub.get('type')), ('TY', pub.get('TY')),
            ('PY', pub.get('PY') or pub.get('year')), ('T2', pub.get('T2') or pub.get('journal')),
            ('VL', pub.get('VL') or pub.get('volume')), ('IS', pub.get('IS') or pub.get('issue')),
            ('SP', pub.get('SP') or pub.get('pages')), ('EP', pub.get('EP')),
            ('AU', pub.get('AU') or pub.get('authors')), ('KW', pub.get('KW') or pub.get('keywords')),
            ('DE', pub.get('DE')), ('AB', pub.get('AB') or pub.get('abstract')),
            ('N2', pub.get('N2') or pub.get('notes')), ('UR', pub.get('UR')),
            ('L1', pub.get('L1')),('L2', pub.get('L2'))
        ]
        for label, val in indices:
            if val:
                st.markdown(f"**{label}:**")
                show(val)
        # мета info из письма
        meta = []
        for k in ('folder','from','subject','date','uid'):
            v = pub.get(k)
            if v: meta.append(f"{k.capitalize()}: {clean_val(v)}")
        if meta:
            st.markdown("**Метаданные письма:**")
            for line in meta:
                st.markdown(line)

    def _clean_doi(self, doi: str) -> str:
        if not doi: return ''
        doi = str(doi).strip()
        for pref in ['https://doi.org/','http://doi.org/','doi.org/','DOI:','doi:']:
            doi = doi.replace(pref,'')
        return doi.strip()
