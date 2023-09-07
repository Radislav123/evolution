import abc
import dataclasses
import random
from typing import Literal, Self, TYPE_CHECKING, Type, TypeVar

from core.mixin import GetSubclassesMixin
from core.service import ObjectDescriptionReader
from evolution import settings


# https://adamj.eu/tech/2021/05/13/python-type-hints-how-to-fix-circular-imports/
if TYPE_CHECKING:
    from simulator.creature.genome import Genome

step_type = TypeVar("step_type")


@dataclasses.dataclass
class GeneDescriptor:
    name: str
    # по умолчанию класс гена абстрактный (появляется ли у существа)
    abstract: bool
    # обязательно ли присутствие хотя бы одного такого гена в геноме (могут ли все копии пропасть из генома)
    required_for_creature: bool
    # список названий (name) генов, необходимых для появления этого гена
    # необходимые гены не должны быть абстрактными, так как абстрактные не могут появиться у существа,
    # значит не появится и тот, что содержит в этом списке хотя бы один абстрактный ген (интерфейс)
    required_genes: list[str]
    mutation_chance: float
    base_disappearance_chance: float
    appearance_chance: float


all_gene_descriptors = ObjectDescriptionReader[GeneDescriptor]().read_folder_to_dict(
    settings.GENE_JSON_PATH,
    GeneDescriptor
)
gene_descriptor = all_gene_descriptors["gene"]


# если ген находится в другом файле, чтобы ген заработал/появился, его базовый класс (или его самого)
# надо импортировать в gene/__init__.py
class Gene(GetSubclassesMixin, abc.ABC):
    _all_genes: dict[str, Type["Gene"]] = None

    @classmethod
    def all_genes(cls) -> dict[str, Type["Gene"]]:
        if cls._all_genes is None:
            cls._all_genes = {x(False).name: x for x in Gene.get_all_subclasses()}
        return cls._all_genes

    name = gene_descriptor.name
    abstract = gene_descriptor.abstract
    required_for_creature = gene_descriptor.required_for_creature
    required_genes = [all_genes()[x] for x in gene_descriptor.required_genes]
    mutation_chance = gene_descriptor.mutation_chance
    base_disappearance_chance = gene_descriptor.base_disappearance_chance
    appearance_chance = gene_descriptor.appearance_chance

    def __init__(self, first: bool):
        self.first = first

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}"

    def get_disappearance_chance(self, genome: "Genome") -> float:
        if not self.can_disappear(genome):
            disappearance_chance = 0
        else:
            disappearance_chance = self.base_disappearance_chance
        return disappearance_chance

    def can_disappear(self, genome: "Genome") -> bool:
        """Проверяет, может ли ген исчезнуть."""

        return not self.required_for_creature or self.required_for_creature and genome.count_genes(self) > 1

    @abc.abstractmethod
    def mutate(self, genome: "Genome"):
        raise NotImplementedError()

    @abc.abstractmethod
    def apply(self, genome: "Genome"):
        """Записывает эффекты гена в хранилище."""

        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def correct(cls, genome: "Genome"):
        """Корректирует суммарный эффект генов данного типа после применения каждого по отдельности."""

        raise NotImplementedError()

    @classmethod
    def get_required_for_creature_genes(cls) -> list[Type[Self]]:
        """Возвращает гены для вставки в геном первого существа."""

        return [gene(True) for gene in cls.get_all_subclasses() if not gene.abstract and gene.required_for_creature]

    @classmethod
    def get_available_genes(cls, genome: "Genome") -> list[Type[Self]]:
        """Возвращает список генов, возможных для добавления в процессе мутации."""

        return [
            gene(False) for gene in cls.get_all_subclasses()
            if not gene.abstract and genome.contains_all(gene.required_genes) and gene.appearance_chance > 0
        ]


class StepGeneMixin:
    # шаг изменения влияния гена
    step: step_type
    positive_step: step_type
    # число должно быть положительным (см. make_step)
    negative_step: step_type
    # минимальное значение влияния гена
    min_limit: int
    # максимальное значение влияния гена
    max_limit: int
    # минимальное значение влияния всех таких генов
    common_min_limit: int
    # максимальное значение влияния всех таких генов
    common_max_limit: int

    def make_step(self, sign: Literal['+', '-', None] = None) -> step_type:
        negative_step = self.negative_step if hasattr(self, "negative_step") else self.step
        positive_step = self.positive_step if hasattr(self, "positive_step") else self.step
        if sign is None:
            step = [-negative_step, positive_step][random.randint(0, 1)]
        elif sign == '+':
            step = positive_step
        elif sign == '-':
            step = negative_step
        else:
            step = None
        return step
