# Создаем утилиты для работы с DOI
doi_utils_content = '''"""
Утилиты для работы с DOI
"""

import re
import requests
from typing import Optional, Dict, Any
from config import API_CONFIG
import streamlit as st

class DOIUtils:
    """Класс для работы с DOI"""
    
    @staticmethod
    def extract_doi_from_text(text: str) -> Optional[str]:
        """Извлечение первого DOI из текста"""
        if not text:
            return None
            
        # Расширенный паттерн для поиска DOI
        patterns = [
            r'\\b(10\\.\\d{4,9}/[-._;()/:A-Z0-9]+)\\b',  # Стандартный DOI
            r'doi\\.org/(10\\.\\d{4,9}/[-._;()/:A-Z0-9]+)',  # URL doi.org
            r'https?://doi\\.org/(10\\.\\d{4,9}/[-._;()/:A-Z0-9]+)',  # Полный URL
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                return matches[0]
        
        return None
    
    @staticmethod
    def clean_doi(doi: str) -> str:
        """Очистка DOI"""
        if not doi:
            return ""
        
        # Убираем различные префиксы
        prefixes = [
            'https://doi.org/',
            'http://doi.org/', 
            'doi.org/',
            'DOI:',
            'doi:',
            'DOI ',
            'doi '
        ]
        
        for prefix in prefixes:
            doi = doi.replace(prefix, '')
        
        return doi.strip()
    
    @staticmethod
    def validate_doi(doi: str) -> bool:
        """Валидация DOI"""
        if not doi:
            return False
        
        # Очищаем DOI
        clean_doi = DOIUtils.clean_doi(doi)
        
        # Проверяем по паттерну
        pattern = r'^10\\.\\d{4,9}/[-._;()/:A-Z0-9]+$'
        return bool(re.match(pattern, clean_doi, re.IGNORECASE))
    
    @staticmethod
    def get_crossref_data(doi: str) -> Optional[Dict[str, Any]]:
        """Получение данных из Crossref API"""
        clean_doi = DOIUtils.clean_doi(doi)
        
        if not DOIUtils.validate_doi(clean_doi):
            return None
        
        url = f"{API_CONFIG['crossref_base_url']}/works/{clean_doi}"
        headers = {'User-Agent': API_CONFIG['user_agent']}
        
        try:
            response = requests.get(url, headers=headers, timeout=20)
            if response.status_code == 200:
                return response.json().get('message')
            return None
            
        except Exception as e:
            st.warning(f"Ошибка запроса к Crossref: {e}")
            return None
    
    @staticmethod
    def format_crossref_to_ris(crossref_data: Dict[str, Any]) -> Dict[str, Any]:
        """Конвертация данных Crossref в RIS формат"""
        ris_data = {}
        
        if not crossref_data:
            return ris_data
        
        try:
            # Основные поля
            ris_data['DO'] = crossref_data.get('DOI', '')
            ris_data['TI'] = crossref_data.get('title', [''])[0]
            ris_data['TY'] = crossref_data.get('type', '')
            
            # Авторы
            authors = []
            for author in crossref_data.get('author', []):
                given = author.get('given', '')
                family = author.get('family', '')
                if given and family:
                    authors.append(f"{family}, {given}")
                elif family:
                    authors.append(family)
            
            if authors:
                ris_data['AU'] = authors
            
            # Журнал
            container_title = crossref_data.get('container-title', [])
            if container_title:
                ris_data['T2'] = container_title[0]
            
            # Год публикации
            published = crossref_data.get('published-print', {}).get('date-parts', [[None]])
            year = published[0][0] if published[0] else None
            if not year:
                published = crossref_data.get('published-online', {}).get('date-parts', [[None]])
                year = published[0][0] if published[0] else None
            
            if year:
                ris_data['PY'] = str(year)
            
            # Дополнительные поля
            ris_data['VL'] = crossref_data.get('volume', '')
            ris_data['IS'] = crossref_data.get('issue', '')
            ris_data['SP'] = crossref_data.get('page', '')
            ris_data['PB'] = crossref_data.get('publisher', '')
            
            # URL
            doi = ris_data.get('DO', '')
            if doi:
                ris_data['UR'] = f"https://doi.org/{doi}"
                
        except Exception as e:
            st.warning(f"Ошибка конвертации Crossref данных: {e}")
        
        return ris_data
'''

with open("utils/doi_utils.py", "w", encoding="utf-8") as f:
    f.write(doi_utils_content)

print("Файл utils/doi_utils.py создан")