import copy
import statistics
from typing import ItemsView, KeysView, Optional, TYPE_CHECKING, Type, ValuesView

from core.mixin import ApplyDescriptorMixin, GetSubclassesMixin
from core.service import ObjectDescriptionReader
from evolution import settings
from simulator.world_resource import RESOURCE_DICT, Resources, WorldResource


if TYPE_CHECKING:
    from simulator.creature import Creature

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

    def __init__(self, creature: "Creature", required_bodypart: Optional["BodypartInterfaceClass"]) -> None:
        self.creature = creature
        self.size_coeff = self.creature.genome.effects.size_coeff
        # часть тела, к которой крепится данная
        self.required_bodypart: BodypartInterfaceClass = required_bodypart
        self.dependent_bodyparts: list["BodypartInterfaceClass"] = []
        self._all_dependent: list["BodypartInterfaceClass"] | None = None
        self._all_required: list["BodypartInterfaceClass"] | None = None
        self._volume: float | None = None
        self._mass: float | None = None

        # уничтожена ли часть тела полностью
        self.destroyed = False
        # построены ли зависимости методом construct
        # устанавливается в положение True только в методе Creature.apply_bodyparts
        self.constructed = False

        self.damage = Resources[int]()
        # ресурсы, находящиеся в неповрежденной части тела/необходимые для воспроизводства части тела
        # при размере (size_coeff) равном 1.0 соответствует composition
        self.resources = (
                Resources[int](
                    {RESOURCE_DICT[resource_name]: amount for resource_name, amount in self.composition.items()}
                ) * self.size_coeff
        ).round()
        # расширение хранилища существа, которое предоставляет часть тела
        self.extra_storage = (self.resources * self.extra_storage_coeff).round()
        self._remaining_resources: Resources[int] | None = None

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}"

    @classmethod
    def construct_body(cls, creature: "Creature") -> "BodypartInterface":
        """Создает часть тела "тело"."""

        return BODYPART_CLASSES["body"](creature, None)

    @property
    def remaining_resources(self) -> Resources[int]:
        """Ресурсы, находящиеся в части тела сейчас."""

        if self._remaining_resources is None:
            self._remaining_resources = self.resources - self.damage
        return self._remaining_resources

    @property
    def all_required(self) -> list["BodypartInterfaceClass"]:
        """Цепочка частей тела, к которой прикреплена данная часть тела."""

        if self._all_required is None or not self.constructed:
            if self.required_bodypart is None:
                self._all_required = []
            else:
                self._all_required = [self.required_bodypart]
                self._all_required.extend(self.required_bodypart.all_required)
        return self._all_required

    @property
    def all_dependent(self) -> list["BodypartInterfaceClass"]:
        """Список частей тела, прикрепленных к данной напрямую или через другие части тела."""

        if self._all_dependent is None or not self.constructed:
            self._all_dependent = copy.copy(self.dependent_bodyparts)
            for bodypart in self.dependent_bodyparts:
                self._all_dependent.extend(bodypart.all_dependent)
        return self._all_dependent

    @property
    def volume(self) -> float:
        if self._volume is None:
            self._volume = sum(resource.volume * amount for resource, amount in self.remaining_resources.items())
        return self._volume

    @property
    def mass(self) -> float:
        if self._mass is None:
            self._mass = sum(resource.mass * amount for resource, amount in self.remaining_resources.items())
        return self._mass

    def construct(self, bodypart_names: list[str]) -> None:
        """Собирает тело, устанавливая ссылки на зависимые и необходимые части тела."""

        bodypart_names = copy.copy(bodypart_names)
        for bodypart_name in bodypart_names:
            if (body_part_class := BODYPART_CLASSES[bodypart_name]).required_bodypart == self.name:
                self.dependent_bodyparts.append(body_part_class(self.creature, self))

        for bodypart in self.dependent_bodyparts:
            bodypart_names.remove(bodypart.name)

        for bodypart in self.dependent_bodyparts:
            bodypart.construct(bodypart_names)

    def destroy(self) -> Resources[int]:
        """Уничтожает часть тела и все зависимые."""

        return_resources = self.remaining_resources
        if not self.destroyed:
            if self in self.creature.damaged_bodyparts:
                self.creature.damaged_bodyparts.remove(self)
            elif self in self.creature.not_damaged_bodyparts:
                self.creature.not_damaged_bodyparts.remove(self)
            else:
                raise ValueError("Destroying bodypart not in damaged_bodyparts and not_damaged_bodyparts.")
            self.creature.present_bodyparts.remove(self)
            self.creature.destroyed_bodyparts.add(self)

            self.reset_resources_cache()
            self.reset_physic_cache()
            # не переходить на self.all_dependent,
            # потому что части тела (например ResourcesStorage) могут переопределять self.destroy
            for dependent in self.dependent_bodyparts:
                return_resources += dependent.destroy()
            self.destroyed = True
            self.damage = copy.copy(self.resources)
        return return_resources

    # todo: урон существу от внешних факторов (внешние условия, другие существа,..) должен наноситься
    #  только после обработки всех существ
    # если возвращаемые ресурсы != 0, значит часть тела уничтожена, а эти ресурсы являются ресурсами,
    # полученными после уничтожения части тела и всех зависимых частей
    def make_damage(self, damaging_resources: Resources[int]) -> Resources[int]:
        if sum(damaging_resources.values()) > 0:
            self.damage += damaging_resources
            self.reset_resources_cache()
            self.reset_physic_cache()
            for resource in self.resources:
                if self.damage[resource] > self.resources[resource]:
                    raise ValueError(
                        f"Bodypart damage {self.damage} can not be greater then resources {self.resources}."
                    )

            # часть тела не выдержала урона и была уничтожена
            if sum(self.remaining_resources.values()) == 0:
                return_resources = self.destroy()
            # часть тела осталась не уничтоженной
            else:
                if self in self.creature.not_damaged_bodyparts:
                    self.creature.not_damaged_bodyparts.remove(self)
                    self.creature.damaged_bodyparts.add(self)
                return_resources = Resources[int]()
        # часть тела не получила урона
        else:
            return_resources = Resources[int]()

        return return_resources

    # если возвращаемые ресурсы != 0, значит эти ресурсы не израсходованы при регенерации
    def regenerate(self, resources: Resources[int]) -> Resources[int]:
        # поправка на урон части тела
        regenerating_resources = Resources[int](
            {resource: min(amount, self.damage[resource]) for resource, amount in resources.items()}
        )

        if sum(regenerating_resources.values()) > 0:
            self.damage -= regenerating_resources
            self.reset_resources_cache()
            self.reset_physic_cache()

            self.creature.present_bodyparts.add(self)
            if self.destroyed:
                self.destroyed = False
                self.creature.destroyed_bodyparts.remove(self)
                # часть тела еще не полностью восстановлена
                if sum(self.damage.values()) > 0:
                    self.creature.damaged_bodyparts.add(self)
                # часть тела восстановлена полностью
                else:
                    self.creature.not_damaged_bodyparts.add(self)
            else:
                # часть тела восстановлена полностью
                if sum(self.damage.values()) == 0:
                    self.creature.damaged_bodyparts.remove(self)
                    self.creature.not_damaged_bodyparts.add(self)

            return_resources = resources - regenerating_resources
        # часть тела не получила необходимых для регенерации ресурсов
        else:
            return_resources = resources

        return return_resources

    def reset_physic_cache(self) -> None:
        self._volume = None
        self._mass = None
        try:
            self.creature.characteristics._volume = None
            self.creature.characteristics._mass = None
        except AttributeError:
            # существо еще не имеет объекта характеристик, если оно создано, но не появилось в мире (creature.start),
            # а ресурсы ему уже передаются, что вызывает данный метод (storage.reset_physic_cache)
            pass

    def reset_resources_cache(self) -> None:
        self._remaining_resources = None
        self.creature._damage = None
        self.creature._remaining_resources = None


