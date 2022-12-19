import abc
import random

from typing import TYPE_CHECKING


# https://adamj.eu/tech/2021/05/13/python-type-hints-how-to-fix-circular-imports/
if TYPE_CHECKING:
    from simulator.object.creature.genome.base import BaseGenome


class BaseGene(abc.ABC):
    # обязательно ли присутствие хотя бы одного такого гена в геноме (могут ли все копии пропасть из генома)
    required: bool

    def __init__(self):
        self._mutate_chance = 0.001
        self.disappear_chance = 0.001

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}"

    def apply(self, genome: "BaseGenome"):
        """Записывает эффекты гена в хранилище."""

        raise NotImplementedError()

    @property
    def mutate_chance(self) -> float:
        return self._mutate_chance

    # если возвращает True, ген необходимо удалить из хромосомы
    def mutate(self, genome: "BaseGenome") -> bool:
        raise NotImplementedError()

    @classmethod
    def get_required_genes(cls) -> list["BaseGene"]:
        return [gene() for gene in cls.__subclasses__() if gene.required]

    @classmethod
    def get_available_genes(cls) -> list["BaseGene"]:
        """Возвращает список генов, возможных для добавления в процессе мутации."""

        return [gene() for gene in cls.__subclasses__()]

    def can_disappear(self, genome: "BaseGenome") -> bool:
        can_disappear = False
        if self.required and len(genome.get_genes(self.__class__)) > 1 or not self.required:
            if random.random() < self.disappear_chance:
                can_disappear = True
        return can_disappear


class ChildrenNumberGene(BaseGene):
    required = True

    def __init__(self):
        super().__init__()
        self.children_number = 1

    def __repr__(self):
        return f"{super().__repr__()}: {self.children_number}"

    def apply(self, genome):
        genome.effects.children_number += self.children_number

    def mutate(self, genome) -> bool:
        if self.can_disappear(genome):
            return True

        self.children_number += [-1, 1][random.randint(0, 1)]
        return False


class SizeGene(BaseGene):
    required = True

    def __init__(self):
        super().__init__()
        self.size = 10

    def __repr__(self):
        return f"{super().__repr__()}: {self.size}"

    def apply(self, genome):
        genome.effects.size += self.size

    def mutate(self, genome) -> bool:
        if self.can_disappear(genome):
            return True

        self.size += [-1, 1][random.randint(0, 1)]
        return False
