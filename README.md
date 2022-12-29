# Генерация истории изменений
`auto-changelog -u`


# Генерация списка зависимостей
`pip freeze > .\requirements.txt`

## Использование списка зависимостей
`pip install -r .\requirements.txt`


# Другое
1) simulator - симуляция мира
2) player - воспроизведение истории мира
3) core - общий сервис для simulator и player
4) установить `Arcade`
   1) `pip install arcade` - так установятся все зависимости, кроме `Pillow`
      1) текущая версия (2.5.7) `Arcade` требует версию `Pillow` 3.1.1, которая не устанавливается на python 3.11 сама
   2) `pip install pillow` - установить последнюю версию pillow
   3) `pip install arcade --no-dependencies` - установит сам `Arcade`
      1) https://stackoverflow.com/a/12759996/13186004
