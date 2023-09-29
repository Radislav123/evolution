import copy
import math
import statistics
from typing import TYPE_CHECKING, Type

from core.mixin import ApplyDescriptorMixin, GetSubclassesMixin
from core.service import ObjectDescriptionReader
from evolution import settings
from simulator.creature.genome.chromosome.gene import BodypartGeneInterface, ResourceStorageGeneInterface
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


class BodypartNotFoundException(Exception):
    pass


class BodypartInterface(GetSubclassesMixin["BodypartInterface"], ApplyDescriptorMixin):
    name = "bodypart_interface"
    # название интерфейса, определяющего часть тела
    interface: str
    # https://ru.wikipedia.org/wiki/%D0%A5%D0%B8%D0%BC%D0%B8%D1%87%D0%B5%D1%81%D0%BA%D0%B0%D1%8F_%D0%BE%D1%80%D0%B3%D0%B0%D0%BD%D0%B8%D0%B7%D0%B0%D1%86%D0%B8%D1%8F_%D0%BA%D0%BB%D0%B5%D1%82%D0%BA%D0%B8
    # ресурсы, из которых состоит часть тела (химический состав) при размере (size_coeff) равном 1.0
    composition: dict[str, int]
    extra_storage_coeff: float

    def __init__(
            self,
            creature: "Creature",
            gene: BodypartGeneInterface,
            required_bodypart: "BodypartInterfaceClass | None"
    ) -> None:
        self.creature = creature
        self.gene = gene
        if not self.gene.active:
            raise ValueError(
                f"Can not create bodypart from non active gene ({self.gene}).\n"
                f"required_bodypart: {self.gene.required_bodypart}\n"
                f"required_gene_number: {self.gene.required_gene_number}\n"
                f"dependent_bodyparts: {self.creature.genome.effects.bodyparts_genes}"
            )
        self.size_coeff = self.creature.genome.effects.size_coeff * self.gene.size_coeff
        # часть тела, к которой крепится данная
        self.required_bodypart: BodypartInterfaceClass = required_bodypart
        self.dependent_bodyparts: set["BodypartInterfaceClass"] = set()
        self._all_dependent: set["BodypartInterfaceClass"] | None = None
        self._all_required: set["BodypartInterfaceClass"] | None = None

        # уничтожена ли часть тела полностью
        self.destroyed = False
        # построены ли зависимости методом construct
        # устанавливается в положение True только в методе Creature.apply_bodyparts
        # todo: remove constructed?
        self.constructed = False

        self.damage = Resources[int]()
        # ресурсы, находящиеся в неповрежденной части тела/необходимые для воспроизводства части тела
        # при размере (size_coeff) равном 1.0 соответствует composition
        self.resources = Resources[int](
            {RESOURCE_DICT[resource_name]: amount for resource_name, amount in self.composition.items()}
        )
        self.resources *= self.size_coeff
        self.resources.iround()
        for resource, amount in self.resources.items():
            if amount == 0:
                self.resources[resource] = 1
        # расширение хранилища существа, которое предоставляет часть тела
        self.extra_storage: Resources[int] = self.resources * self.extra_storage_coeff
        self.extra_storage.iround()
        self._remaining_resources: Resources[int] | None = None

        self._mass: float | None = None
        self.volume = sum(resource.volume * amount for resource, amount in self.remaining_resources.items())

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({sum(self.remaining_resources.values())}/{sum(self.resources.values())})"

    @property
    def remaining_resources(self) -> Resources[int]:
        """Ресурсы, находящиеся в части тела сейчас."""

        if self._remaining_resources is None:
            self._remaining_resources = self.resources - self.damage
        return self._remaining_resources

    @property
    def all_required(self) -> set["BodypartInterfaceClass"]:
        """Цепочка частей тела, к которой прикреплена данная часть тела."""

        if self._all_required is None or not self.constructed:
            if self.required_bodypart is None:
                self._all_required = set()
            else:
                self._all_required = self.required_bodypart.all_required.copy()
                self._all_required.add(self.required_bodypart)
        return self._all_required

    @property
    def all_dependent(self) -> set["BodypartInterfaceClass"]:
        """Список частей тела, прикрепленных к данной напрямую или через другие части тела."""

        if self._all_dependent is None or not self.constructed:
            self._all_dependent = self.dependent_bodyparts.copy()
            for bodypart in self.dependent_bodyparts:
                self._all_dependent.update(bodypart.all_dependent)
        return self._all_dependent

    @property
    def mass(self) -> float:
        if self._mass is None:
            self._mass = sum(resource.mass * amount for resource, amount in self.remaining_resources.items())
        return self._mass

    @classmethod
    def construct_creature(cls, creature: "Creature") -> tuple["BodypartInterface", "StorageInterface"]:
        """Собирает существо из частей тела."""

        genes = creature.genome.effects.bodyparts_genes
        dependent_genes = creature.genome.effects.dependent_bodypart_genes
        body_gene = list(genes["body"].values())[0]
        body = BODYPART_CLASSES[body_gene.bodypart](creature, body_gene, None)

        body.construct(genes, dependent_genes)

        for bodypart in body.all_dependent:
            if bodypart.name == "storage":
                storage = bodypart
                break
        else:
            # todo: добавить обработку случаев, когда в геноме отсутствует тело или хранилище
            #  (не хватает required частей тела)
            raise BodypartNotFoundException()

        for bodypart in body.all_dependent:
            # todo: переделать, когда появятся новые типы хранилищ
            if bodypart.name == "resource_storage":
                storage.capacity[bodypart.world_resource] += bodypart.capacity
                bodypart.storage = storage
        storage.volume += sum(resource.volume * amount for resource, amount in storage.capacity.items())

        return body, storage

    def construct(
            self,
            genes: dict[str, dict[int, BodypartGeneInterface]],
            dependent_genes: dict[BodypartGeneInterface, set[BodypartGeneInterface]]
    ) -> None:
        """Собирает часть тела и все зависимые, устанавливая ссылки на зависимые и необходимые части тела."""

        for gene in dependent_genes[self.gene]:
            bodypart = BODYPART_CLASSES[gene.bodypart](self.creature, gene, self)
            self.dependent_bodyparts.add(bodypart)
            bodypart.construct(genes, dependent_genes)

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
            for resource, amount in self.damage.items():
                if amount > self.resources[resource]:
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
        self._mass = None
        self.creature.characteristics._mass = None

    def reset_resources_cache(self) -> None:
        self._remaining_resources = None
        self.creature._damage = None
        self.creature._remaining_resources = None


