# Создаем папку для компонентов
import os
if not os.path.exists("components"):
    os.makedirs("components")
    
if not os.path.exists("utils"):
    os.makedirs("utils")
    
print("Папки components и utils созданы")

# Создаем __init__.py файлы для пакетов
with open("components/__init__.py", "w") as f:
    f.write("")
    
with open("utils/__init__.py", "w") as f:
    f.write("")
    
print("Файлы __init__.py созданы")