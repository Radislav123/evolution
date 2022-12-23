import abc
import copy
from typing import Optional, TYPE_CHECKING, Type

from simulator.world_resource import BaseWorldResource, CARBON, HYDROGEN, OXYGEN


if TYPE_CHECKING:
    from simulator.object.creature import BaseSimulationCreature


class BaseBodypart(abc.ABC):
    # https://ru.wikipedia.org/wiki/%D0%A5%D0%B8%D0%BC%D0%B8%D1%87%D0%B5%D1%81%D0%BA%D0%B0%D1%8F_%D0%BE%D1%80%D0%B3%D0%B0%D0%BD%D0%B8%D0%B7%D0%B0%D1%86%D0%B8%D1%8F_%D0%BA%D0%BB%D0%B5%D1%82%D0%BA%D0%B8
    # ресурсы, из которых состоит часть тела (химический состав)
    _composition: dict[BaseWorldResource, int]
    damage: dict[BaseWorldResource, int]
    required_bodypart_class: Type["BaseBodypart"] | None
    extra_storage_coef = 0.1

    def __init__(self, size: float, required_bodypart: Optional["BaseBodypart"]):
        self.size = size
        # часть тела, к которой крепится данная
        self.required_bodypart: "BaseBodypart" = required_bodypart
        self.dependent_bodyparts: list["BaseBodypart"] = []

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}"

    @property
    def all_dependent(self) -> list["BaseBodypart"]:
        all_dependent = copy.copy(self.dependent_bodyparts)

        if len(self.dependent_bodyparts) > 0:
            for bodypart in self.dependent_bodyparts:
                all_dependent.extend(bodypart.all_dependent)
        return all_dependent

    @property
    def all_required(self) -> list["BaseBodypart"]:
        if self.required_bodypart is None:
            all_required = []
        else:
            all_required = [self.required_bodypart]
            all_required.extend(self.required_bodypart.all_required)
        return all_required

    def construct(self, bodyparts_classes: list[Type["BaseBodypart"]], creature: "BaseSimulationCreature"):
        for bodypart_class in bodyparts_classes:
            if bodypart_class.required_bodypart_class is self.__class__:
                self.dependent_bodyparts.append(
                    bodypart_class(creature.genome.effects.size, self)
                )

        bodyparts = copy.copy(bodyparts_classes)
        for bodypart in self.dependent_bodyparts:
            bodyparts.remove(bodypart.__class__)

        for bodypart in self.dependent_bodyparts:
            bodypart.construct(bodyparts, creature)

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
