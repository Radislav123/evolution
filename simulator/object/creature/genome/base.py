import copy
import random
from typing import TYPE_CHECKING, Type, TypeVar

from simulator.object.creature.bodypart.base import BaseBodypart
from simulator.object.creature.genome.chromosome.base import BaseChromosome
from simulator.object.creature.genome.chromosome.gene.base import BaseGene
from simulator.world_resource.base import BaseWorldResource


# https://adamj.eu/tech/2021/05/13/python-type-hints-how-to-fix-circular-imports/
if TYPE_CHECKING:
    from simulator.object.creature.base import BaseSimulationCreature

GENE_CLASS = TypeVar("GENE_CLASS", bound = BaseGene)


class GenomeEffects:
    """Хранилище эффектов генома."""

    def __init__(self):
        # не переносить определения в тело класса,
        # иначе не простые типы (list, dict) используются всеми экземплярами совместно
        self.children_number = 0
        self.size = 0.0
        self.elasticity = 0.0
        self.consumption_amount = 0
        self.consumption_resources: list[BaseWorldResource] = []
        self.bodyparts: list[BaseBodypart] = []
        self.resource_storages: dict[BaseWorldResource, int] = {}


class BaseGenome:
    # [0, 1]
    # todo: вернуть 0.05
    _mutation_chance = 1
    # максимальное количество новых хромосом, которые могут появиться за одну мутацию
    max_new_chromosomes = 3

    def __init__(self, chromosomes: list[BaseChromosome] | None, world_generation: bool = False):
        self.effects = GenomeEffects()
        # такая ситуация подразумевается только при генерации мира
        if world_generation:
            chromosomes = [BaseChromosome(BaseGene.get_required_for_creature_genes())]
        self.chromosomes = chromosomes

    def __repr__(self) -> str:
        string = f"{self.__class__.__name__}:\n"
        for chromosome in self.chromosomes:
            string += f"{chromosome}\n"
        if string[-1:] == "\n":
            string = string[:-1]
        return string

    def __len__(self) -> int:
        return len(self.chromosomes)

    def __contains__(self, gene: Type[BaseGene] | BaseGene) -> bool:
        if isinstance(gene, type):
            gene_class = gene
        else:
            gene_class = gene.__class__
        contains = False
        for chromosome in self.chromosomes:
            if gene_class in chromosome:
                contains = True
                break
        return contains

    def contains_all(self, genes: list[Type[BaseGene]] | list[BaseGene]) -> bool:
        if len(genes) == 0:
            return True

        if isinstance(genes[0], type):
            genes_classes = genes
        else:
            genes_classes = [gene.__class__ for gene in genes]
        contains = True
        for gene_class in genes_classes:
            if gene_class not in self:
                contains = False
                break
        return contains

    def get_genes(self, gene: Type[GENE_CLASS] | GENE_CLASS) -> list[GENE_CLASS]:
        """Ищет запрошенные гены и все дочерние."""

        if isinstance(gene, type):
            gene_class = gene
        else:
            gene_class = gene.__class__

        genes = []
        for chromosome in self.chromosomes:
            genes.extend([x for x in chromosome.genes if isinstance(x, gene_class)])
        return genes

    def count_genes(self, gene: BaseGene | Type[BaseGene]) -> int:
        return len(self.get_genes(gene))

    @property
    def mutation_chance(self) -> float:
        # todo: добавить возможность влияния внешних факторов на шанс мутации
        return self._mutation_chance + sum([chromosome.mutation_chance for chromosome in self.chromosomes])

    def mutate(self):
        # добавляются новые хромосомы
        mutate_number = random.randint(0, len(self))
        if mutate_number == len(self):
            new_chromosomes_number = 1 + random.choices(
                range(self.max_new_chromosomes), [1 / 10**x for x in range(self.max_new_chromosomes)]
            )[0]
            self.chromosomes.extend([BaseChromosome([])] * new_chromosomes_number)

        # исчезновение хромосом
        # noinspection DuplicatedCode
        amount = random.choices(range(len(self)), [1 / 10**x for x in range(len(self))])[0]
        weights = [chromosome.disappearance_chance for chromosome in self.chromosomes]
        chromosomes_numbers = set(random.choices(range(len(self)), weights, k = amount))
        for number in chromosomes_numbers:
            if self.chromosomes[number].disappear():
                del self.chromosomes[number]

        # мутации хромосом
        # noinspection DuplicatedCode
        amount = random.choices(range(len(self)), [1 / 10**x for x in range(len(self))])[0]
        weights = [chromosome.mutation_chance for chromosome in self.chromosomes]
        chromosomes_numbers = set(random.choices(range(len(self)), weights, k = amount))
        for number in chromosomes_numbers:
            self.chromosomes[number].mutate(self)

    def apply_genes(self):
        """Записывает эффекты генов в хранилище."""

        for chromosome in self.chromosomes:
            chromosome.apply_genes(self)

    @staticmethod
    def get_child_genome(parents: list["BaseSimulationCreature"]) -> "BaseGenome":
        parent = parents[0]
        child_genome = parent.genome.__class__(copy.deepcopy(parent.genome.chromosomes))
        if random.random() < child_genome.mutation_chance:
            child_genome.mutate()
        return child_genome
