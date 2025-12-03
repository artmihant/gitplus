#!/usr/bin/python
import os
import git
import sys
import re
from datetime import datetime

VERSION_FILE = 'VERSION'
CHANGELOG_FILE = 'CHANGELOG.md'

def has_commits(repo):
    """Проверяет, есть ли коммиты в репозитории"""
    try:
        repo.head.commit
        return True
    except (git.exc.BadName, ValueError):
        return False

def get_current_version():
    if os.path.exists(VERSION_FILE):
        with open(VERSION_FILE, 'r') as f:
            return f.read().strip()
    return '0.0.0'
    
def save_version(version_str):
    with open(VERSION_FILE, 'w') as f:
        f.write(version_str)

def increment_version(version_str):
    parts = version_str.split('.')
    if len(parts) >= 1:
        # Пытаемся инкрементировать последнюю часть, если она число
        try:
            parts[-1] = str(int(parts[-1]) + 1)
        except ValueError:
            # Если не число, просто добавляем .1
            parts.append('1')
    else:
        parts = ['0', '0', '1']
    return '.'.join(parts)

def parse_changelog_scenario(changelog_path):
    """
    Пытается выполнить сценарий (b).
    Возвращает кортеж (version, commit_message, new_file_content) если успешно.
    Возвращает None, если сценарий (b) невозможен (нет файла, нет [Unreleased], неверный формат).
    """
    if not os.path.exists(changelog_path):
        return None

    with open(changelog_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Ищем заголовок с [Unreleased].
    # Ожидаемый формат заголовка из примера: ## 1.2.3 - [2025-02-10 14:50:46] [Unreleased]
    # Ожидаемый формат из описания: ## 1.2.3 [2025-02-10 14:50:46]: message [Unreleased]
    # Будем искать ## ... [Unreleased] и парсить версию.
    
    # Regex ищем строку, начинающуюся с ##, содержащую [Unreleased]
    # Группируем всё до [Unreleased] чтобы вытащить версию
    # re.MULTILINE нужен для ^
    match = re.search(r'^##\s+(.*?)\s+\[Unreleased\]', content, re.MULTILINE)
    
    if not match:
        return None

    full_header_line = match.group(0)
    header_content = match.group(1) # "1.2.3 - [2025-02-10...]" или "1.2.3 [2025...]: msg"

    # Пытаемся вытащить версию. Обычно это первое "слово" в header_content
    # Предполагаем, что версия состоит из цифр и точек
    version_match = re.search(r'(\d+\.\d+\.\d+)', header_content)
    if not version_match:
        return None
    
    version = version_match.group(1)
    
    # Определяем границы тела сообщения
    start_index = match.end()
    
    # Ищем следующий заголовок второго уровня или конец файла
    next_header = re.search(r'^##\s+', content[start_index:], re.MULTILINE)
    
    if next_header:
        end_index = start_index + next_header.start()
        raw_body = content[start_index:end_index]
    else:
        raw_body = content[start_index:]
    
    # Формируем сообщение: убираем # в начале строк, убираем лишние пробелы
    lines = raw_body.split('\n')
    cleaned_lines = []
    for line in lines:
        # Убираем символы заголовков Markdown (#, ##, ###) в начале строки
        clean_line = re.sub(r'^\s*#+\s*', '', line)
        # Или просто убираем # как просили: "Убираем из текста сообщения символы # в началах строк"
        # clean_line = line.lstrip('#').strip() 
        # Но обычно в markdown это списки (*). 
        # Спека: "Убираем ... символы # в началах строк, то есть обозначения подзаголовков"
        cleaned_lines.append(clean_line)
            
    commit_message = '\n'.join(cleaned_lines).strip()
    
    # Убираем [Unreleased] из исходного контента
    # Заменяем первое вхождение найденной строки заголовка на неё же, но без [Unreleased]
    # Но нужно быть аккуратным с пробелами перед [Unreleased]
    new_header_line = full_header_line.replace('[Unreleased]', '').rstrip()
    new_content = content.replace(full_header_line, new_header_line, 1)

    # Добавляем заголовок (без [Unreleased]) как первую строку сообщения
    header_for_msg = new_header_line.lstrip('#').strip()
    commit_message = f"{header_for_msg}\n\n{commit_message}"

    return version, commit_message, new_content


if __name__ == '__main__':
    # Настройка рабочей директории
    current_dir = os.path.abspath(os.curdir)
    while not os.path.exists('.git'):
        current_dir = os.path.abspath(current_dir)
        if current_dir != os.path.dirname(current_dir):
            os.chdir(os.path.dirname(current_dir))
        else:
            print("❌ Ошибка: Git-репозиторий не найден!")
            print("💡 Для инициализации нового репозитория выполните: git init")
            sys.exit(1)
    
    try:
        repo = git.Repo(".")
    except git.exc.InvalidGitRepositoryError:
        print("❌ Ошибка: Папка .git найдена, но это не валидный Git-репозиторий!")
        sys.exit(1)

    # Основная логика выбора сценария
    # Сценарий (a) запускается если:
    # - Передан аргумент команды
    # - Или парсинг CHANGELOG.md не удался (нет файла, нет [Unreleased])
    
    args_message = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else None
    
    scenario = 'a'
    changelog_data = None

    if args_message:
        scenario = 'a'
    else:
        # Пытаемся парсить changelog
        changelog_data = parse_changelog_scenario(CHANGELOG_FILE)
        if changelog_data:
            scenario = 'b'
        else:
            scenario = 'a'

    # Сбор файлов для коммита (общая часть)
    has_repo_commits = has_commits(repo)
    working_tree_diffs = list(repo.index.diff(None))
    untracked_files = list(repo.untracked_files)
    staged_changes = list(repo.index.diff("HEAD")) if has_repo_commits else []

    if not (untracked_files or working_tree_diffs or staged_changes):
        # Если нет изменений файлов, но, возможно, мы хотим обновить версию/лог?
        # Обычно если нет изменений, коммит пустой. Скрипт раньше выходил.
        print('Nothing to commit!')
        sys.exit(0)

    # Добавляем файлы
    for diff in working_tree_diffs:
        repo.git.add(diff.a_path)
    for file in untracked_files:
        repo.git.add(file)
    
    # Вывод статуса (как было)
    if has_repo_commits:
        for diff in repo.index.diff("HEAD"):
            # Отображаем тип изменения
            print(f"{diff.change_type}: {diff.a_path}")
    else:
        print("Первый коммит:")
        for file in repo.untracked_files:
            print('-', file)

    # Выполнение сценария
    commit_message = ""
    
    if scenario == 'a':
        print("Commit Message (Arguments):")
        current_ver = get_current_version()
        new_version = increment_version(current_ver)
        save_version(new_version)
        repo.git.add(VERSION_FILE)
        
        current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        commit_message = f'{new_version} [{current_datetime}]'
        if args_message:
            commit_message += f': {args_message}'
            
    elif scenario == 'b' and changelog_data:
        print("Commit Message (Changelog):")
        version, msg_body, new_changelog_content = changelog_data
        
        # Обновляем VERSION
        save_version(version)
        repo.git.add(VERSION_FILE)
        
        # Обновляем CHANGELOG.md
        with open(CHANGELOG_FILE, 'w', encoding='utf-8') as f:
            f.write(new_changelog_content)
        repo.git.add(CHANGELOG_FILE)
        
        commit_message = msg_body

    print(f'Commit Message:\n{commit_message}')
    repo.git.commit(m=commit_message)
