# Создаем итоговый список всех созданных файлов
import os

def get_file_tree(directory='.', prefix='', max_depth=3, current_depth=0):
    """Создает древовидную структуру файлов"""
    if current_depth > max_depth:
        return ""
    
    items = []
    try:
        for item in sorted(os.listdir(directory)):
            if item.startswith('.') and item not in ['.streamlit', '.gitignore']:
                continue
            if item == '__pycache__':
                continue
                
            path = os.path.join(directory, item)
            
            if os.path.isdir(path):
                items.append(f"{prefix}📁 {item}/")
                if current_depth < max_depth:
                    subtree = get_file_tree(path, prefix + "  ", max_depth, current_depth + 1)
                    if subtree:
                        items.append(subtree)
            else:
                # Определяем тип файла по расширению
                if item.endswith('.py'):
                    icon = "🐍"
                elif item.endswith('.md'):
                    icon = "📝"
                elif item.endswith('.txt'):
                    icon = "📄"
                elif item.endswith('.toml'):
                    icon = "⚙️"
                else:
                    icon = "📄"
                items.append(f"{prefix}{icon} {item}")
    except PermissionError:
        pass
    
    return "\\n".join(items)

tree = get_file_tree()

print("🔬 СТРУКТУРА ПРИЛОЖЕНИЯ SCI.NET.NODE")
print("=" * 50)
print(tree)
print("=" * 50)

# Подсчитаем статистику
total_files = 0
total_lines = 0

for root, dirs, files in os.walk('.'):
    # Исключаем скрытые папки и __pycache__
    dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
    
    for file in files:
        if file.endswith(('.py', '.md', '.txt', '.toml')) and not file.startswith('.'):
            total_files += 1
            filepath = os.path.join(root, file)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    total_lines += len(f.readlines())
            except:
                pass

print(f"\\n📊 СТАТИСТИКА:")
print(f"📄 Общее количество файлов: {total_files}")
print(f"📝 Общее количество строк кода: {total_lines}")
print(f"🐍 Python файлов: {len([f for f in os.listdir('.') if f.endswith('.py')] + [f for f in os.listdir('components') if f.endswith('.py')] + [f for f in os.listdir('utils') if f.endswith('.py')])}")
print(f"📁 Компонентов: {len([f for f in os.listdir('components') if f.endswith('.py') and f != '__init__.py'])}")
print(f"🔧 Утилит: {len([f for f in os.listdir('utils') if f.endswith('.py') and f != '__init__.py'])}")