#!/usr/bin/python
import os
import git
import sys
from datetime import datetime

VERSION_FILE = 'VERSION'

def has_commits(repo):
    """Проверяет, есть ли коммиты в репозитории"""
    try:
        repo.head.commit
        return True
    except (git.exc.BadName, ValueError):
        return False

if __name__ == '__main__':
    dir = os.path.abspath(os.curdir)
    while not os.path.exists('.git'):
        dir = os.path.abspath(os.curdir)
        if dir != os.path.dirname(dir):
            os.chdir(os.path.dirname(dir))
        else:
            print("❌ Ошибка: Git-репозиторий не найден!")
            print("💡 Для инициализации нового репозитория выполните: git init")
            sys.exit(1)
    
    try:
        repo = git.Repo(".")
    except git.exc.InvalidGitRepositoryError:
        print("❌ Ошибка: Папка .git найдена, но это не валидный Git-репозиторий!")
        print("💡 Для инициализации нового репозитория выполните: git init")
        sys.exit(1)

    # print(repo.index.diff(None))
    # print(repo.untracked_files)
    # print(repo.index.diff("HEAD"))
    
    # Проверяем изменения с учетом того, что репозиторий может быть пустым
    has_repo_commits = has_commits(repo)
    # Фиксируем состояние изменений до автоматического добавления файлов
    working_tree_diffs = list(repo.index.diff(None))  # неиндексированные изменения
    untracked_files = list(repo.untracked_files)      # неотслеживаемые файлы
    staged_changes = list(repo.index.diff("HEAD")) if has_repo_commits else []  # уже проиндексированные изменения

    # Определяем, был ли изменён файл LAST_COMMIT (создан/изменён/проиндексирован)
    last_commit_changed = False
    # Изменения в рабочем дереве
    for diff in working_tree_diffs:
        if diff.a_path == 'LAST_COMMIT':
            last_commit_changed = True
            break
    # Если ещё не найден, проверяем неотслеживаемые файлы
    if not last_commit_changed:
        if 'LAST_COMMIT' in untracked_files:
            last_commit_changed = True
    # Если ещё не найден, проверяем уже проиндексированные изменения
    if not last_commit_changed and has_repo_commits:
        for diff in staged_changes:
            if diff.a_path == 'LAST_COMMIT':
                last_commit_changed = True
                break

    if untracked_files or working_tree_diffs or staged_changes:

        for diff in working_tree_diffs:
            repo.git.add(diff.a_path)

        for file in untracked_files:
            repo.git.add(file)

        # Показываем изменения только если есть коммиты
        if has_repo_commits:
            for diff in repo.index.diff("HEAD"):
                if diff.change_type == 'D':
                    print('+',  diff.a_path)
                elif diff.change_type == 'M':
                    print('*',  diff.a_path)
                elif diff.change_type == 'A':
                    print('-',  diff.a_path)
                else:
                    print(diff.change_type ,  diff.a_path)
        else:
            # Для первого коммита показываем все добавляемые файлы
            print("Первый коммит:")
            for file in repo.untracked_files:
                print('-', file)

        if os.path.exists(VERSION_FILE):
            with open(VERSION_FILE, 'r') as version_file:
                version_str = version_file.read()
        else:
            version_str = '0.0.0'

        version_split = version_str.split('.')

        version_split[-1] = str(int(version_split[-1]) + 1)

        version_str = '.'.join(version_split)

        with open(VERSION_FILE, 'w') as version_file:
            version_file.write(version_str)
        
        repo.git.add(VERSION_FILE) 

        # Формируем сообщение коммита с датой и временем
        current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        commit_message = f'{version_str} [{current_datetime}]'

        if len(sys.argv) > 1:
            commit_message = f'{commit_message}: {" ".join(sys.argv[1:])}'
        elif last_commit_changed and os.path.exists('LAST_COMMIT'):
            with open('LAST_COMMIT', 'r') as last_commit_file:
                last_commit_content = last_commit_file.read().strip()
                if last_commit_content:
                    commit_message = f'{commit_message}: {last_commit_content}'

        print(f'Commit: {commit_message}')

        repo.git.commit(m=commit_message)

    else:
        print('Nothing to commit!')
