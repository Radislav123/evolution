import abc
import copy
from typing import Optional, TYPE_CHECKING, Type

from simulator.world_resource import CARBON, ENERGY, HYDROGEN, OXYGEN, Resources


if TYPE_CHECKING:
    from simulator.creature import SimulationCreature


# todo: rename to BodyPart
class BaseBodypart(abc.ABC):
    # https://ru.wikipedia.org/wiki/%D0%A5%D0%B8%D0%BC%D0%B8%D1%87%D0%B5%D1%81%D0%BA%D0%B0%D1%8F_%D0%BE%D1%80%D0%B3%D0%B0%D0%BD%D0%B8%D0%B7%D0%B0%D1%86%D0%B8%D1%8F_%D0%BA%D0%BB%D0%B5%D1%82%D0%BA%D0%B8
    # ресурсы, из которых состоит часть тела (химический состав)
    _composition: Resources
    required_bodypart_class: Type["BaseBodypart"] | None
    extra_storage_coeff = 0.1

    def __init__(self, size: float, required_bodypart: Optional["BaseBodypart"]):
        self.size = size
        # часть тела, к которой крепится данная
        self.required_bodypart: "BaseBodypart" = required_bodypart
        self.dependent_bodyparts: list["BaseBodypart"] = []
        self._all_dependent: list["BaseBodypart"] | None = None
        self._all_required: list["BaseBodypart"] | None = None

        # уничтожена ли часть тела полностью
        self.destroyed = False
        # построены ли зависимости методом construct
        # устанавливается в положение True только в методе SimulationCreature.apply_bodyparts
        self.constructed = False

        self.damage = Resources()
        # ресурсы, находящиеся в неповрежденной части тела/необходимые для воспроизводства части тела
        self.resources = (self._composition * self.size).round()
        # расширение хранилища существа, которое предоставляет часть тела
        self.extra_storage = (self.resources * self.extra_storage_coeff).round()
        self._remaining_resources: Resources | None = None

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}"

    @property
    # должно использоваться только в make_damage(), для всех остальных случаев есть destroyed
    def _present(self) -> bool:
        """Показывает, присутствует ли часть тела относительно нанесенного ей урона."""

        present = True
        for resource, amount in self.resources.items():
            if amount <= self.damage[resource]:
                present = False
                break
        return present

    @property
    def damaged(self) -> bool:
        """Проверяет, нанесен ли урон части тела."""

        damaged = False
        for amount in self.damage.values():
            if amount > 0:
                damaged = True
                break
        return damaged

    @property
    def remaining_resources(self) -> Resources:
        """Ресурсы, находящиеся в части тела сейчас."""

        if self._remaining_resources is None:
            self._remaining_resources = self.resources - self.damage
        return self._remaining_resources

    @property
    def all_required(self) -> list["BaseBodypart"]:
        if self._all_required is None or not self.constructed:
            if self.required_bodypart is None:
                self._all_required = []
            else:
                self._all_required = [self.required_bodypart]
                self._all_required.extend(self.required_bodypart.all_required)
        return self._all_required

    @property
    def all_dependent(self) -> list["BaseBodypart"]:
        if self._all_dependent is None or not self.constructed:
            self._all_dependent = copy.copy(self.dependent_bodyparts)
            if len(self.dependent_bodyparts) > 0:
                for bodypart in self.dependent_bodyparts:
                    self._all_dependent.extend(bodypart.all_dependent)
        return self._all_dependent

    @property
    def volume(self) -> int:
        if not self.destroyed:
            # todo: можно добавить кэширование (аккуратнее с хранилищами)
            volume = int(sum([resource.volume * amount for resource, amount in self.resources.items()]))
        else:
            volume = 0
        return volume

    @property
    def mass(self) -> int:
        if not self.destroyed:
            # todo: можно добавить кэширование (аккуратнее с хранилищами)
            mass = sum([resource.mass * amount for resource, amount in self.remaining_resources.items()])
        else:
            mass = 0
        return mass

    def construct(self, bodypart_classes: list[Type["BaseBodypart"]], creature: "SimulationCreature"):
        """Собирает тело, устанавливая ссылки на зависимые и необходимые части тела."""

        for bodypart_class in bodypart_classes:
            if bodypart_class.required_bodypart_class is self.__class__:
                self.dependent_bodyparts.append(
                    bodypart_class(creature.genome.effects.size_coeff, self)
                )

        bodyparts = copy.copy(bodypart_classes)
        for bodypart in self.dependent_bodyparts:
            bodyparts.remove(bodypart.__class__)

        for bodypart in self.dependent_bodyparts:
            bodypart.construct(bodyparts, creature)

    def destroy(self) -> Resources:
        """Уничтожает часть тела и все зависимые."""

        return_resources = self.remaining_resources
        self._remaining_resources = None
        for dependent in self.dependent_bodyparts:
            return_resources += dependent.destroy()
        self.destroyed = True
        self.damage = copy.copy(self.resources)
        return return_resources

    # если возвращаемые ресурсы != 0, значит часть тела уничтожена, а эти ресурсы являются ресурсами,
    # полученными после уничтожения части тела и всех зависимых частей
    # если возвращаемые ресурсы < 0, данная часть тела и все ее зависимые части не могут покрыть нанесенного урона
    def make_damage(self, damaging_resources: Resources) -> Resources:
        self._remaining_resources = None
        self.damage += damaging_resources
        if not self._present:
            return_resources = copy.copy(damaging_resources)
            return_resources += self.destroy()
        else:
            return_resources = Resources()
        return return_resources

    # если возвращаемые ресурсы != 0, значит эти ресурсы не израсходованы при регенерации
    def regenerate(self, resources: Resources) -> Resources:
        self._remaining_resources = None
        regenerating_resources = copy.copy(resources)
        for resource, amount in resources.items():
            if self.damage[resource] < amount:
                regenerating_resources[resource] = self.damage[resource]

        self.damage -= regenerating_resources
        if self._present:
            self.destroyed = False

        return resources - regenerating_resources


class Body(BaseBodypart):
    _composition = Resources(
        {
            OXYGEN: 70,
            CARBON: 20,
            HYDROGEN: 10,
            # todo: убрать энергию отсюда, когда будут синтезируемые вещества
            ENERGY: 100
        }
    )
