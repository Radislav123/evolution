import abc
import random
from typing import TYPE_CHECKING, Type, TypeVar

from simulator.object.creature.bodypart.base import BaseBodypart, Body
from simulator.object.creature.bodypart.storage import Storage
from simulator.world_resource.base import BaseWorldResource, CARBON, ENERGY, HYDROGEN, OXYGEN


# https://adamj.eu/tech/2021/05/13/python-type-hints-how-to-fix-circular-imports/
if TYPE_CHECKING:
    from simulator.object.creature.genome.base import BaseGenome


class BaseGene(abc.ABC):
    # по умолчанию класс гена абстрактный
    abstract = True
    # обязательно ли присутствие хотя бы одного такого гена в геноме (могут ли все копии пропасть из генома)
    required_for_creature: bool
    # список генов, необходимых для появления этого гена
    required_genes: list[Type["BaseGene"]] = []
    mutation_chance = 0.001
    disappearance_chance = 0.001
    appearance_chance = 1

    def __init__(self, first: bool):
        self.first = first

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}"

    @classmethod
    def get_all_subclasses(cls) -> list[Type["BaseGene"]]:
        """Возвращает все дочерние классы рекурсивно."""

        subclasses = cls.__subclasses__()
        children_subclasses = []
        for child in subclasses:
            children_subclasses.extend(child.get_all_subclasses())
        subclasses.extend(children_subclasses)
        return subclasses

    @abc.abstractmethod
    def apply(self, genome: "BaseGenome"):
        """Записывает эффекты гена в хранилище."""

        raise NotImplementedError()

    @abc.abstractmethod
    def mutate(self, genome: "BaseGenome"):
        raise NotImplementedError()

    @classmethod
    def get_required_for_creature_genes(cls) -> list["BaseGene"]:
        """Возвращает гены для вставки в геном первого существа."""

        return [gene(True) for gene in cls.get_all_subclasses() if not gene.abstract and gene.required_for_creature]

    @classmethod
    def get_available_genes(cls, genome: "BaseGenome") -> list["BaseGene"]:
        """Возвращает список генов, возможных для добавления в процессе мутации."""

        return [
            gene(False) for gene in cls.get_all_subclasses()
            if not gene.abstract and genome.contains_all(gene.required_genes) and gene.appearance_chance > 0
        ]

    def disappear(self, genome: "BaseGenome") -> bool:
        can_disappear = False
        if not self.required_for_creature or self.required_for_creature and genome.count_genes(self) > 1:
            if random.random() < self.disappearance_chance:
                can_disappear = True
        return can_disappear


step_type = TypeVar("step_type", int, float)


class BaseNumberGene(BaseGene, abc.ABC):
    """Базовый класс для генов, влияющих численно."""

    step: step_type
    attribute_default: step_type
    attribute_name: str

    def __init__(self, first):
        super().__init__(first)

        if self.first:
            attribute_value = self.attribute_default
        else:
            attribute_value = 0

        self.__setattr__(self.attribute_name, attribute_value)

    def __repr__(self):
        return f"{super().__repr__()}: {self.__getattribute__(self.attribute_name)}"

    def make_step(self) -> step_type:
        return [-self.step, self.step][random.randint(0, 1)]

    def apply(self, genome):
        genome.effects.__setattr__(
            self.attribute_name,
            genome.effects.__getattribute__(self.attribute_name) + self.__getattribute__(self.attribute_name)
        )

    def mutate(self, genome):
        self.__setattr__(
            self.attribute_name,
            self.__getattribute__(self.attribute_name) + self.make_step()
        )


class ChildrenNumberGene(BaseNumberGene):
    abstract = False
    required_for_creature = True
    step = 1
    attribute_default = 1
    attribute_name = "children_number"


class SizeGene(BaseNumberGene):
    abstract = False
    required_for_creature = True
    step = 0.1
    attribute_default = 1
    attribute_name = "size"


class ElasticityGene(BaseNumberGene):
    abstract = False
    required_for_creature = True
    step = 0.1
    attribute_default = 0.5
    attribute_name = "elasticity"


