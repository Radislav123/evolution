import abc
import random
from typing import TYPE_CHECKING, Type, TypeVar


# https://adamj.eu/tech/2021/05/13/python-type-hints-how-to-fix-circular-imports/
if TYPE_CHECKING:
    from simulator.object.creature.genome import BaseGenome

step_type = TypeVar("step_type")


# если ген находится в другом файле, чтобы ген заработал, его базовый класс (или его самого)
# надо импортировать в gene/__init__.py
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
    step: step_type
    positive_step: step_type
    # число должно быть положительным (см. make_step)
    negative_step: step_type

    def __init__(self, first: bool):
        self.first = first

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}"

    def make_step(self) -> step_type:
        negative_step = self.negative_step if hasattr(self, "negative_step") else self.step
        positive_step = self.positive_step if hasattr(self, "positive_step") else self.step
        return [-negative_step, positive_step][random.randint(0, 1)]

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
