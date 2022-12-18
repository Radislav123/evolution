import abc
import random

from typing import TYPE_CHECKING


# https://adamj.eu/tech/2021/05/13/python-type-hints-how-to-fix-circular-imports/
if TYPE_CHECKING:
    from simulator.object.creature.genome.base import BaseGenome


class BaseGene(abc.ABC):
    # обязательно ли присутствие гена в геноме (может ли он пропасть)
    required = False
    # может ли ген повторятся в других хромосомах
    duplicatable = True

    def __init__(self):
        self._mutate_chance = 0.001
        self._disappear_chance = 0.1

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}"

    @property
    def disappear_chance(self):
        if self.required:
            return 0
        else:
            return self._disappear_chance

    @property
    def mutate_chance(self) -> float:
        return self._mutate_chance

    # если возвращает True, ген необходимо удалить из хромосомы
    def mutate(self) -> bool:
        raise NotImplementedError()

    @classmethod
    def get_required_genes(cls) -> list["BaseGene"]:
        return [gene() for gene in cls.__subclasses__() if gene.required]

    @classmethod
    def get_available_genes(cls, genome: "BaseGenome") -> list["BaseGene"]:
        """Возвращает список генов, возможных для добавления в процессе мутации."""

        return [
            gene() for gene in cls.__subclasses__()
            if not gene.required and (gene.duplicatable or len(genome.get_genes(gene)) == 0)
        ]


class ChildrenNumberGene(BaseGene):
    required = True
    duplicatable = False

    def __init__(self):
        super().__init__()
        self.children_number = 1

    def mutate(self) -> bool:
        self.children_number += [-1, 1][random.randint(0, 1)]
        return False
