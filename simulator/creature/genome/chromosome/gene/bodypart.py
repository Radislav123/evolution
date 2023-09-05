import abc

from simulator.creature.bodypart import BaseBodypart, Body, Storage
from simulator.creature.genome.chromosome.gene import Gene, StepGeneMixin
from simulator.world_resource import WorldResource, CARBON, ENERGY, HYDROGEN, OXYGEN


class BodyPartGene(Gene, abc.ABC):
    """Базовый класс для генов, добавляющих части тела."""

    # утеря ресурсов из-за частей тела уже включена в расчеты (берется часть ресурсов существа для "обновления клеток")
    effect_attribute_name = None
    bodypart: BaseBodypart

    def apply(self, genome):
        genome.effects.bodyparts.append(self.bodypart)


class BodyGene(BodyPartGene):
    abstract = False
    required_for_creature = True
    bodypart = Body
    appearance_chance = 0
    _disappearance_chance = 0
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

    @classmethod
    def correct(cls, genome):
        pass

    def mutate(self, genome):
        # mutation_chance = 0 (никогда не мутирует)
        raise NotImplementedError()
        pass


class StorageGene(BodyPartGene):
    abstract = False
    required_for_creature = True
    bodypart = Storage
    appearance_chance = 0
    _disappearance_chance = 0
    mutation_chance = 0
    required_genes = [BodyGene]

    @classmethod
    def correct(cls, genome):
        pass

    def mutate(self, genome):
        # mutation_chance = 0 (никогда не мутирует)
        raise NotImplementedError()
        pass


class BaseResourceStorageGene(StepGeneMixin, BodyPartGene, abc.ABC):
    # bodypart = ResourceStorage
    resource: WorldResource
    step = 10
    common_min_limit = 0
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
        genome.effects.resource_storages[self.resource] += self.capacity

    @classmethod
    def correct(cls, genome):
        if genome.effects.resource_storages[cls.resource] < cls.common_min_limit:
            genome.effects.resource_storages[cls.resource] = cls.common_min_limit

    def mutate(self, genome):
        self.capacity += self.make_step()


class EnergyStorageGene(BaseResourceStorageGene):
    abstract = False
    required_for_creature = True
    resource = ENERGY
    # todo: вернуть на 100 (или 200), когда уберу ENERGY из ресурсов Body
    default_capacity = 400


class OxygenStorageGene(BaseResourceStorageGene):
    abstract = False
    required_for_creature = True
    resource = OXYGEN
    default_capacity = 350


class CarbonStorageGene(BaseResourceStorageGene):
    abstract = False
    required_for_creature = True
    resource = CARBON
    default_capacity = 200


class HydrogenStorageGene(BaseResourceStorageGene):
    abstract = False
    required_for_creature = True
    resource = HYDROGEN
    default_capacity = 100


class ResourceConsumptionGene(StepGeneMixin, Gene, abc.ABC):
    """Базовый класс для генов, позволяющих потреблять ресурсы."""

    step = 1
    common_min_limit = 0
    default_consumption = 5
    resource: WorldResource

    def __init__(self, first: bool):
        super().__init__(first)

        if self.first:
            self.consumption = self.default_consumption
        else:
            self.consumption = self.make_step()

    def __repr__(self):
        return f"{super().__repr__()}: {self.resource}"

    def apply(self, genome):
        genome.effects.consumption_amount[self.resource] += self.consumption

    @classmethod
    def correct(cls, genome):
        if genome.effects.consumption_amount[cls.resource] < cls.common_min_limit:
            genome.effects.consumption_amount[cls.resource] = cls.common_min_limit

    def mutate(self, genome):
        self.consumption += self.make_step()


# todo: изменить - сделать из EnergyConsumptionGene абстрактный
class EnergyConsumptionGene(ResourceConsumptionGene):
    abstract = False
    required_for_creature = True
    required_genes = [EnergyStorageGene]
    resource = ENERGY


class OxygenConsumptionGene(ResourceConsumptionGene):
    abstract = False
    required_for_creature = True
    required_genes = [OxygenStorageGene]
    resource = OXYGEN


class CarbonConsumptionGene(ResourceConsumptionGene):
    abstract = False
    required_for_creature = True
    required_genes = [CarbonStorageGene]
    resource = CARBON


class HydrogenConsumptionGene(ResourceConsumptionGene):
    abstract = False
    required_for_creature = True
    required_genes = [HydrogenStorageGene]
    resource = HYDROGEN
