import glob
import json
from typing import Generic, TypeVar
from arcade import SpriteList, SpriteType


VT = TypeVar("VT")

# кэш для загрузки файлов
VALUES_CACHE = {}


# поля начинающиеся с '_' считаются комментариями
class ObjectDescriptionReader(Generic[VT]):
    @staticmethod
    def read_file(path: str) -> dict:
        with open(path, 'r') as file:
            data = json.load(file)
        return data

    @classmethod
    def read_folder(cls, folder: str) -> dict[str, list[dict]]:
        pattern = f"{folder}/*.json"
        if pattern not in VALUES_CACHE:
            values = []
            for file in glob.glob(pattern):
                values.extend(cls.read_file(file)["values"].values())
            VALUES_CACHE[pattern] = values

        return {"values": VALUES_CACHE[pattern]}

    @classmethod
    def read_folder_to_dict(cls, folder: str, descriptor: type) -> dict[str, VT]:
        """Считывает все json-файлы в папке."""

        json_dict = cls.read_folder(folder)
        return {x["name"]: descriptor(**x) for x in json_dict["values"]}

    @classmethod
    def read_folder_to_list(cls, folder: str, descriptor: type = dict) -> list[VT]:
        """Считывает все json-файлы в папке."""

        return list(cls.read_folder_to_dict(folder, descriptor).values())


class EvolutionSpriteList(SpriteList[SpriteType]):
    def __repr__(self) -> str:
        return repr(self.sprite_list)
