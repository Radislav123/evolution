import copy
from typing import Optional, TYPE_CHECKING, Type

from core.mixin import ApplyDescriptorMixin, GetSubclassesMixin
from core.service import ObjectDescriptionReader
from evolution import settings
from simulator.world_resource import RESOURCE_DICT, Resources, WorldResource


if TYPE_CHECKING:
    from simulator.creature import SimulationCreature

bodypart_interface_descriptors = ObjectDescriptionReader[dict]().read_folder_to_dict(
    settings.BODYPART_INTERFACE_DESCRIPTIONS_PATH,
    dict
)
bodypart_descriptors = ObjectDescriptionReader[dict]().read_folder_to_dict(
    settings.BODYPART_DESCRIPTIONS_PATH,
    dict
)


class BodypartInterface(GetSubclassesMixin["BodypartInterface"], ApplyDescriptorMixin):
    name = "bodypart_interface"
    # название интерфейса, определяющего часть тела
    interface: str
    # https://ru.wikipedia.org/wiki/%D0%A5%D0%B8%D0%BC%D0%B8%D1%87%D0%B5%D1%81%D0%BA%D0%B0%D1%8F_%D0%BE%D1%80%D0%B3%D0%B0%D0%BD%D0%B8%D0%B7%D0%B0%D1%86%D0%B8%D1%8F_%D0%BA%D0%BB%D0%B5%D1%82%D0%BA%D0%B8
    # ресурсы, из которых состоит часть тела (химический состав) при размере (size_coeff) равном 1.0
    composition: dict[str, int]
    required_bodypart: str
    extra_storage_coeff: float

    def __init__(self, creature: "SimulationCreature", required_bodypart: Optional["BodypartInterface"]) -> None:
        self.creature = creature
        self.size_coeff = self.creature.genome.effects.size_coeff
        # часть тела, к которой крепится данная
        self.required_bodypart: "BodypartInterface" = required_bodypart
        self.dependent_bodyparts: list["BodypartInterface"] = []
        self._all_dependent: list["BodypartInterface"] | None = None
        self._all_required: list["BodypartInterface"] | None = None

        # уничтожена ли часть тела полностью
        self.destroyed = False
        # построены ли зависимости методом construct
        # устанавливается в положение True только в методе SimulationCreature.apply_bodyparts
        self.constructed = False

        self.damage = Resources()
        # ресурсы, находящиеся в неповрежденной части тела/необходимые для воспроизводства части тела
        # при размере (size_coeff) равном 1.0 соответствует composition
        self.resources = (
                Resources(
                    {RESOURCE_DICT[resource_name]: amount for resource_name, amount in self.composition.items()}
                ) * self.size_coeff
        ).round()
        # расширение хранилища существа, которое предоставляет часть тела
        self.extra_storage = (self.resources * self.extra_storage_coeff).round()
        self._remaining_resources: Resources | None = None

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}"

    @classmethod
    def construct_body(cls, creature: "SimulationCreature") -> "BodypartInterface":
        """Создает часть тела "тело"."""

        return BODYPART_CLASSES["body"](creature, None)

    @property
    # должно использоваться только в make_damage() и regenerate(), для всех остальных случаев есть destroyed
    def present(self) -> bool:
        """Показывает, присутствует ли часть тела относительно нанесенного ей урона."""

        for resource, amount in self.resources.items():
            if amount <= self.damage[resource]:
                present = False
                break
        else:
            present = True
        return present

    @property
    def damaged(self) -> bool:
        """Проверяет, нанесен ли урон части тела."""

        for amount in self.damage.values():
            if amount > 0:
                damaged = True
                break
        else:
            damaged = False
        return damaged

    @property
    def remaining_resources(self) -> Resources:
        """Ресурсы, находящиеся в части тела сейчас."""

        if self._remaining_resources is None:
            self._remaining_resources = self.resources - self.damage
        return self._remaining_resources

    @property
    def all_required(self) -> list["BodypartInterface"]:
        """Цепочка частей тела, к которой прикреплена данная часть тела."""

        if self._all_required is None or not self.constructed:
            if self.required_bodypart is None:
                self._all_required = []
            else:
                self._all_required = [self.required_bodypart]
                self._all_required.extend(self.required_bodypart.all_required)
        return self._all_required

    @property
    def all_dependent(self) -> list["BodypartInterface"]:
        """Список частей тела, прикрепленных к данной напрямую или через другие части тела."""

        if self._all_dependent is None or not self.constructed:
            self._all_dependent = copy.copy(self.dependent_bodyparts)
            for bodypart in self.dependent_bodyparts:
                self._all_dependent.extend(bodypart.all_dependent)
        return self._all_dependent

    @property
    def volume(self) -> int:
        if not self.destroyed:
            # todo: можно добавить кэширование (аккуратнее с хранилищами)
            volume = int(sum(resource.volume * amount for resource, amount in self.resources.items()))
        else:
            volume = 0
        return volume

    @property
    def mass(self) -> int:
        if not self.destroyed:
            # todo: можно добавить кэширование (аккуратнее с хранилищами)
            mass = int(sum(resource.mass * amount for resource, amount in self.remaining_resources.items()))
        else:
            mass = 0
        return mass

    def construct(self, bodypart_names: list[str]) -> None:
        """Собирает тело, устанавливая ссылки на зависимые и необходимые части тела."""

        bodypart_names = copy.copy(bodypart_names)
        for bodypart_name in bodypart_names:
            if (body_part_class := BODYPART_CLASSES[bodypart_name]).required_bodypart == self.name:
                self.dependent_bodyparts.append(
                    body_part_class(self.creature, self)
                )

        for bodypart in self.dependent_bodyparts:
            bodypart_names.remove(bodypart.name)

        for bodypart in self.dependent_bodyparts:
            bodypart.construct(bodypart_names)

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
        if not self.present:
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
        if self.present:
            self.destroyed = False

        return resources - regenerating_resources


