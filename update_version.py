import git
import tap


def get_version() -> str:
    with open("version.txt", 'r') as version_file:
        version = version_file.read().strip()
    return version


class ArgumentParser(tap.Tap):
    message: str = ""  # сообщение, записываемое с тегом
    remove: bool = False  # если установлен, удаляет тег
    tag_name: str = get_version()  # задает специфичное, отличное от того, что указано в version.txt, имя тега


if __name__ == "__main__":
    arguments = ArgumentParser().parse_args()
    repository = git.Repo()
    if arguments.remove:
        removing_tag = repository.tag(arguments.tag_name)
        repository.git.tag("-d", removing_tag)
        print(f"Удален тег {arguments.tag_name}")
    else:
        repository.create_tag(get_version(), message = arguments.message)
        message = f"Добавлен тег {arguments.tag_name}"
        if arguments.message:
            message += f" с сообщением \"{arguments.message}\""
        print(message)