class ConsumptionAmountGene(BaseNumberGene):
    abstract = False
    required_for_creature = True
    step = 1
    attribute_default = 5
    attribute_name = "consumption_amount"


class BaseBodyPartGene(BaseGene, abc.ABC):
    """Базовый класс для генов, добавляющих части тела."""

    bodypart: BaseBodypart

    def apply(self, genome):
        genome.effects.bodyparts.append(self.bodypart)


class BodyGene(BaseBodyPartGene):
    abstract = False
    required_for_creature = True
    bodypart = Body
    appearance_chance = 0
    disappearance_chance = 0
    mutation_chance = 0

    def mutate(self, genome):
        # mutation_chance = 0 (никогда не мутирует)
        raise NotImplementedError()
        pass


class StorageGene(BaseBodyPartGene):
    abstract = False
    required_for_creature = True
    bodypart = Storage
    appearance_chance = 0
    disappearance_chance = 0
    mutation_chance = 0

    def mutate(self, genome):
        # mutation_chance = 0 (никогда не мутирует)
        raise NotImplementedError()
        pass


class BaseResourceStorageGene(BaseBodyPartGene, abc.ABC):
    # bodypart = ResourceStorage
    resource: BaseWorldResource
    step = 10
    default_capacity: int

    def __init__(self, first):
        super().__init__(first)

        if self.first:
            self.capacity = self.default_capacity
        else:
            self.capacity = self.make_step()

    def __repr__(self):
        return f"{super().__repr__()}: {self.capacity}"

    def make_step(self) -> step_type:
        return [-self.step, self.step][random.randint(0, 1)]

    def apply(self, genome):
        if self.resource not in genome.effects.resource_storages:
            genome.effects.resource_storages[self.resource] = self.capacity
        else:
            genome.effects.resource_storages[self.resource] += self.capacity

    def mutate(self, genome):
        self.capacity += self.make_step()


# noinspection DuplicatedCode
class EnergyStorageGene(BaseResourceStorageGene):
    abstract = False
    required_for_creature = True
    resource = ENERGY
    default_capacity = 100


# noinspection DuplicatedCode
class CarbonStorageGene(BaseResourceStorageGene):
    abstract = False
    required_for_creature = True
    resource = CARBON
    default_capacity = 150


# noinspection DuplicatedCode
class OxygenStorageGene(BaseResourceStorageGene):
    abstract = False
    required_for_creature = True
    resource = OXYGEN
    default_capacity = 350


# noinspection DuplicatedCode
class HydrogenStorageGene(BaseResourceStorageGene):
    abstract = False
    required_for_creature = True
    resource = HYDROGEN
    default_capacity = 100


class BaseResourceConsumptionGene(BaseGene, abc.ABC):
    """Базовый класс для генов, позволяющих потреблять ресурсы."""

    mutation_chance = 0
    resource: BaseWorldResource

    def __repr__(self):
        return f"{super().__repr__()}: {self.resource}"

    def apply(self, genome):
        genome.effects.consumption_resources.append(self.resource)

    def mutate(self, genome):
        # mutation_chance = 0 (никогда не мутирует)
        raise NotImplementedError()
        pass


# todo: изменить - сделать из EnergyConsumptionGene абстрактный
# noinspection DuplicatedCode
class EnergyConsumptionGene(BaseResourceConsumptionGene):
    abstract = False
    required_for_creature = True
    required_genes = [EnergyStorageGene]
    resource = ENERGY


# noinspection DuplicatedCode
class CarbonConsumptionGene(BaseResourceConsumptionGene):
    abstract = False
    required_for_creature = True
    required_genes = [CarbonStorageGene]
    resource = CARBON


# noinspection DuplicatedCode
class OxygenConsumptionGene(BaseResourceConsumptionGene):
    abstract = False
    required_for_creature = True
    required_genes = [OxygenStorageGene]
    resource = OXYGEN


# noinspection DuplicatedCode
class HydrogenConsumptionGene(BaseResourceConsumptionGene):
    abstract = False
    required_for_creature = True
    required_genes = [HydrogenStorageGene]
    resource = HYDROGEN
