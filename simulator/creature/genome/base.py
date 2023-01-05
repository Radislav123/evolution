import copy
import random
from typing import TYPE_CHECKING, Type, TypeVar

from simulator.creature.bodypart import BaseBodypart
from simulator.creature.genome.chromosome import BaseChromosome
from simulator.creature.genome.chromosome.gene import BaseGene
from simulator.world_resource import Resources


# https://adamj.eu/tech/2021/05/13/python-type-hints-how-to-fix-circular-imports/
if TYPE_CHECKING:
    from simulator.creature import BaseSimulationCreature

GENE_CLASS = TypeVar("GENE_CLASS", bound = BaseGene)


class GenomeEffects:
    """Хранилище эффектов генома."""

    def __init__(self):
        # не переносить определения в тело класса,
        # иначе не простые типы (list, dict...) используются всеми экземплярами совместно
        self.children_number = 0
        self.size_coef = 0.0
        # todo: настроить гены, чтобы эластичность принадлежала отрезку [0, 1),
        #  где 0 - абсолютно твердое тела, а 1 - абсолютно упругое тело
        self.elasticity = 0.0
        self.consumption_amount = Resources()
        self.bodyparts: list[Type[BaseBodypart]] = []
        self.resource_storages = Resources()
        self.color: list[int] = [0, 0, 0]
        self.resources_loss = Resources()
        # MetabolismGene
        self.metabolism = 0.0
        # ResourcesLossCoefGene
        self.resources_loss_coef = 0.0
        self.regeneration_amount = 0

    def prepare(self):
        self.prepare_color()

    def prepare_color(self):
        other_color_numbers = {
            0: [1, 2],
            1: [0, 2],
            2: [0, 1]
        }

        # исправление отрицательных цветов (пигмент/цвет не может вырабатываться в отрицательном количестве)
        for i in range(len(self.color)):
            if self.color[i] < 0:
                self.color[i] = 0

        # подготовка цвета к субтрактивному применению (так применяет arcade)
        if max(self.color) > 255:
            temp_color = [max(self.color)] * 3
        else:
            temp_color = [255, 255, 255]
        for number in range(len(self.color)):
            for other_number in other_color_numbers[number]:
                temp_color[other_number] -= self.color[number]
        self.color = temp_color

        # корректировка отрицательных цветов
        minimum = min(self.color)
        if minimum < 0:
            for number in range(len(self.color)):
                self.color[number] -= minimum

        # нормализация цвета
        if max(self.color) > 255:
            maximum = max(self.color)
            if maximum != 0:
                for number in range(len(self.color)):
                    self.color[number] = self.color[number] * 255 // maximum


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
            self.chromosomes.extend([copy.deepcopy(BaseChromosome([])) for _ in range(new_chromosomes_number)])

        # исчезновение хромосом
        # noinspection DuplicatedCode
        amount = random.choices(range(len(self)), [1 / 10**x for x in range(len(self))])[0]
        weights = [chromosome.get_disappearance_chance(self) for chromosome in self.chromosomes]
        if sum(weights) > 0:
            disappearing_chromosomes = set(random.choices(self.chromosomes, weights, k = amount))
            self.chromosomes = [chromosome for chromosome in self.chromosomes
                                if chromosome not in disappearing_chromosomes]

        # мутации хромосом
        amount = random.choices(range(len(self)), [1 / 10**x for x in range(len(self))])[0]
        amount = min(amount, len(self))
        weights = [chromosome.mutation_chance for chromosome in self.chromosomes]
        chromosomes_numbers = set(random.choices(range(len(self)), weights, k = amount))
        for number in chromosomes_numbers:
            self.chromosomes[number].mutate(self)

    def apply_genes(self):
        """Записывает эффекты генов в хранилище."""

        gene_classes: set[Type[BaseGene]] = set()
        for chromosome in self.chromosomes:
            chromosome.apply_genes(self)
            gene_classes.update([gene.__class__ for gene in chromosome.genes])

        for gene_class in gene_classes:
            gene_class.correct(self)

        self.effects.prepare()

    @staticmethod
    def get_child_genome(parents: list["BaseSimulationCreature"]) -> "BaseGenome":
        parent = parents[0]
        child_genome = parent.genome.__class__(copy.deepcopy(parent.genome.chromosomes))
        if random.random() < child_genome.mutation_chance:
            child_genome.mutate()
        return child_genome
