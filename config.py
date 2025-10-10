"""
Конфигурация приложения Sci.Net.Node
"""

import os

# Настройки почты Mail.ru
EMAIL_CONFIG = {
    "imap_server": "imap.mail.ru",
    "smtp_server": "smtp.mail.ru", 
    "smtp_port": 465,
    "use_ssl": True
}

# Настройки приложения
APP_CONFIG = {
    "title": "Sci.Net.Node - Scientific Network Node",
    "description": "Система управления научными публикациями через электронную почту",
    "version": "1.0.0"
}

# API настройки
API_CONFIG = {
    "openalex_base_url": "https://api.openalex.org",
    "crossref_base_url": "https://api.crossref.org",
    "user_agent": "SciNetNode/1.0 (https://github.com/user/sci-net-node)"
}

# RIS теги и их описания
RIS_TAGS = {
    "TY": "Type of reference",
    "M3": "Type of work", 
    "TI": "Title",
    "AU": "Authors",
    "PY": "Publication year",
    "DO": "DOI",
    "AB": "Abstract", 
    "KW": "Keywords",
    "DE": "Author keywords",
    "T2": "Secondary title (journal)",
    "VL": "Volume",
    "IS": "Issue", 
    "SP": "Start page",
    "EP": "End page",
    "PB": "Publisher",
    "CY": "Place of publication",
    "N2": "Notes",
    "UR": "URL",
    "L1": "Link to PDF",
    "L2": "Link to full-text",
    "ER": "End of reference"
}

# Паттерны запросов из Sci.Net.Core
REQUEST_PATTERNS = {
    "PDF_REQUEST": "[PDF request]",
    "M3_REQUEST": "[M3 request]", 
    "KW_REQUEST": "[KW request]",
    "PMID_REQUEST": "[PMID request]",
    "CITS_REQUEST": "[CITS request]",
    "INSERT_ABSTRACT": "[insert abstract]",
    "INSERT_KEYWORDS": "[insert authors keywords]",
    "INSERT_NOTES": "[insert notes]"
}

# DOI регулярное выражение
DOI_PATTERN = r'\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b'

# Sci.Net.Core почтовый адрес
SCINET_CORE_EMAIL = "sci.net@inbox.ru"