class StorageException(Exception):
    """Исключение для Storage."""

    def __init__(self, message: str):
        super().__init__(message)
        self.resources = Resources[int]()


class AddToDestroyedStorageException(StorageException):
    pass


class RemoveFromDestroyedStorageException(StorageException):
    pass


class ResourceStorageException(Exception):
    """Исключение для ResourceStorage."""

    def __init__(self, world_resource: WorldResource, amount: int, message: str):
        super().__init__(message)
        self.world_resource = world_resource
        self.amount = amount


class AddToDestroyedResourceStorageException(ResourceStorageException):
    pass


class RemoveFromDestroyedResourcesStorageException(ResourceStorageException):
    pass


class ResourceStorageBelowZeroException(ResourceStorageException):
    pass


class StorageNotFoundException(Exception):
    pass


class StorageInterface(BodypartInterface):
    name = "storage_interface"

    def __init__(self, creature, required_bodypart) -> None:
        super().__init__(creature, required_bodypart)
        self._storage: dict[WorldResource, ResourceStorageInterface] = {}
        self._stored_resources: Resources[int] | None = None
        self._available_space: Resources[int] | None = None
        self._extra_resources: Resources[int] | None = None
        self._fullness: Resources[float] | None = None
        self._mean_fullness: float | None = None

    def __repr__(self) -> str:
        string = f"{super().__repr__()}: "
        if len(self._storage) > 0:
            for resource_storage in self.values():
                if resource_storage.destroyed:
                    string += f"{resource_storage.world_resource.formula}: destroyed, "
                else:
                    string += (f"{resource_storage.world_resource.formula}:"
                               f" {resource_storage.current}/{resource_storage.capacity}, ")
        else:
            string += "empty"
        if string[-2:] == ", ":
            string = string[:-2]
        return string

    def __getitem__(self, item):
        return self._storage[item]

    def __iter__(self):
        return iter(self._storage)

    def destroy(self) -> Resources[int]:
        return_resources = super().destroy()
        self._stored_resources = None
        return return_resources

    @classmethod
    def find_storage(cls, bodyparts: set["BodypartInterface"]) -> "StorageInterface":
        """Находит хранилище (storage) в списке частей тела."""

        for bodypart in bodyparts:
            if bodypart.name == "storage":
                break
        else:
            raise StorageNotFoundException()
        # noinspection PyTypeChecker
        return bodypart

    @property
    def stored_resources(self) -> Resources[int]:
        """Хранимые ресурсы."""

        if self._stored_resources is None:
            self._stored_resources = Resources[int]({x.world_resource: x.current for x in self._storage.values()})
        return self._stored_resources

    @property
    def extra_resources(self) -> Resources[int]:
        """Ресурсы, не помещающиеся в хранилище."""

        if self._extra_resources is None:
            self._extra_resources = Resources[int]({x.world_resource: x.extra for x in self._storage.values()})
        return self._extra_resources

    @property
    def available_space(self) -> Resources[int]:
        """Ресурсы, которые поместятся в хранилище без переполнения."""

        if self._available_space is None:
            self._available_space = Resources[int]({x.world_resource: x.available for x in self._storage.values()})
        return self._available_space

    @property
    def fullness(self) -> Resources[float]:
        if self._fullness is None:
            self._fullness = Resources[float]({x.world_resource: x.fullness for x in self._storage.values()})
        return self._fullness

    @property
    def mean_fullness(self) -> float:
        if self._mean_fullness is None:
            self._mean_fullness = statistics.mean(x.fullness for x in self._storage.values())
        return self._mean_fullness

    def items(self) -> ItemsView[WorldResource, "ResourceStorageInterface"]:
        return self._storage.items()

    def keys(self) -> KeysView[WorldResource]:
        return self._storage.keys()

    def values(self) -> ValuesView["ResourceStorageInterface"]:
        return self._storage.values()

    def add_resource_storage(self, resource: WorldResource) -> None:
        """Присоединяет хранилище ресурса к общему."""

        # noinspection PyTypeChecker,PyArgumentList
        resource_storage: ResourceStorageInterface = BODYPART_CLASSES["resource_storage"](self.creature, self, resource)
        self._storage[resource] = resource_storage
        self.dependent_bodyparts.append(resource_storage)

    def add_resources(self, resources: Resources[int]) -> None:
        self.reset_cache()
        not_added_resources = None
        for resource in resources:
            amount = resources[resource]
            try:
                self._storage[resource].add(amount)
            except AddToDestroyedResourceStorageException as exception:
                if not_added_resources is None:
                    not_added_resources = Resources[int]()
                not_added_resources[exception.world_resource] = exception.amount
        if not_added_resources is not None:
            common_exception = AddToDestroyedStorageException(f"{not_added_resources} can not be added to {self}")
            common_exception.resources = not_added_resources
            raise common_exception

    def remove_resources(self, resources: Resources[int]):
        self.reset_cache()
        not_removed_resources = None
        for resource in resources:
            amount = resources[resource]
            try:
                self._storage[resource].remove(amount)
            except RemoveFromDestroyedResourcesStorageException as exception:
                if not_removed_resources is None:
                    not_removed_resources = Resources[int]()
                not_removed_resources[exception.world_resource] = exception.amount
        if not_removed_resources is not None:
            common_exception = RemoveFromDestroyedStorageException(
                f"{not_removed_resources} can not be removed from {self}"
            )
            common_exception.resources = not_removed_resources
            raise common_exception

    def add_resource(self, resource: WorldResource, amount: int) -> None:
        self.reset_cache()
        self._storage[resource].add(amount)

    def remove_resource(self, resource: WorldResource, amount: int) -> None:
        self.reset_cache()
        self._storage[resource].remove(amount)

    def reset_cache(self):
        self._stored_resources = None
        self._available_space = None
        self._extra_resources = None
        self._fullness = None
        self._mean_fullness = None
        self.reset_physic_cache()


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
    def available(self) -> int:
        if self.current >= self.capacity:
            available_space = 0
        else:
            available_space = self.capacity - self.current
        return available_space

    @property
    def extra(self) -> int:
        if self.current >= self.capacity:
            extra = self.current - self.capacity
        else:
            extra = 0
        return extra

    @property
    def volume(self) -> float:
        if self._volume is None:
            self._volume = (sum(resource.volume * amount for resource, amount in self.remaining_resources.items()) +
                            self.capacity * self.world_resource.volume * self.extra_volume_coeff)
        return self._volume

    @property
    def mass(self) -> float:
        if self._mass is None:
            self._mass = (sum(resource.mass * amount for resource, amount in self.remaining_resources.items()) +
                          self.current * self.world_resource.mass)
        return self._mass

    # метод должен вызываться только из Storage.add_resources, так как здесь не вызывается метод reset_physic_cache
    def add(self, amount: int) -> None:
        # self._volume не сбрасывается,
        # так как объем части тела (хранилища) не зависит от текущего количества хранимого ресурса
        self._mass = None
        if amount > 0:
            if self.destroyed:
                raise AddToDestroyedResourceStorageException(self.world_resource, amount, f"{self}")
            else:
                self.current += amount
        elif amount < 0:
            raise ValueError(f"Adding resource ({self.world_resource}) must be not negative ({amount}). {self}")

    # метод должен вызываться только из Storage.add_resources, так как здесь не вызывается метод reset_physic_cache
    def remove(self, amount: int) -> None:
        # self._volume не сбрасывается,
        # так как объем части тела (хранилища) не зависит от текущего количества хранимого ресурса
        self._mass = None
        if amount > 0:
            if self.destroyed:
                raise RemoveFromDestroyedResourcesStorageException(self.world_resource, amount, f"{self}")
            else:
                self.current -= amount
                if self.current < 0:
                    message = f"{self.current + amount} - {amount} = {self.current}"
                    raise ResourceStorageBelowZeroException(self.world_resource, self.current, message)
        elif amount < 0:
            raise ValueError(f"Removing resource ({self.world_resource}) must be not negative ({amount}). {self}")

    def destroy(self) -> Resources[int]:
        return_resources = super().destroy()
        return_resources[self.world_resource] += self.current
        self.current = 0
        return return_resources


BodypartInterfaceClass = (BodypartInterface | StorageInterface | ResourceStorageInterface)

# noinspection DuplicatedCode
BODYPART_INTERFACE_CLASSES: dict[str, Type[BodypartInterfaceClass]] = {
    x.name: x for x in BodypartInterface.get_all_subclasses()
}
BODYPART_INTERFACE_CLASSES[BodypartInterface.name] = BodypartInterface
# обновляются данные в интерфейсах
BodypartInterface.apply_descriptor(bodypart_interface_descriptors[BodypartInterface.name])
for name, bodypart_interface_class in BODYPART_INTERFACE_CLASSES.items():
    bodypart_interface_class.apply_descriptor(bodypart_interface_descriptors[name])

# создаются классы частей тела
BODYPART_CLASSES: dict[str, Type[BodypartInterfaceClass]] = {
    x["name"]: type(x["name"], (BODYPART_INTERFACE_CLASSES[x["interface"]],), x)
    for x in bodypart_descriptors.values()
}
# обновляются данные в классах генов
for name, bodypart_class in BODYPART_CLASSES.items():
    bodypart_class.apply_descriptor(bodypart_descriptors[name])
