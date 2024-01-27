import copy
import dataclasses
import random
from collections import Counter, defaultdict
from typing import Self, TYPE_CHECKING, Type

from core.service import ObjectDescriptionReader
from evolution import settings
from simulator.creature.genome.chromosome import Chromosome
from simulator.creature.genome.chromosome.gene import BodypartGeneInterface, GENE_CLASSES, GeneInterface, \
    GeneInterfaceClass
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
        self.bodyparts_genes: dict[str, dict[int, BodypartGeneInterface]] | None = None
        # {gene.required_bodypart_gene: {gene.required_gene_number: {gene}}}
        self.dependent_bodypart_genes: dict[str, dict[int, set[BodypartGeneInterface]]] | None = None
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
            temp_color = [max(self.color) for _ in range(3)]
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

    def prepare_bodypart_genes(self, genome: "Genome") -> None:
        bodypart_genes = [gene for chromosome in genome.chromosomes
                          for gene in chromosome.genes if isinstance(gene, BodypartGeneInterface)]

        for gene in bodypart_genes:
            # необходимый уникальный ген был потерян при мутации генома
            if (gene.required_bodypart_gene in genome.mutation["removed_uniq_bodypart_genes"] and
                    gene.required_gene_number in
                    genome.mutation["removed_uniq_bodypart_genes"][gene.required_bodypart_gene]):
                gene.required_gene_number = None

            # ген только появился в геноме
            if gene.number is None:
                gene.number = len(self.bodyparts_genes[gene.name])

            self.bodyparts_genes[gene.name][gene.number] = gene

        for gene in bodypart_genes:
            # ген только появился в геноме или необходимый уникальный ген был потерян при мутации генома
            # gene.name != "body_gene" - туловище не от чего не зависит
            if gene.required_gene_number is None and gene.name != "body_gene":
                gene.required_gene_number = random.choice(
                    list(self.bodyparts_genes[gene.required_bodypart_gene].keys())
                )

            self.dependent_bodypart_genes[gene.required_bodypart_gene][gene.required_gene_number].add(gene)


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

        self.mutation: dict[str, set[Chromosome] | dict[str | GeneInterfaceClass]] = {
            "removed": set(),
            "added": set(),
            "mutated": {
                "removed": set(),
                "added": set(),
                "mutated": set()
            },
            "removed_uniq_bodypart_genes": dict[str, dict[int, GeneInterfaceClass]]
        }

    def __repr__(self) -> str:
        string = [f"{self.__class__.__name__}:"]
        for chromosome in self.chromosomes:
            string.append(f"{chromosome}")
        return "\n".join(string)

    def __len__(self) -> int:
        return len(self.chromosomes)

    def __contains__(self, gene: str | Type[GeneInterface] | GeneInterfaceClass) -> bool:
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

    def mutate(self) -> None:
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
                        self.mutation["removed"].add(chromosome)

        # добавляются новые хромосомы
        mutate_number = random.randint(0, len(self.chromosomes))
        if mutate_number == len(self.chromosomes):
            new_chromosomes_number = 1 + random.choices(
                range(self.max_new_chromosomes), [1 / 10**x for x in range(self.max_new_chromosomes)]
            )[0]
            new_chromosomes = [Chromosome([]) for _ in range(new_chromosomes_number)]
            self.chromosomes.extend(new_chromosomes)
            self.mutation["added"].update(new_chromosomes)

        # мутации хромосом
        amount = random.choices(range(len(self.chromosomes)), [1 / 10**x for x in range(len(self.chromosomes))])[0]
        weights = [chromosome.mutation_chance for chromosome in self.chromosomes]
        chromosome_numbers = set(random.choices(range(len(self.chromosomes)), weights, k = amount))
        for number in chromosome_numbers:
            self.gene_counter.subtract(self.chromosomes[number].gene_counter)
            self.chromosomes[number].mutate(self)
            self.gene_counter.update(self.chromosomes[number].gene_counter)

        # обновляются списки и статистика
        self.mutation["removed_uniq_bodypart_genes"].update(
            {x.number: x for chromosome in self.mutation["removed"] for x in chromosome.genes
             if isinstance(x, BodypartGeneInterface) and x.uniq}
        )
        self.mutation["removed_uniq_bodypart_genes"].update(
            {x.number: x for x in self.mutation["mutated"]["removed"]
             if isinstance(x, BodypartGeneInterface) and x.uniq}
        )

        # сбрасываются гены, которые были в родительском геноме
        for chromosome in self.chromosomes:
            for gene in chromosome.genes:
                gene.active = None

    def apply_genes(self) -> None:
        """Записывает эффекты генов в хранилище."""

        self.effects.bodyparts_genes = defaultdict(dict)
        self.effects.dependent_bodypart_genes = defaultdict(lambda: defaultdict(set))
        self.effects.prepare_bodypart_genes(self)

        gene_classes: set[Type[GeneInterfaceClass]] = set()
        for chromosome in self.chromosomes:
            for gene in chromosome.genes:
                gene.check_activation(self)
                if gene.active:
                    gene.apply(self)
            gene_classes.update(gene.__class__ for gene in chromosome.genes)

        for gene_class in gene_classes:
            gene_class.correct(self)

        self.effects.bodyparts_genes.default_factory = None
        self.effects.dependent_bodypart_genes.default_factory = None
        for dependent_bodypart_genes in self.effects.dependent_bodypart_genes.values():
            dependent_bodypart_genes.default_factory = None

        self.effects.prepare()

    @classmethod
    def get_child_genome(cls, parents: list["Creature"]) -> "Genome":
        # todo: переделать этот метод при введении системы полового размножения
        parent = parents[0]
        child_genome = cls(copy.deepcopy(parent.genome.chromosomes), False)
        if random.random() <= child_genome.mutation_chance:
            child_genome.mutate()
        return child_genome

