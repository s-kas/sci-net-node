"""
RIS парсер для Sci.Net.Node
Извлечение и обработка RIS данных из писем
"""

import re
from typing import Dict, List, Any, Optional
from config import RIS_TAGS
import streamlit as st

class RISParser:
    """Класс для парсинга RIS данных"""

    def __init__(self):
        self.ris_tags = RIS_TAGS

    def parse_ris_from_text(self, text: str) -> Dict[str, Any]:
        """
        Извлечение RIS данных из произвольного текста
        """
        if not text:
            return {}

        ris_data = {}

        # Паттерн для RIS полей: TAG - VALUE
        ris_pattern = r'^([A-Z0-9]{2})\s*-\s*(.+)$'

        lines = text.split('\n')
        current_tag = None
        current_value = ""

        for line in lines:
            line = line.strip()

            # Проверяем начало нового RIS поля
            match = re.match(ris_pattern, line)
            if match:
                # Сохраняем предыдущее поле если есть
                if current_tag:
                    self._add_ris_field(ris_data, current_tag, current_value)

                current_tag, current_value = match.groups()
                current_value = current_value.strip()
            else:
                # Продолжение многострочного поля
                if current_tag and line:
                    current_value += " " + line

        # Сохраняем последнее поле
        if current_tag:
            self._add_ris_field(ris_data, current_tag, current_value)

        return ris_data

    def _add_ris_field(self, ris_data: Dict, tag: str, value: str):
        """Добавление RIS поля в структуру данных"""
        value = value.strip()
        if not value:
            return

        # Поля которые могут повторяться
        multi_fields = ['AU', 'KW', 'DE', 'CR', 'A1', 'A2', 'A3']

        if tag in multi_fields:
            if tag not in ris_data:
                ris_data[tag] = []
            ris_data[tag].append(value)
        else:
            # Для одиночных полей берем последнее значение
            ris_data[tag] = value

    def extract_publication_info(self, ris_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Извлечение основной информации о публикации из RIS данных
        """
        info = {
            'doi': ris_data.get('DO', ''),
            'title': ris_data.get('TI', ''),
            'type': ris_data.get('M3', ris_data.get('TY', '')),
            'year': ris_data.get('PY', ''),
            'authors': [],
            'journal': ris_data.get('T2', ''),
            'volume': ris_data.get('VL', ''),
            'issue': ris_data.get('IS', ''),
            'pages': ris_data.get('SP', ''),
            'keywords': [],
            'abstract': ris_data.get('AB', ''),
            'notes': ris_data.get('N2', ''),
            'url': ris_data.get('UR', ''),
            'pdf_link': ris_data.get('L1', '')
        }

        # Обработка авторов
        authors = ris_data.get('AU', [])
        if isinstance(authors, list):
            info['authors'] = authors
        elif isinstance(authors, str):
            info['authors'] = [authors]

        # Первый и последний автор для отображения
        if info['authors']:
            info['first_author'] = info['authors'][0]
            info['last_author'] = info['authors'][-1] if len(info['authors']) > 1 else ''
        else:
            info['first_author'] = ''
            info['last_author'] = ''

        # Обработка ключевых слов
        keywords = []
        for kw_field in ['KW', 'DE']:
            kw_data = ris_data.get(kw_field, [])
            if isinstance(kw_data, list):
                keywords.extend(kw_data)
            elif isinstance(kw_data, str):
                keywords.append(kw_data)

        info['keywords'] = keywords

        return info

    def filter_publications_by_ris(self, publications: List[Dict], 
                                  ris_filters: Dict[str, str]) -> List[Dict]:
        """
        Фильтрация публикаций по RIS полям
        """
        filtered = []

        for pub in publications:
            matches = True

            for field, filter_value in ris_filters.items():
                if not filter_value:  # Пропускаем пустые фильтры
                    continue

                pub_value = pub.get(field, '')

                # Для списков ищем вхождение
                if isinstance(pub_value, list):
                    if not any(filter_value.lower() in str(v).lower() for v in pub_value):
                        matches = False
                        break
                else:
                    # Для строк ищем подстроку
                    if filter_value.lower() not in str(pub_value).lower():
                        matches = False
                        break

            if matches:
                filtered.append(pub)

        return filtered

    def get_unique_values_for_field(self, publications: List[Dict], 
                                   field: str) -> List[str]:
        """
        Получение уникальных значений для конкретного поля
        """
        values = set()

        for pub in publications:
            field_value = pub.get(field)

            if isinstance(field_value, list):
                values.update(str(v) for v in field_value if v)
            elif field_value:
                values.add(str(field_value))

        return sorted(list(values))

    def validate_doi(self, doi: str) -> bool:
        """Проверка корректности DOI"""
        if not doi:
            return False

        # Базовый паттерн DOI
        doi_pattern = r'^10\.\d{4,9}/[-._;()/:A-Z0-9]+$'
        return bool(re.match(doi_pattern, doi, re.IGNORECASE))

    def clean_doi(self, doi: str) -> str:
        """Очистка DOI от лишних символов"""
        if not doi:
            return ""

        # Убираем префиксы URL
        doi = doi.replace('https://doi.org/', '')
        doi = doi.replace('http://doi.org/', '')
        doi = doi.replace('doi.org/', '')
        doi = doi.replace('DOI:', '')
        doi = doi.replace('doi:', '')

        return doi.strip()
