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
`pip freeze > .\requirements.txt`

## Использование списка зависимостей
`pip install -r .\requirements.txt`


# Другое

1) simulator - симуляция мира
2) player - воспроизведение истории мира
3) core - общий сервис для simulator и player
4) существа иногда не "расползаются" после появления нового
    1) это связано с тем, что `__init__` не задает позицию существа в мире, она задается позже при старте
5) [*пример*](https://github.com/pyglet/pyglet/blob/master/setup.py) setup.py
