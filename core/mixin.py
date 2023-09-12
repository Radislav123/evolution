import abc
from typing import Generic, Type, TypeVar


T = TypeVar("T")


# если подкласс не в том же файле, что и родитель,
# чтобы подкласс нашелся, его надо куда-нибудь импортировать (лучше в __init__.py)
# не всегда работает из других файлов
class GetSubclassesMixin(Generic[T]):
    @classmethod
    def get_all_subclasses(cls) -> list[Type[T]]:
        """Возвращает все дочерние классы рекурсивно."""

        subclasses = cls.__subclasses__()
        children_subclasses = []
        for child in subclasses:
            children_subclasses.extend(child.get_all_subclasses())
        subclasses.extend(children_subclasses)
        return subclasses


class ApplyDescriptorMixin:
    # использование этого метода подразумевается только для интерфейсов
    @classmethod
    def apply_descriptor(cls, descriptor: dict) -> None:
        for key, value in descriptor.items():
            setattr(cls, key, value)


class WorldObjectMixin(abc.ABC):
    id: int = None

    @property
    def object_id(self):
        return f"{self.__class__.__name__}{self.id}"
