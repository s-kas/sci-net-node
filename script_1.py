# Создаем файл requirements.txt
requirements_content = """streamlit==1.28.1
imap-tools==1.7.0
beautifulsoup4==4.12.2
requests==2.31.0
plotly==5.17.0
pandas==2.1.2
openpyxl==3.1.2
python-dateutil==2.8.2
urllib3==2.0.7
email-validator==2.1.0
rispy==0.7.1
python-dotenv==1.0.0
"""

with open("requirements.txt", "w", encoding="utf-8") as f:
    f.write(requirements_content)

print("Файл requirements.txt создан")
print(requirements_content)