class StorageException(Exception):
    """Исключение для Storage."""

    def __init__(self, message: str, resources: Resources[int]):
        super().__init__(message)
        self.resources = resources


class AddToNonExistentStorageException(StorageException):
    pass


class RemoveFromNonExistentStorageException(StorageException):
    pass


class StorageInterface(BodypartInterface):
    name = "storage_interface"

    def __init__(
            self,
            creature: "Creature",
            gene: BodypartGeneInterface,
            required_bodypart: "BodypartInterfaceClass | None"
    ) -> None:
        super().__init__(creature, gene, required_bodypart)
        # не обращаться к current извне напрямую
        self.current: Resources[int] = Resources[int]()
        self.capacity: Resources[int] = Resources[int]()
        self._available_space: Resources[int] | None = None
        self._extra: Resources[int] | None = None
        self._fullness: Resources[float] | None = None
        self._mean_fullness: float | None = None

    def __repr__(self) -> str:
        string = [f"{super().__repr__()}: "]
        if len(self.capacity) > 0:
            for resource, amount in self.capacity.items():
                string.append(f"{resource.formula}: {self.current[resource]}/{amount}, ")
        else:
            string += ["empty"]
        string = "".join(string)
        if string[-2:] == ", ":
            string = string[:-2]
        return string

    def destroy(self) -> Resources[int]:
        return_resources = super().destroy()
        return_resources += self.current
        self.current = Resources[int]()
        return return_resources

    @property
    def extra(self) -> Resources[int]:
        """Ресурсы, не помещающиеся в хранилище."""

        if self._extra is None:
            self._extra = Resources[int]()
            for resource, capacity in self.capacity.items():
                if (extra := self.current[resource] - capacity) > 0:
                    self._extra[resource] = extra
        return self._extra

    @property
    def available_space(self) -> Resources[int]:
        """Ресурсы, которые поместятся в хранилище без переполнения."""

        if self._available_space is None:
            self._available_space = Resources[int]()
            for resource, capacity in self.capacity.items():
                if (available_space := capacity - self.current[resource]) > 0:
                    self._available_space[resource] = available_space
        return self._available_space

    @property
    def fullness(self) -> Resources[float]:
        if self._fullness is None:
            self._fullness = Resources[float]()
            for resource, capacity in self.capacity.items():
                self._fullness[resource] = self.current[resource] / capacity
        return self._fullness

    @property
    def mean_fullness(self) -> float:
        if self._mean_fullness is None:
            self._mean_fullness = statistics.mean(self.fullness.values())
        return self._mean_fullness

    def add_resources(self, resources: Resources[int]) -> None:
        self.reset_storage_cache()
        for resource, amount in resources.items():
            not_added_resources = Resources[int]()
            if self.capacity[resource] > 0:
                self.current[resource] += amount
            else:
                not_added_resources[resource] += amount
            if len(not_added_resources) > 0:
                raise AddToNonExistentStorageException(
                    f"{not_added_resources} can not be added to {self}.",
                    not_added_resources
                )

    def remove_resources(self, resources: Resources[int]) -> None:
        self.reset_storage_cache()
        for resource, amount in resources.items():
            not_removed_resources = Resources[int]()
            if self.capacity[resource] > 0:
                self.current[resource] -= amount
                if self.current[resource] < 0:
                    raise ValueError(f"{resource} is below zero ({self.current[resource]}) in storage.")
            else:
                not_removed_resources[resource] += amount
            if len(not_removed_resources) > 0:
                raise RemoveFromNonExistentStorageException(
                    f"{not_removed_resources} can not be added to {self}.",
                    not_removed_resources
                )

    @property
    def mass(self) -> float:
        if self._mass is None:
            self._mass = (sum(resource.mass * amount for resource, amount in self.remaining_resources.items()) +
                          sum(resource.mass * amount for resource, amount in self.current.items()))
        return self._mass

    def reset_storage_cache(self):
        self._available_space = None
        self._extra = None
        self._fullness = None
        self._mean_fullness = None
        self.reset_physic_cache()


class ResourceStorageInterface(BodypartInterface):
    name = "resource_storage_interface"
    world_resource: WorldResource

    def __init__(
            self,
            creature: "Creature",
            gene: ResourceStorageGeneInterface,
            required_bodypart: "BodypartInterfaceClass | None"
    ) -> None:
        super().__init__(creature, gene, required_bodypart)

        self.world_resource = RESOURCE_DICT[gene.resource]
        self.capacity = int(
            math.pi / 4 * sum(resource.volume * amount for resource, amount in self.resources.items())**2
        )
        self.storage: StorageInterface | None = None

    def __repr__(self) -> str:
        string = [
            f"{self.world_resource.name.upper()}Storage",
            f"({sum(self.remaining_resources.values())}/{sum(self.resources.values())}): "
        ]
        if self.destroyed:
            string.append("destroyed")
        else:
            string.append(str(self.capacity))
        return "".join(string)

    def destroy(self) -> Resources[int]:
        return_resources = super().destroy()
        self.storage.capacity[self.world_resource] -= self.capacity
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
