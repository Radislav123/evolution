import json
from typing import TypeVar, Generic


VT = TypeVar("VT")


class ObjectDescriptionReader(Generic[VT]):
    @staticmethod
    def read_file(path: str) -> dict:
        with open(path, 'r') as file:
            data = json.load(file)
        return data

    @classmethod
    def read_file_to_dict(cls, path: str, descriptor: type) -> dict[str, VT]:
        json_dict = cls.read_file(path)
        return {x["name"]: descriptor(**x) for x in json_dict["values"]}

    @classmethod
    def read_file_to_list(cls, path: str, descriptor: type) -> list[VT]:
        json_dict = cls.read_file(path)
        return [descriptor(**x) for x in json_dict["values"]]