class AddToNonExistentStoragesException(Exception):
    """Исключение для Storage."""

    def __init__(self, message: str):
        super().__init__(message)
        self.resources = Resources()


class AddToDestroyedStorageException(Exception):
    """Исключение для ResourceStorage."""

    def __init__(self, world_resource: WorldResource, amount: int, message: str):
        super().__init__(message)
        self.world_resource = world_resource
        self.amount = amount


class StorageNotFoundException(Exception):
    pass


class StorageInterface(BodypartInterface):
    name = "storage_interface"

    def __init__(self, creature, required_bodypart) -> None:
        super().__init__(creature, required_bodypart)
        self._storage: dict[WorldResource, ResourceStorageInterface] = {}
        self._stored_resources: Resources | None = None
        self._extra_resources: Resources | None = None
        self._lack_resources: Resources | None = None
        self._fullness: Resources | None = None

    def __repr__(self) -> str:
        string = f"{super().__repr__()}: "
        if len(self._storage) > 0:
            for storage in self.values():
                if storage.destroyed:
                    string += f"{storage.world_resource.formula}: destroyed, "
                else:
                    string += f"{storage.world_resource.formula}: {storage.current}/{storage.capacity}, "
        else:
            string += "empty"
        if string[-2:] == ", ":
            string = string[:-2]
        return string

    def __getitem__(self, item):
        return self._storage[item]

    def __iter__(self):
        return iter(self._storage)

    @classmethod
    def find_storage(cls, bodyparts: list["BodypartInterface"]) -> "StorageInterface":
        """Находит хранилище (storage) в списке частей тела."""

        for bodypart in bodyparts:
            if bodypart.name == "storage":
                break
        else:
            raise StorageNotFoundException()
        # noinspection PyTypeChecker
        return bodypart

    @property
    def stored_resources(self) -> Resources:
        if self._stored_resources is None:
            self._stored_resources = Resources({x.world_resource: x.current for x in self._storage.values()})
        return self._stored_resources

    @property
    def extra_resources(self) -> Resources:
        if self._extra_resources is None:
            self._extra_resources = Resources({x.world_resource: x.extra for x in self._storage.values()})
        return self._extra_resources

    @property
    def lack_resources(self) -> Resources:
        if self._lack_resources is None:
            self._lack_resources = Resources({x.world_resource: x.lack for x in self._storage.values()})
        return self._lack_resources

    @property
    def fullness(self) -> Resources:
        if self._fullness is None:
            self._fullness = Resources({x.world_resource: x.fullness for x in self._storage.values()})
        return self._fullness

    def items(self):
        return self._storage.items()

    def keys(self):
        return self._storage.keys()

    def values(self):
        return self._storage.values()

    def add_resource_storage(self, resource: WorldResource):
        """Присоединяет хранилище ресурса к общему."""

        # noinspection PyTypeChecker,PyArgumentList
        resource_storage: ResourceStorageInterface = BODYPART_CLASSES["resource_storage"](self.creature, self, resource)
        self._storage[resource] = resource_storage
        self.dependent_bodyparts.append(resource_storage)

    def add_resources(self, resources: Resources):
        self.reset_cache()
        not_added_resources = Resources()
        for resource, amount in resources.items():
            if amount > 0:
                try:
                    self._storage[resource].add(amount)
                except AddToDestroyedStorageException as exception:
                    not_added_resources[exception.world_resource] = exception.amount
            elif amount < 0:
                raise ValueError(f"Adding resource ({resource}) must be not negative ({amount}). {self}")
        if len(not_added_resources) > 0:
            common_exception = AddToNonExistentStoragesException(f"{not_added_resources} can not be added to {self}")
            common_exception.resources = not_added_resources
            raise common_exception

    def remove_resources(self, resources: Resources):
        self.reset_cache()
        for resource, amount in resources.items():
            if amount > 0:
                self._storage[resource].remove(amount)
            elif amount < 0:
                raise ValueError(f"Removing resource ({resource}) must be not negative ({amount}). {self}")

    def reset_cache(self):
        self._stored_resources = None
        self._extra_resources = None
        self._lack_resources = None
        self._fullness = None


