# Генерация истории изменений

## Генератор истории изменений
Ссылка на библиотеку - [*auto-changelog*](https://github.com/KeNaCo/auto-changelog). Сгенерировать историю:

```shell
auto-changelog
```

Сгенерировать историю, включая коммиты без релиза

```shell
auto-changelog -u
```

## Установка версии

За установку версии генератором истории изменений отвечают [*git-теги*](https://git-scm.com/docs/git-tag). Проект содержит файл [*version.txt*](version.txt),
содержащий текущую версию. Чтобы установить тег версии, достаточно использовать [*update_version.py*](update_version.py):

```shell
python .\update_version.py
```

Удалить тег:

```shell
python .\update_version.py --remove
```

Посмотреть помощь по аргументам:

```shell
python .\update_version.py --help
```


Отправить тег в удаленный репозиторий ([*Stack Overflow*](https://stackoverflow.com/a/5195913/13186004)):

```shell
git push origin <tag_name>
git push origin 0.0.1
```


Отправить все теги в удаленный репозиторий:

```shell
git push --tags
```


# Генерация списка зависимостей

```shell
pip freeze > .\requirements.txt
```

## Использование списка зависимостей

```shell
pip install -r .\requirements.txt
```


# Первый запуск

1) установка зависимостей
    1) смотреть пункт [*Использование списка зависимостей*](#использование-списка-зависимостей)
2) инициализация БД
    1) используемая БД - `Postgres 15.1`
    2) ```shell
       python .\manage.py makemigrtions core python .\manage.py migrate
       ```
3) запуск
    1) смотреть пункт [*Запуск*](#запуск)


# Запуск

```shell
python .\start.py
```

# Документация

1) [*VERSION.md*](VERSION.md) - планы (и история) относительно версий
2) [*CHANGELOG.md*](CHANGELOG.md) - история изменений (генерируется - смотреть пункт [*Генерация истории изменений*](#генерация-истории-изменений))

# Другое

1) simulator - симуляция мира
2) player - воспроизведение истории мира
3) core - общее для всего проекта
4) [*пример*](https://github.com/pyglet/pyglet/blob/master/setup.py) setup.py
