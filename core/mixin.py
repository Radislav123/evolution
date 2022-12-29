import abc
from typing import Self, Type

from core import models


# чтобы подкласс нашелся, его надо куда-нибудь импортировать (лучше в __init__.py)
class GetSubclassesMixin:
    @classmethod
    def get_all_subclasses(cls) -> list[Type[Self]]:
        """Возвращает все дочерние классы рекурсивно."""

        subclasses = cls.__subclasses__()
        children_subclasses = []
        for child in subclasses:
            children_subclasses.extend(child.get_all_subclasses())
        subclasses.extend(children_subclasses)
        return subclasses


class DatabaseSavableMixin(abc.ABC):
    db_model: Type[models.EvolutionModel]
    db_instance: models.EvolutionModel

    @abc.abstractmethod
    def save_to_db(self, *args, **kwargs):
        """Сохраняет или обновляет объект в БД."""

        raise NotImplementedError()


class WorldObjectMixin(abc.ABC):
    id: int

    @property
    def object_id(self):
        return f"{self.__class__.__name__}{self.id}"
