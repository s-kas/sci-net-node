# Создаем утилиты для работы с OpenAlex
openalex_utils_content = '''"""
Утилиты для работы с OpenAlex API
"""

import requests
from typing import List, Dict, Any, Optional
from config import API_CONFIG
import streamlit as st

class OpenAlexUtils:
    """Класс для работы с OpenAlex API"""
    
    @staticmethod
    def get_work_by_doi(doi: str) -> Optional[Dict[str, Any]]:
        """Получение работы по DOI"""
        if not doi:
            return None
        
        # Очищаем DOI
        clean_doi = doi.replace('https://doi.org/', '').replace('http://doi.org/', '')
        url = f"{API_CONFIG['openalex_base_url']}/works/https://doi.org/{clean_doi}"
        
        headers = {'User-Agent': API_CONFIG['user_agent']}
        
        try:
            response = requests.get(url, headers=headers, timeout=20)
            if response.status_code == 200:
                return response.json()
            return None
            
        except Exception as e:
            st.warning(f"Ошибка запроса к OpenAlex: {e}")
            return None
    
    @staticmethod
    def get_concepts_for_text(title: str, abstract: str = "") -> List[Dict[str, Any]]:
        """Получение концептов для текста через OpenAlex"""
        if not title:
            return []
        
        url = f"{API_CONFIG['openalex_base_url']}/text/concepts"
        params = {'title': title}
        
        if abstract:
            params['abstract'] = abstract
        
        headers = {'User-Agent': API_CONFIG['user_agent']}
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=15)
            if response.status_code == 200:
                data = response.json()
                return data.get('concepts', [])
            return []
            
        except Exception as e:
            st.warning(f"Ошибка получения концептов: {e}")
            return []
    
    @staticmethod
    def format_concepts_for_sankey(concepts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Форматирование концептов для Sankey диаграммы"""
        sankey_data = []
        
        for concept in concepts:
            # Получаем уровень концепта
            level = concept.get('level', 0)
            display_name = concept.get('display_name', '')
            score = concept.get('score', 0)
            
            if display_name and score > 0.1:  # Фильтруем слабые концепты
                sankey_data.append({
                    'level': level,
                    'name': display_name,
                    'score': score,
                    'label': f"K{level} - {display_name}"
                })
        
        return sankey_data
    
    @staticmethod
    def search_works_by_concepts(concept_ids: List[str], limit: int = 50) -> List[Dict[str, Any]]:
        """Поиск работ по концептам"""
        if not concept_ids:
            return []
        
        # Формируем фильтр по концептам
        concepts_filter = '|'.join(concept_ids)
        url = f"{API_CONFIG['openalex_base_url']}/works"
        
        params = {
            'filter': f'concepts.id:{concepts_filter}',
            'per-page': limit,
            'sort': 'cited_by_count:desc'
        }
        
        headers = {'User-Agent': API_CONFIG['user_agent']}
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=20)
            if response.status_code == 200:
                data = response.json()
                return data.get('results', [])
            return []
            
        except Exception as e:
            st.warning(f"Ошибка поиска работ: {e}")
            return []
    
    @staticmethod
    def get_citations_for_work(work_id: str) -> List[Dict[str, Any]]:
        """Получение цитирований для работы"""
        if not work_id:
            return []
        
        url = f"{API_CONFIG['openalex_base_url']}/works"
        params = {
            'filter': f'cites:{work_id}',
            'per-page': 100,
            'sort': 'publication_date:desc'
        }
        
        headers = {'User-Agent': API_CONFIG['user_agent']}
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=20)
            if response.status_code == 200:
                data = response.json()
                return data.get('results', [])
            return []
            
        except Exception as e:
            st.warning(f"Ошибка получения цитирований: {e}")
            return []
    
    @staticmethod
    def format_work_to_ris(work_data: Dict[str, Any]) -> Dict[str, Any]:
        """Конвертация данных OpenAlex в RIS формат"""
        ris_data = {}
        
        if not work_data:
            return ris_data
        
        try:
            # Основные поля
            ris_data['DO'] = work_data.get('doi', '').replace('https://doi.org/', '')
            ris_data['TI'] = work_data.get('title', '')
            ris_data['TY'] = work_data.get('type', '')
            
            # Год публикации
            pub_date = work_data.get('publication_date')
            if pub_date:
                ris_data['PY'] = pub_date.split('-')[0]
            
            # Авторы
            authors = []
            authorships = work_data.get('authorships', [])
            for authorship in authorships:
                author = authorship.get('author', {})
                display_name = author.get('display_name', '')
                if display_name:
                    authors.append(display_name)
            
            if authors:
                ris_data['AU'] = authors
            
            # Журнал/источник
            primary_location = work_data.get('primary_location', {})
            if primary_location:
                source = primary_location.get('source', {})
                if source:
                    ris_data['T2'] = source.get('display_name', '')
            
            # Концепты как ключевые слова
            concepts = work_data.get('concepts', [])
            keywords = []
            for concept in concepts[:10]:  # Берем топ-10 концептов
                if concept.get('score', 0) > 0.3:
                    keywords.append(concept.get('display_name', ''))
            
            if keywords:
                ris_data['KW'] = keywords
            
            # URL
            ris_data['UR'] = work_data.get('id', '')
            
            # Цитирования
            cited_by_count = work_data.get('cited_by_count', 0)
            if cited_by_count > 0:
                ris_data['N2'] = f"Цитируется: {cited_by_count} раз"
                
        except Exception as e:
            st.warning(f"Ошибка конвертации OpenAlex данных: {e}")
        
        return ris_data
    
    @staticmethod
    def get_author_works(author_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Получение работ автора"""
        if not author_id:
            return []
        
        url = f"{API_CONFIG['openalex_base_url']}/works"
        params = {
            'filter': f'authorships.author.id:{author_id}',
            'per-page': limit,
            'sort': 'publication_date:desc'
        }
        
        headers = {'User-Agent': API_CONFIG['user_agent']}
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=20)
            if response.status_code == 200:
                data = response.json()
                return data.get('results', [])
            return []
            
        except Exception as e:
            st.warning(f"Ошибка получения работ автора: {e}")
            return []
'''

with open("utils/openalex_utils.py", "w", encoding="utf-8") as f:
    f.write(openalex_utils_content)

print("Файл utils/openalex_utils.py создан")