from core.force_server_update import update_file


def reload_server():
    # дописывает строку
    with open("core/force_server_update/update_file.py", "r+") as file:
        data = file.read()
        file.write("\n")
    # возвращает исходный текст файла
    # должно быть именно в два захода, чтобы изменение файла было замечено django
    with open("core/force_server_update/update_file.py", "w") as file:
        file.write(data)
