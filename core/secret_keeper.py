import json

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    pass


class SecretKeeper:
    class Module:
        name: str
        secrets_path: str
        json: dict
        secret_keeper: "SecretKeeper"

        def get_dict(self) -> dict:
            return self.json

    class Database(Module):
        ENGINE: str
        NAME: str
        USER: str
        PASSWORD: str
        HOST: str
        PORT: str

    # объекты секретов
    database: Database

    # пути секретов
    SECRETS_FOLDER = "secrets"

    DATABASE_SECRETS_FOLDER = f"{SECRETS_FOLDER}/database"
    DATABASE_CREDENTIALS_PATH = f"{DATABASE_SECRETS_FOLDER}/credentials.json"

    def __init__(self) -> None:
        self.add_module("database", self.DATABASE_CREDENTIALS_PATH)

    @staticmethod
    def read_json(path: str) -> dict:
        with open(path, 'r') as file:
            data = json.load(file)
        return data

    def add_module(self, name: str, secrets_path: str) -> None:
        json_dict = self.read_json(secrets_path)
        module = type(name, (self.Module,), json_dict)()
        module.name = name
        module.secrets_path = secrets_path
        module.json = json_dict
        module.secret_keeper = self
        setattr(self, name, module)
