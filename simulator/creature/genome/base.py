import copy
import dataclasses
import random
from collections import Counter, defaultdict
from typing import Self, TYPE_CHECKING, Type

from core.service import ObjectDescriptionReader
from evolution import settings
from simulator.creature.genome.chromosome import Chromosome
from simulator.creature.genome.chromosome.gene import BodypartGeneInterface, GENE_CLASSES, GeneInterface
from simulator.world_resource import Resources


# https://adamj.eu/tech/2021/05/13/python-type-hints-how-to-fix-circular-imports/
if TYPE_CHECKING:
    from simulator.creature import Creature


class GenomeEffects:
    """Хранилище эффектов генома."""

    def __init__(self) -> None:
        # не переносить определения в тело класса,
        # иначе не простые типы (list, dict...) используются всеми экземплярами совместно
        # количество потомков, которые появляются при размножении
        self.children_amount = 0
        self.size_coeff = 0.0
        self.elasticity = 0.0
        self.metabolism = 0.0
        self.resources_loss_coeff = 0.0
        self.regeneration_amount = 0.0
        self.regeneration_amount_coeff: float | None = None
        # количество определенного ресурса, которое существо может потребить за тик
        self.consumption_amount = Resources[int]()
        # максимальная сумма всех ресурсов, которое существо может потребить за тик
        self.consumption_limit = 0
        # {gene.name: {gene.number: gene}}
        self.bodyparts_genes: defaultdict[str, dict[int, BodypartGeneInterface]] = defaultdict(dict)
        self.dependent_bodypart_genes: defaultdict[BodypartGeneInterface, set[BodypartGeneInterface]] | None = None
        self.color: list[int] = [0, 0, 0]
        self.action_weights: defaultdict[str, float] = defaultdict(float)
        self.action_duration_coeff: float | None = None

        self.consumption_weight_from_fullness = 0.0
        self.regeneration_weight_from_fullness = 0.0
        self.reproduction_weight_from_fullness = 0.0

    def prepare(self) -> None:
        self.prepare_color()

        # устанавливается влияние генов на длительность действий
        metabolism_gene_class = GENE_CLASSES["metabolism_gene"]
        resources_loss_coeff_gene_class = GENE_CLASSES["resources_loss_coeff_gene"]
        self.action_duration_coeff = (metabolism_gene_class.attribute_default / self.metabolism *
                                      resources_loss_coeff_gene_class.attribute_default / self.resources_loss_coeff)

        # устанавливается влияние сторонних генов на скорость регенерации
        self.regeneration_amount_coeff = ((1 + (1 / metabolism_gene_class.attribute_default**3) *
                                           (self.metabolism - metabolism_gene_class.attribute_default)**3) *
                                          (1 + (1 / resources_loss_coeff_gene_class.attribute_default**3) *
                                           (self.resources_loss_coeff -
                                            resources_loss_coeff_gene_class.attribute_default)**3))

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
            for number in range(len(self.color)):
                self.color[number] = int(self.color[number] * 255 // maximum)


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
        return self.base_mutation_chance + sum(chromosome.mutation_chance for chromosome in self.chromosomes)

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
            for gene in chromosome.genes:
                gene.apply(self)
                if not gene.active:
                    gene.activate(self)
            gene_classes.update(gene.__class__ for gene in chromosome.genes)

        # todo: body_gene часто является неактивным, как такое возможно?
        self.effects.dependent_bodypart_genes = defaultdict(set)
        for one_type_genes in self.effects.bodyparts_genes.values():
            for gene in one_type_genes.values():
                if gene.bodypart != "body" and gene.active:
                    if gene.bodypart == "storage":
                        gene.deactivate(self)
                        gene.activate(self)
                    if (gene.required_gene_number in (
                            required_bodypart_genes := self.effects.bodyparts_genes[gene.required_bodypart])):
                        self.effects.dependent_bodypart_genes[required_bodypart_genes[gene.required_gene_number]].add(
                            gene
                        )

        for gene_class in gene_classes:
            gene_class.correct(self)

        self.effects.prepare()

        # отключаются гены, для которых не выполнены условия активации
        for chromosome in self.chromosomes:
            for gene in chromosome.genes:
                if gene.can_be_deactivated and gene.active:
                    gene.deactivate(self)

    @classmethod
    def get_child_genome(cls, parents: list["Creature"]) -> "Genome":
        # todo: переделать этот метод при введении системы полового размножения
        parent = parents[0]
        child_genome = cls(copy.deepcopy(parent.genome.chromosomes), False)
        if random.random() <= child_genome.mutation_chance:
            child_genome.mutate()
        return child_genome
