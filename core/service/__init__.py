import glob
import json
from typing import Generic, TypeVar


VT = TypeVar("VT")


class ObjectDescriptionReader(Generic[VT]):
    DEFAULT_FOLDER = "object_descriptions"

    @staticmethod
    def read_file(path: str) -> dict:
        with open(path, 'r') as file:
            data = json.load(file)
        return data

    @classmethod
    def read_folder(cls, folder: str) -> dict:
        pattern = f"{cls.DEFAULT_FOLDER}/{folder}/*.json"
        values = []
        for file in glob.glob(pattern):
            values.extend(cls.read_file(file)["values"])
        return {"values": values}

    @classmethod
    def read_folder_to_dict(cls, folder: str, descriptor: type = dict) -> dict[str, VT]:
        """Считывает все json-файлы в папке."""

        json_dict = cls.read_folder(folder)
        return {x["name"]: descriptor(**x) for x in json_dict["values"]}

    @classmethod
    def read_folder_to_list(cls, folder: str, descriptor: type = dict) -> list[VT]:
        """Считывает все json-файлы в папке."""

        return [x for x in cls.read_folder_to_dict(folder, descriptor).values()]
