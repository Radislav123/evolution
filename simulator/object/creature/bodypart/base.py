from simulator.world_resource.base import BaseWorldResource, CARBON, HYDROGEN, OXYGEN
import abc


class BaseBodypart(abc.ABC):
    # https://ru.wikipedia.org/wiki/%D0%A5%D0%B8%D0%BC%D0%B8%D1%87%D0%B5%D1%81%D0%BA%D0%B0%D1%8F_%D0%BE%D1%80%D0%B3%D0%B0%D0%BD%D0%B8%D0%B7%D0%B0%D1%86%D0%B8%D1%8F_%D0%BA%D0%BB%D0%B5%D1%82%D0%BA%D0%B8
    # ресурсы, из которых состоит часть тела (химический состав)
    _composition: dict[BaseWorldResource, int]
    extra_storage_coef = 0.1

    def __init__(self, size: float):
        self.size = size

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}"

    @property
    def resources(self) -> dict[BaseWorldResource, int]:
        resources = {}
        for resource, amount in self._composition.items():
            resources[resource] = int(amount * self.size)
        return resources

    @property
    def volume(self) -> int:
        return sum([resource.volume * amount for resource, amount in self.resources.items()])

    @property
    def mass(self) -> int:
        return sum([resource.mass * amount for resource, amount in self.resources.items()])

    @property
    def extra_storage(self) -> dict[BaseWorldResource, int]:
        """Расширение хранилища существа, которое предоставляет часть тела."""

        return {resource: int(amount * self.extra_storage_coef) for resource, amount in self.resources.items()}


class Body(BaseBodypart):
    _composition = {
        OXYGEN: 70,
        CARBON: 20,
        HYDROGEN: 10
    }
