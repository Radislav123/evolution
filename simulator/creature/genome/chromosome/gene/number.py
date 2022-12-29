import abc

from simulator.creature.genome.chromosome.gene import BaseGene, step_type


class BaseNumberGene(BaseGene, abc.ABC):
    """Базовый класс для генов, влияющих численно."""

    attribute_default: step_type
    attribute_name: str

    def __init__(self, first):
        super().__init__(first)

        if self.first:
            attribute_value = self.attribute_default
        else:
            attribute_value = self.make_step()

        self.__setattr__(self.attribute_name, attribute_value)

    def __repr__(self):
        return f"{super().__repr__()}: {self.__getattribute__(self.attribute_name)}"

    @property
    def resources_loss_effect_attribute_name(self) -> str:
        return self.attribute_name

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


# todo: добавить мутации
class MetabolismGene(BaseNumberGene):
    abstract = False
    required_for_creature = True
    appearance_chance = 0
    mutation_chance = 0
    attribute_default = 0.005
    attribute_name = "metabolism"


# todo: добавить мутации
class ResourcesLossCoefGene(BaseNumberGene):
    abstract = False
    required_for_creature = True
    appearance_chance = 0
    mutation_chance = 0
    attribute_default = 0.005
    attribute_name = "resources_loss_coef"


class RegenerateAmountGene(BaseNumberGene):
    abstract = False
    required_for_creature = True
    step = 1
    attribute_default = 5
    attribute_name = "regeneration_amount"
