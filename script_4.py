# Создаем обработчик почты на основе Sci.Net.Core
email_handler_content = '''"""
Обработчик электронной почты для Sci.Net.Node
Адаптировано из Sci.Net.Core
"""

import re
import smtplib
import urllib.parse
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from imap_tools import MailBox, AND, OR
from bs4 import BeautifulSoup
from config import EMAIL_CONFIG, DOI_PATTERN, REQUEST_PATTERNS, SCINET_CORE_EMAIL
import streamlit as st
from typing import List, Dict, Tuple, Optional
from datetime import datetime

class EmailHandler:
    """Класс для работы с электронной почтой"""
    
    def __init__(self):
        self.mailbox = None
        self.smtp = None
        self.email = None
        self.password = None
        self.connected = False
        
    def connect(self, email: str, password: str) -> bool:
        """Подключение к почтовому серверу"""
        try:
            self.email = email
            self.password = password
            
            # Подключение к IMAP
            self.mailbox = MailBox(EMAIL_CONFIG["imap_server"])
            self.mailbox.login(email, password)
            
            # Подключение к SMTP  
            self.smtp = smtplib.SMTP_SSL(EMAIL_CONFIG["smtp_server"], EMAIL_CONFIG["smtp_port"])
            self.smtp.login(email, password)
            
            self.connected = True
            return True
            
        except Exception as e:
            st.error(f"Ошибка подключения к почте: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """Отключение от почтовых серверов"""
        try:
            if self.mailbox:
                self.mailbox.logout()
            if self.smtp:
                self.smtp.quit()
            self.connected = False
        except Exception as e:
            st.error(f"Ошибка отключения: {e}")
    
    def get_folders(self) -> List[str]:
        """Получение списка папок почтового ящика"""
        if not self.connected:
            return []
        
        try:
            folders = [folder.name for folder in self.mailbox.folder.list()]
            return folders
        except Exception as e:
            st.error(f"Ошибка получения папок: {e}")
            return []
    
    def extract_doi_from_text(self, text: str) -> Optional[str]:
        """Извлечение первого DOI из текста"""
        if not text:
            return None
            
        doi_matches = re.findall(DOI_PATTERN, text, re.IGNORECASE)
        return doi_matches[0] if doi_matches else None
    
    def get_emails_with_doi(self, folders: List[str] = None, 
                           date_from: datetime = None,
                           date_to: datetime = None) -> List[Dict]:
        """
        Получение всех писем содержащих DOI с фильтрацией
        """
        if not self.connected:
            return []
        
        if folders is None:
            folders = self.get_folders()
        
        emails_data = []
        
        for folder in folders:
            try:
                self.mailbox.folder.set(folder)
                
                # Строим критерии поиска
                criteria = []
                if date_from:
                    criteria.append(f"SINCE {date_from.strftime('%d-%b-%Y')}")
                if date_to:
                    criteria.append(f"BEFORE {date_to.strftime('%d-%b-%Y')}")
                
                # Получаем сообщения
                messages = list(self.mailbox.fetch(AND(*criteria) if criteria else None))
                
                for msg in messages:
                    try:
                        # Получаем текст письма
                        email_text = msg.text or ""
                        if not email_text and msg.html:
                            soup = BeautifulSoup(msg.html, 'html.parser')
                            email_text = soup.get_text()
                        
                        # Ищем DOI
                        doi = self.extract_doi_from_text(email_text)
                        
                        if doi:
                            email_data = {
                                'uid': msg.uid,
                                'folder': folder,
                                'from': msg.from_,
                                'to': msg.to,
                                'subject': msg.subject,
                                'date': msg.date,
                                'doi': doi,
                                'text': email_text,
                                'html': msg.html
                            }
                            emails_data.append(email_data)
                            
                    except Exception as msg_error:
                        continue
                        
            except Exception as folder_error:
                st.warning(f"Ошибка обработки папки {folder}: {folder_error}")
                continue
        
        return emails_data
    
    def parse_ris_data_from_email(self, email_text: str) -> Dict[str, str]:
        """
        Извлечение RIS данных из текста письма
        """
        ris_data = {}
        
        if not email_text:
            return ris_data
        
        # Паттерн для RIS полей
        ris_pattern = r'^([A-Z0-9]{2})\\s*-\\s*(.+)$'
        
        lines = email_text.split('\\n')
        for line in lines:
            line = line.strip()
            match = re.match(ris_pattern, line)
            if match:
                tag, value = match.groups()
                # Для множественных значений создаем списки
                if tag in ['AU', 'KW', 'DE']:
                    if tag not in ris_data:
                        ris_data[tag] = []
                    ris_data[tag].append(value.strip())
                else:
                    ris_data[tag] = value.strip()
        
        return ris_data
    
    def create_request_email_link(self, to_email: str, subject: str, body: str) -> str:
        """Создание mailto ссылки для запроса"""
        subject_encoded = urllib.parse.quote(subject)
        body_encoded = urllib.parse.quote(body)
        return f"mailto:{to_email}?subject={subject_encoded}&body={body_encoded}"
    
    def send_request_email(self, subject: str, body: str, to_email: str = SCINET_CORE_EMAIL) -> bool:
        """Отправка запроса в Sci.Net.Core"""
        if not self.connected:
            st.error("Нет подключения к почте")
            return False
        
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = self.email
            msg['To'] = to_email
            msg['Subject'] = subject
            msg['X-Mailer'] = 'SciNetNode1.0'
            
            # Текстовая версия
            text_part = MIMEText(body, 'plain')
            msg.attach(text_part)
            
            # Отправка
            self.smtp.sendmail(self.email, [to_email], msg.as_string())
            return True
            
        except Exception as e:
            st.error(f"Ошибка отправки письма: {e}")
            return False
'''

with open("components/email_handler.py", "w", encoding="utf-8") as f:
    f.write(email_handler_content)

print("Файл components/email_handler.py создан")