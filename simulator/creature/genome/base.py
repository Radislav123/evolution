import copy
import dataclasses
import random
from collections import Counter
from typing import Self, TYPE_CHECKING, Type

from core.service import ObjectDescriptionReader
from evolution import settings
from simulator.creature.genome.chromosome import Chromosome
from simulator.creature.genome.chromosome.gene import GeneInterface
from simulator.world_resource import Resources


# https://adamj.eu/tech/2021/05/13/python-type-hints-how-to-fix-circular-imports/
if TYPE_CHECKING:
    from simulator.creature import SimulationCreature


class GenomeEffects:
    """Хранилище эффектов генома."""

    def __init__(self) -> None:
        # не переносить определения в тело класса,
        # иначе не простые типы (list, dict...) используются всеми экземплярами совместно
        self.children_amount = 0
        self.size_coeff = 0.0
        self.elasticity = 0.0
        self.metabolism = 0.0
        self.resources_loss_coeff = 0.0
        self.regeneration_amount = 0
        # количество ресурса, которое существо может потребить за тик
        self.consumption_amount = Resources()
        # количество ресурсов, теряемых каждый тик
        self.resources_loss = Resources()
        self.bodyparts: list[str] = []
        self.resource_storages = Resources()
        self.color: list[int] = [0, 0, 0]

    def prepare(self) -> None:
        self.prepare_color()

    def prepare_color(self) -> None:
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


@dataclasses.dataclass
class GenomeDescriptor:
    name: str
    # [0, 1]
    base_mutation_chance: float
    # максимальное количество новых хромосом, которые могут появиться за одну мутацию
    max_new_chromosomes: int


genome_descriptor = ObjectDescriptionReader[GenomeDescriptor]().read_folder_to_list(
    settings.GENOME_DESCRIPTIONS_PATH,
    GenomeDescriptor
)[0]


class Genome:
    def __init__(self, chromosomes: list[Chromosome] | None, world_generation: bool):
        self.base_mutation_chance = genome_descriptor.base_mutation_chance
        self.max_new_chromosomes = genome_descriptor.max_new_chromosomes

        self.effects = GenomeEffects()
        # такая ситуация подразумевается только при генерации мира
        if world_generation:
            chromosomes = [Chromosome.get_first_chromosome()]
        self.chromosomes = chromosomes

        self.gene_counter = Counter()
        for chromosome in self.chromosomes:
            self.gene_counter.update(chromosome.gene_counter)

    def __repr__(self) -> str:
        string = f"{self.__class__.__name__}:\n"
        for chromosome in self.chromosomes:
            string += f"{chromosome}\n"
        if string[-1:] == "\n":
            string = string[:-1]
        return string

    def __len__(self) -> int:
        return len(self.chromosomes)

    def __contains__(self, gene: str | Type[GeneInterface] | GeneInterface) -> bool:
        if isinstance(gene, str):
            gene_name = gene
        else:
            gene_name = gene.name
        return gene_name in self.gene_counter

    @classmethod
    def get_first_genome(cls) -> Self:
        return cls(None, True)

    def contains_all(self, gene_names: list[str]) -> bool:
        for gene_name in gene_names:
            if self.gene_counter[gene_name] <= 0:
                contains = False
                break
        else:
            contains = True
        return contains

    @property
    def mutation_chance(self) -> float:
        # todo: добавить возможность влияния внешних факторов на шанс мутации
        return self.base_mutation_chance + sum([chromosome.mutation_chance for chromosome in self.chromosomes])

    def mutate(self):
        # исчезновение хромосом
        if len(self.chromosomes) > 1:
            amount = random.choices(range(len(self.chromosomes)), [1 / 10**x for x in range(len(self.chromosomes))])[0]
            weights = [chromosome.get_disappearance_chance(self) for chromosome in self.chromosomes]
            if sum(weights) > 0:
                disappearing_chromosomes = set(random.choices(self.chromosomes, weights, k = amount))
                for chromosome in disappearing_chromosomes:
                    if chromosome.can_disappear(self):
                        self.gene_counter.subtract(chromosome.gene_counter)
                        self.chromosomes.remove(chromosome)

        # добавляются новые хромосомы
        mutate_number = random.randint(0, len(self.chromosomes))
        if mutate_number == len(self.chromosomes):
            new_chromosomes_number = 1 + random.choices(
                range(self.max_new_chromosomes), [1 / 10**x for x in range(self.max_new_chromosomes)]
            )[0]
            self.chromosomes.extend([Chromosome([]) for _ in range(new_chromosomes_number)])

        # мутации хромосом
        amount = random.choices(range(len(self.chromosomes)), [1 / 10**x for x in range(len(self.chromosomes))])[0]
        weights = [chromosome.mutation_chance for chromosome in self.chromosomes]
        chromosome_numbers = set(random.choices(range(len(self.chromosomes)), weights, k = amount))
        for number in chromosome_numbers:
            self.gene_counter.subtract(self.chromosomes[number].gene_counter)
            self.chromosomes[number].mutate(self)
            self.gene_counter.update(self.chromosomes[number].gene_counter)

    def apply_genes(self):
        """Записывает эффекты генов в хранилище."""

        gene_classes: set[Type[GeneInterface]] = set()
        for chromosome in self.chromosomes:
            chromosome.apply_genes(self)
            gene_classes.update([gene.__class__ for gene in chromosome.genes])

        for gene_class in gene_classes:
            gene_class.correct(self)

        self.effects.prepare()

    @classmethod
    def get_child_genome(cls, parents: list["SimulationCreature"]) -> "Genome":
        # todo: переделать этот метод при введении системы полового размножения
        parent = parents[0]
        child_genome = cls(copy.deepcopy(parent.genome.chromosomes), False)
        if random.random() < child_genome.mutation_chance:
            child_genome.mutate()
        return child_genome
