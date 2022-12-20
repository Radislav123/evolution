import abc
import random
from abc import ABC
from typing import TYPE_CHECKING, Type, TypeVar


# https://adamj.eu/tech/2021/05/13/python-type-hints-how-to-fix-circular-imports/
if TYPE_CHECKING:
    from simulator.object.creature.genome.base import BaseGenome


class BaseGene(abc.ABC):
    # по умолчанию класс гена абстрактный
    abstract = True
    # обязательно ли присутствие хотя бы одного такого гена в геноме (могут ли все копии пропасть из генома)
    required: bool

    def __init__(self, first: bool):
        self._mutate_chance = 0.001
        self.disappear_chance = 0.001
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

    @property
    def mutate_chance(self) -> float:
        return self._mutate_chance

    # если возвращает True, ген необходимо удалить из хромосомы
    @abc.abstractmethod
    def mutate(self, genome: "BaseGenome") -> bool:
        raise NotImplementedError()

    @classmethod
    def get_required_genes(cls) -> list["BaseGene"]:
        """Возвращает гены для вставки пустое существо."""

        return [gene(True) for gene in cls.get_all_subclasses() if not gene.abstract and gene.required]

    @classmethod
    def get_available_genes(cls) -> list["BaseGene"]:
        """Возвращает список генов, возможных для добавления в процессе мутации."""

        return [gene(False) for gene in cls.get_all_subclasses() if not gene.abstract]

    def can_disappear(self, genome: "BaseGenome") -> bool:
        can_disappear = False
        if self.required and len(genome.get_genes(self.__class__)) > 1 or not self.required:
            if random.random() < self.disappear_chance:
                can_disappear = True
        return can_disappear


step_type = TypeVar("step_type", int, float)


class BaseNumberGene(BaseGene, ABC):
    """Базовый класс для генов, влияющих численно."""

    step: step_type
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

    def make_step(self) -> step_type:
        return [-self.step, self.step][random.randint(0, 1)]

    def apply(self, genome):
        genome.effects.__setattr__(
            self.attribute_name,
            genome.effects.__getattribute__(self.attribute_name) + self.__getattribute__(self.attribute_name)
        )

    def mutate(self, genome) -> bool:
        if self.can_disappear(genome):
            return True

        self.__setattr__(
            self.attribute_name,
            self.__getattribute__(self.attribute_name) + self.make_step()
        )
        return False


class ChildrenNumberGene(BaseNumberGene):
    abstract = False
    required = True
    step = 1
    attribute_default = 1
    attribute_name = "children_number"


class SizeGene(BaseNumberGene):
    abstract = False
    required = True
    step = 1
    attribute_default = 10
    attribute_name = "size"


class ElasticityGene(BaseNumberGene):
    abstract = False
    required = True
    step = 0.1
    attribute_default = 0.5
    attribute_name = "elasticity"
