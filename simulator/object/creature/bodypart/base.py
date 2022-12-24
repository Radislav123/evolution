import abc
import copy
from typing import Optional, TYPE_CHECKING, Type

from simulator.world_resource import BaseWorldResource, CARBON, HYDROGEN, OXYGEN, ENERGY


if TYPE_CHECKING:
    from simulator.object.creature import BaseSimulationCreature


class BaseBodypart(abc.ABC):
    # https://ru.wikipedia.org/wiki/%D0%A5%D0%B8%D0%BC%D0%B8%D1%87%D0%B5%D1%81%D0%BA%D0%B0%D1%8F_%D0%BE%D1%80%D0%B3%D0%B0%D0%BD%D0%B8%D0%B7%D0%B0%D1%86%D0%B8%D1%8F_%D0%BA%D0%BB%D0%B5%D1%82%D0%BA%D0%B8
    # ресурсы, из которых состоит часть тела (химический состав)
    _composition: dict[BaseWorldResource, int]
    destroyed = False
    required_bodypart_class: Type["BaseBodypart"] | None
    extra_storage_coef = 0.1

    def __init__(self, size: float, required_bodypart: Optional["BaseBodypart"]):
        self.size = size
        # часть тела, к которой крепится данная
        self.required_bodypart: "BaseBodypart" = required_bodypart
        self.dependent_bodyparts: list["BaseBodypart"] = []

        self.damage: dict[BaseWorldResource, int] = {}
        for resource in self._composition:
            self.damage[resource] = 0

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}"

    # если возвращается отрицательное количество ресурса, значит его не хватает
    # даже с учетом уничтожения зависимых частей тела
    def make_damage(self, damaging_resources: dict[BaseWorldResource, int]) -> dict[BaseWorldResource, int]:
        for resource in damaging_resources:
            self.damage[resource] += damaging_resources[resource]
        if not self.present:
            returned_resources = self.destroy()
        else:
            returned_resources = {}

        return returned_resources

    @property
    def present(self) -> bool:
        """Показывает, присутствует ли часть тела относительно нанесенного ей урона."""

        present = True
        for resource in self.resources:
            if self.resources[resource] <= self.damage[resource]:
                present = False
                break
        return present

    def destroy(self) -> dict[BaseWorldResource, int]:
        """Уничтожает часть тела и все зависимые."""
        return_resources = {resource: amount - self.damage[resource] for resource, amount in self.resources.items()}
        for dependent in self.dependent_bodyparts:
            dependent_return_resources = dependent.destroy()
            for resource, amount in dependent_return_resources.items():
                if resource not in return_resources:
                    return_resources[resource] = amount
                else:
                    return_resources[resource] += amount
        self.destroyed = True
        return return_resources

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
        if self.present:
            volume = sum([resource.volume * amount for resource, amount in self.resources.items()])
        else:
            volume = 0
        return volume

    @property
    def mass(self) -> int:
        if self.present:
            mass = sum(
                [resource.mass * (amount - self.damage[resource]) for resource, amount in self.resources.items()]
            )
        else:
            mass = 0
        return mass

    @property
    def extra_storage(self) -> dict[BaseWorldResource, int]:
        """Расширение хранилища существа, которое предоставляет часть тела."""

        if self.present:
            extra_storage = {
                resource: int(amount * self.extra_storage_coef) for resource, amount in self.resources.items()
            }
        else:
            extra_storage = {}
        return extra_storage


class Body(BaseBodypart):
    _composition = {
        OXYGEN: 70,
        CARBON: 20,
        HYDROGEN: 10,
        # todo: убрать энергию отсюда, когда будут синтезируемые вещества
        ENERGY: 100
    }
