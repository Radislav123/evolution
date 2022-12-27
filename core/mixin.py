from typing import Self, Type


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