class ResourceStorageInterface(BodypartInterface):
    name = "resource_storage_interface"
    world_resource: WorldResource
    capacity: int
    # показывает дополнительное увеличение объема части тела (хранилища), в зависимости от вместимости
    extra_volume_coeff: float

    def __init__(self, creature, required_bodypart, world_resource: WorldResource) -> None:
        super().__init__(creature, required_bodypart)

        self.world_resource = world_resource
        self.current = 0

    def __repr__(self) -> str:
        string = f"{repr(self.world_resource)}Storage: "
        if self.destroyed:
            string += "destroyed"
        else:
            string += f"{self.current}/{self.capacity}"
        return string

    @property
    def fullness(self) -> float:
        return self.current / self.capacity

    @property
    def full(self) -> bool:
        return self.current >= self.capacity

    @property
    def empty(self) -> bool:
        return self.current <= 0

    @property
    def extra(self) -> int:
        if self.full:
            extra = self.current - self.capacity
        else:
            extra = 0
        return extra

    @property
    def lack(self) -> int:
        if self.empty:
            lack = -self.current
        else:
            lack = 0
        return lack

    @property
    def volume(self) -> int:
        volume = super().volume
        volume += int(self.world_resource.volume * self.capacity * self.extra_volume_coeff)
        return volume

    @property
    def mass(self) -> int:
        mass = super().mass
        mass += self.world_resource.mass * self.current
        return mass

    def add(self, amount: int):
        if not self.destroyed:
            self.current += amount
        else:
            raise AddToDestroyedStorageException(self.world_resource, amount, f"{self}")

    def remove(self, amount: int):
        if not self.destroyed:
            self.current -= amount
        else:
            raise ValueError(f"{self}")

    def reset(self):
        self.current = 0

    def destroy(self) -> Resources:
        return_resources = super().destroy()
        return_resources[self.world_resource] += self.current
        self.reset()
        return return_resources


# noinspection DuplicatedCode
BODYPART_INTERFACE_CLASSES: dict[str, Type[BodypartInterface]] = {
    x.name: x for x in BodypartInterface.get_all_subclasses()
}
BODYPART_INTERFACE_CLASSES[BodypartInterface.name] = BodypartInterface
# обновляются данные в интерфейсах
BodypartInterface.apply_descriptor(bodypart_interface_descriptors[BodypartInterface.name])
for name, bodypart_interface_class in BODYPART_INTERFACE_CLASSES.items():
    bodypart_interface_class.apply_descriptor(bodypart_interface_descriptors[name])

# создаются классы частей тела
BODYPART_CLASSES: dict[str, Type[BodypartInterface]] = {
    x["name"]: type(x["name"], (BODYPART_INTERFACE_CLASSES[x["interface"]],), x)
    for x in bodypart_descriptors.values()
}
# обновляются данные в классах генов
for name, bodypart_class in BODYPART_CLASSES.items():
    bodypart_class.apply_descriptor(bodypart_descriptors[name])
