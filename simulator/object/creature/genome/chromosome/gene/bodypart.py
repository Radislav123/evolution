import abc

from simulator.object.creature.bodypart import BaseBodypart, Body, Storage
from simulator.object.creature.genome.chromosome.gene import BaseGene
from simulator.world_resource import BaseWorldResource, CARBON, ENERGY, HYDROGEN, OXYGEN


class BaseBodyPartGene(BaseGene, abc.ABC):
    """Базовый класс для генов, добавляющих части тела."""

    # утеря ресурсов из-за частей тела уже включена в расчеты (берется часть ресурсов существа для "обновления клеток")
    effect_attribute_name = None
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

    def __init__(self, first: bool):
        super().__init__(first)

        self.required_genes = [
            OxygenConsumptionGene,
            CarbonConsumptionGene,
            HydrogenConsumptionGene,
            EnergyConsumptionGene,
            OxygenStorageGene,
            CarbonStorageGene,
            HydrogenStorageGene,
            EnergyStorageGene
        ]

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
    required_genes = [BodyGene]

    def mutate(self, genome):
        # mutation_chance = 0 (никогда не мутирует)
        raise NotImplementedError()
        pass


class BaseResourceStorageGene(BaseBodyPartGene, abc.ABC):
    # bodypart = ResourceStorage
    resource: BaseWorldResource
    step = 10
    default_capacity: int
    required_genes = [StorageGene]

    def __init__(self, first):
        super().__init__(first)

        if self.first:
            self.capacity = self.default_capacity
        else:
            self.capacity = self.make_step()

    def __repr__(self):
        return f"{super().__repr__()}: {self.capacity}"

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
    effect_attribute_name = None
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
