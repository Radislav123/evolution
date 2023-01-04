import abc

from simulator.creature.genome.chromosome.gene import BaseGene, StepGeneMixin, step_type


class BaseNumberGene(StepGeneMixin, BaseGene, abc.ABC):
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
        return f"{super().__repr__()}: {getattr(self, self.attribute_name)}"

    @property
    def resources_loss_effect_attribute_name(self) -> str:
        return self.attribute_name

    def apply(self, genome):
        setattr(
            genome.effects,
            self.attribute_name,
            getattr(genome.effects, self.attribute_name) + getattr(self, self.attribute_name)
        )
        if hasattr(self, "common_min_limit") and getattr(genome.effects, self.attribute_name) < self.common_min_limit:
            setattr(
                genome.effects,
                self.attribute_name,
                self.common_min_limit
            )
        if hasattr(self, "common_max_limit") and getattr(genome.effects, self.attribute_name) > self.common_min_limit:
            setattr(
                genome.effects,
                self.attribute_name,
                self.common_max_limit
            )

    def mutate(self, genome):
        step = self.make_step()
        if hasattr(self, "min_limit") and self.__getattribute__(self.attribute_name) + step < self.min_limit:
            self.__setattr__(
                self.attribute_name,
                self.__getattribute__(self.attribute_name) + self.make_step("+")
            )
        elif hasattr(self, "max_limit") and self.__getattribute__(self.attribute_name) + step > self.max_limit:
            self.__setattr__(
                self.attribute_name,
                self.__getattribute__(self.attribute_name) + self.make_step("-")
            )
        else:
            self.__setattr__(
                self.attribute_name,
                self.__getattribute__(self.attribute_name) + step
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
    common_min_limit = 0.1
    attribute_name = "size_coef"


# todo: добавить трату специализированного ресурса, связанного с эластичностью
#  можно так - если >= 0.3, то один ресурс (эластичность), если < 0.3 - другой ресурс (твердость)
class ElasticityGene(BaseNumberGene):
    abstract = False
    required_for_creature = True
    step = 0.1
    attribute_default = 0.5
    common_min_limit = 0
    common_max_limit = 1
    attribute_name = "elasticity"


# todo: добавить бонусы за высокое значение метаболизма, возможно, связанные с другими генами (температура, скорость...)
class MetabolismGene(BaseNumberGene):
    abstract = False
    required_for_creature = True
    step = 0.0005
    common_min_limit = 0.001
    attribute_default = 0.005
    attribute_name = "metabolism"


# todo: добавить бонусы за высокое значение потери ресурсов, возможно, связанные с другими генами
class ResourcesLossCoefGene(BaseNumberGene):
    abstract = False
    required_for_creature = True
    step = 0.0005
    common_min_limit = 0.001
    attribute_default = 0.005
    attribute_name = "resources_loss_coef"


class RegenerateAmountGene(BaseNumberGene):
    abstract = False
    required_for_creature = True
    step = 1
    common_min_limit = 0
    attribute_default = 5
    attribute_name = "regeneration_amount"
