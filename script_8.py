# Создаем боковую панель с фильтрами
sidebar_content = '''"""
Боковая панель с фильтрами для Sci.Net.Node
"""

import streamlit as st
from datetime import datetime, date
from typing import List, Dict, Any
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter
import pandas as pd

class SidebarPanel:
    """Класс для боковой панели с фильтрами и функциями"""
    
    def __init__(self, publications: List[Dict[str, Any]]):
        self.publications = publications
    
    def render_connection_section(self) -> Dict[str, str]:
        """Секция подключения к почте"""
        st.sidebar.header("🔐 Подключение к почте")
        
        email = st.sidebar.text_input(
            "Email адрес",
            placeholder="username@mail.ru",
            help="Ваш адрес электронной почты Mail.ru"
        )
        
        password = st.sidebar.text_input(
            "Пароль", 
            type="password",
            help="Пароль от почтового ящика"
        )
        
        connect_button = st.sidebar.button("🔗 Подключиться", type="primary")
        
        return {
            'email': email,
            'password': password,
            'connect': connect_button
        }
    
    def render_filters_section(self, folders: List[str]) -> Dict[str, Any]:
        """Секция фильтров"""
        st.sidebar.header("🔍 Фильтры")
        
        # Фильтр по папкам
        selected_folders = st.sidebar.multiselect(
            "Папки почтового ящика",
            options=folders,
            default=folders,
            help="Выберите папки для отображения писем"
        )
        
        # Фильтр по дате
        st.sidebar.subheader("📅 Период")
        
        col1, col2 = st.sidebar.columns(2)
        with col1:
            date_from = st.date_input(
                "С даты",
                value=date.today().replace(year=date.today().year-1),
                help="Начальная дата фильтрации"
            )
        
        with col2:
            date_to = st.date_input(
                "До даты", 
                value=date.today(),
                help="Конечная дата фильтрации"
            )
        
        # RIS фильтры
        st.sidebar.subheader("📋 RIS поля")
        
        # Получаем уникальные значения для фильтров
        unique_types = self._get_unique_field_values('type')
        unique_years = self._get_unique_field_values('year')
        
        # Фильтр по типу публикации
        selected_types = st.sidebar.multiselect(
            "Тип публикации (M3/TY)",
            options=unique_types,
            help="Фильтр по типу работы"
        )
        
        # Фильтр по году
        selected_years = st.sidebar.multiselect(
            "Год публикации (PY)", 
            options=sorted(unique_years, reverse=True),
            help="Фильтр по году публикации"
        )
        
        # Фильтр по автору
        author_search = st.sidebar.text_input(
            "Поиск по автору (AU)",
            placeholder="Введите имя автора...",
            help="Поиск по авторам публикации"
        )
        
        # Фильтр по заголовку
        title_search = st.sidebar.text_input(
            "Поиск по заголовку (TI)",
            placeholder="Введите ключевые слова...",
            help="Поиск по заголовку публикации"
        )
        
        # Фильтр по ключевым словам
        keywords_search = st.sidebar.text_input(
            "Поиск по ключевым словам (KW/DE)",
            placeholder="Введите ключевые слова...",
            help="Поиск по ключевым словам"
        )
        
        return {
            'folders': selected_folders,
            'date_from': date_from,
            'date_to': date_to,
            'types': selected_types,
            'years': selected_years,
            'author_search': author_search,
            'title_search': title_search,
            'keywords_search': keywords_search
        }
    
    def render_analytics_section(self, filtered_publications: List[Dict[str, Any]]):
        """Секция аналитики и диаграмм"""
        st.sidebar.header("📊 Аналитика")
        
        if not filtered_publications:
            st.sidebar.info("Нет данных для анализа")
            return
        
        # Показываем статистику
        total_pubs = len(filtered_publications)
        unique_dois = len(set(pub.get('doi', '') for pub in filtered_publications if pub.get('doi')))
        
        st.sidebar.metric("Всего публикаций", total_pubs)
        st.sidebar.metric("Уникальных DOI", unique_dois)
        
        # Кнопки для диаграмм
        st.sidebar.subheader("📈 Диаграммы")
        
        # Выбор поля для анализа
        analysis_field = st.sidebar.selectbox(
            "Поле для анализа",
            options=['type', 'year', 'keywords'],
            format_func=lambda x: {
                'type': 'Тип публикации (TY/M3)',
                'year': 'Год публикации (PY)', 
                'keywords': 'Ключевые слова (KW/DE)'
            }[x]
        )
        
        if st.sidebar.button("📊 Показать частоты", key="frequency_chart"):
            self._show_frequency_chart(filtered_publications, analysis_field)
        
        if st.sidebar.button("🌟 Отобразить концепции", key="concepts_chart"):
            self._show_concepts_sankey(filtered_publications)
        
        # Экспорт данных
        st.sidebar.subheader("💾 Экспорт")
        
        if st.sidebar.button("📄 Скачать RIS"):
            self._export_to_ris(filtered_publications)
        
        if st.sidebar.button("📊 Скачать CSV"):
            self._export_to_csv(filtered_publications)
    
    def _get_unique_field_values(self, field: str) -> List[str]:
        """Получение уникальных значений поля"""
        values = set()
        
        for pub in self.publications:
            value = pub.get(field)
            if isinstance(value, list):
                values.update(str(v) for v in value if v)
            elif value:
                values.add(str(value))
        
        return sorted(list(values))
    
    def _show_frequency_chart(self, publications: List[Dict[str, Any]], field: str):
        """Отображение диаграммы частот"""
        with st.expander("📊 Диаграмма частот", expanded=True):
            # Подготовка данных
            data = []
            for pub in publications:
                value = pub.get(field)
                year = pub.get('year', 'Неизвестно')
                
                if isinstance(value, list):
                    for v in value:
                        if v:
                            data.append({'value': str(v), 'year': str(year)})
                elif value:
                    data.append({'value': str(value), 'year': str(year)})
            
            if not data:
                st.warning("Нет данных для отображения")
                return
            
            df = pd.DataFrame(data)
            
            # Группировка и подсчет
            freq_df = df.groupby(['year', 'value']).size().reset_index(name='count')
            
            # Создание диаграммы
            fig = px.line(
                freq_df, 
                x='year', 
                y='count',
                color='value',
                title=f'Частота встречаемости: {field}',
                labels={'year': 'Год', 'count': 'Количество', 'value': field}
            )
            
            fig.update_layout(
                height=400,
                xaxis_title="Год публикации",
                yaxis_title="Частота"
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    def _show_concepts_sankey(self, publications: List[Dict[str, Any]]):
        """Отображение Sankey диаграммы концептов"""
        with st.expander("🌟 Sankey диаграмма концептов", expanded=True):
            
            # Получаем концепты из OpenAlex для заголовков
            st.info("🔄 Получение концептов из OpenAlex...")
            
            # Импортируем здесь чтобы избежать циклических импортов
            from utils.openalex_utils import OpenAlexUtils
            
            all_concepts = []
            
            # Собираем концепты для всех публикаций
            for pub in publications[:10]:  # Ограничиваем для демо
                title = pub.get('title', '')
                abstract = pub.get('abstract', '')
                
                if title:
                    concepts = OpenAlexUtils.get_concepts_for_text(title, abstract)
                    formatted_concepts = OpenAlexUtils.format_concepts_for_sankey(concepts)
                    all_concepts.extend(formatted_concepts)
            
            if not all_concepts:
                st.warning("Не удалось получить концепты для анализа")
                return
            
            # Подготовка данных для Sankey
            sankey_data = self._prepare_sankey_data(all_concepts)
            
            if sankey_data:
                fig = go.Figure(data=[go.Sankey(
                    node=dict(
                        pad=15,
                        thickness=20,
                        line=dict(color="black", width=0.5),
                        label=sankey_data['labels'],
                        color="blue"
                    ),
                    link=dict(
                        source=sankey_data['sources'],
                        target=sankey_data['targets'], 
                        value=sankey_data['values']
                    )
                )])
                
                fig.update_layout(
                    title_text="Sankey диаграмма концептов",
                    font_size=10,
                    height=600
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Недостаточно данных для Sankey диаграммы")
    
    def _prepare_sankey_data(self, concepts: List[Dict[str, Any]]) -> Dict[str, List]:
        """Подготовка данных для Sankey диаграммы"""
        
        # Группируем концепты по уровням
        levels = {}
        for concept in concepts:
            level = concept['level']
            if level not in levels:
                levels[level] = []
            levels[level].append(concept)
        
        # Если уровней меньше 2, не можем построить Sankey
        if len(levels) < 2:
            return {}
        
        # Создаем labels, sources, targets, values
        labels = []
        label_to_idx = {}
        sources = []
        targets = []
        values = []
        
        # Добавляем все концепты в labels
        for level in sorted(levels.keys()):
            for concept in levels[level]:
                label = concept['label']
                if label not in label_to_idx:
                    label_to_idx[label] = len(labels)
                    labels.append(label)
        
        # Создаем связи между уровнями
        level_keys = sorted(levels.keys())
        for i in range(len(level_keys) - 1):
            current_level = level_keys[i]
            next_level = level_keys[i + 1]
            
            for source_concept in levels[current_level][:5]:  # Ограничиваем
                for target_concept in levels[next_level][:5]:  # Ограничиваем
                    source_idx = label_to_idx[source_concept['label']]
                    target_idx = label_to_idx[target_concept['label']]
                    
                    # Значение связи основано на скорах концептов
                    value = (source_concept['score'] + target_concept['score']) / 2
                    
                    sources.append(source_idx)
                    targets.append(target_idx)
                    values.append(value)
        
        return {
            'labels': labels,
            'sources': sources, 
            'targets': targets,
            'values': values
        }
    
    def _export_to_ris(self, publications: List[Dict[str, Any]]):
        """Экспорт в RIS формат"""
        ris_content = ""
        
        for pub in publications:
            ris_content += "TY  - JOUR\\n"  # Тип по умолчанию
            
            if pub.get('doi'):
                ris_content += f"DO  - {pub['doi']}\\n"
            
            if pub.get('title'):
                ris_content += f"TI  - {pub['title']}\\n"
            
            if pub.get('authors'):
                for author in pub['authors']:
                    ris_content += f"AU  - {author}\\n"
            
            if pub.get('year'):
                ris_content += f"PY  - {pub['year']}\\n"
            
            if pub.get('journal'):
                ris_content += f"T2  - {pub['journal']}\\n"
            
            if pub.get('keywords'):
                for keyword in pub['keywords']:
                    ris_content += f"KW  - {keyword}\\n"
            
            ris_content += "ER  -\\n\\n"
        
        st.download_button(
            label="💾 Скачать RIS файл",
            data=ris_content,
            file_name=f"sci_net_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.ris",
            mime="text/plain"
        )
    
    def _export_to_csv(self, publications: List[Dict[str, Any]]):
        """Экспорт в CSV формат"""
        
        # Подготавливаем данные для CSV
        csv_data = []
        for pub in publications:
            csv_data.append({
                'DOI': pub.get('doi', ''),
                'Title': pub.get('title', ''),
                'Authors': '; '.join(pub.get('authors', [])),
                'Year': pub.get('year', ''),
                'Type': pub.get('type', ''),
                'Journal': pub.get('journal', ''),
                'Keywords': '; '.join(pub.get('keywords', []))
            })
        
        df = pd.DataFrame(csv_data)
        csv = df.to_csv(index=False)
        
        st.download_button(
            label="📊 Скачать CSV файл", 
            data=csv,
            file_name=f"sci_net_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
'''

with open("components/sidebar.py", "w", encoding="utf-8") as f:
    f.write(sidebar_content)

print("Файл components/sidebar.py создан")