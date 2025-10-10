# Создаем структуру приложения Sci.Net.Node
import os

# Создаем основные файлы приложения
files_structure = {
    "app.py": "Главный файл Streamlit приложения",
    "requirements.txt": "Зависимости приложения",
    "config.py": "Конфигурация приложения", 
    "components/": "Папка с компонентами",
    "components/email_handler.py": "Обработчик почты",
    "components/sidebar.py": "Боковая панель с фильтрами",
    "components/main_panel.py": "Основная панель с карточками",
    "components/charts_panel.py": "Панель с диаграммами",
    "components/ris_parser.py": "Парсер RIS формата",
    "utils/": "Папка с утилитами",
    "utils/doi_utils.py": "Утилиты для работы с DOI",
    "utils/openalex_utils.py": "Утилиты для работы с OpenAlex API",
    "README.md": "Инструкции по запуску"
}

print("Структура файлов приложения Sci.Net.Node:")
for file_path, description in files_structure.items():
    print(f"{file_path:35} - {description}")