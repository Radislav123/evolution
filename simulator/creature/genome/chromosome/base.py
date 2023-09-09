import dataclasses
import random
from collections import Counter
from typing import Self, TYPE_CHECKING, Type

from core.service import ObjectDescriptionReader
from evolution import settings
from simulator.creature.genome.chromosome.gene import GeneInterface


# https://adamj.eu/tech/2021/05/13/python-type-hints-how-to-fix-circular-imports/
if TYPE_CHECKING:
    from simulator.creature.genome import Genome


@dataclasses.dataclass
class ChromosomeDescriptor:
    name: str
    # [0, 1]
    base_mutation_chance: float
    base_disappearance_chance: float
    # максимальное количество новых генов, которые могут появиться за одну мутацию
    max_new_genes: int


chromosome_descriptor = ObjectDescriptionReader[ChromosomeDescriptor]().read_folder_to_list(
    settings.CHROMOSOME_JSON_PATH,
    ChromosomeDescriptor
)[0]


class Chromosome:
    # использование конструктора подразумевается только при создании первого существа
    # не использовать обратные ссылки (gene -> chromosome -> genome),
    # они сильно усложняют код и вызывают проблемы при копировании (а значит и при создании потомков) хромосом и генов
    def __init__(self, gene_classes: list[Type[GeneInterface]]) -> None:
        self.base_mutation_chance = chromosome_descriptor.base_mutation_chance
        self.base_disappearance_chance = chromosome_descriptor.base_disappearance_chance
        self.max_new_genes = chromosome_descriptor.max_new_genes
        self.genes = GeneInterface.construct_genes(True, gene_classes)
        self.gene_counter = Counter(x.name for x in self.genes)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}: {self.genes}"

    def __len__(self) -> int:
        return len(self.genes)

    def __contains__(self, gene: str | Type[GeneInterface] | GeneInterface) -> bool:
        if isinstance(gene, str):
            gene_name = gene
        else:
            gene_name = gene.name
        return gene_name in self.gene_counter

    @classmethod
    def get_first_chromosome(cls) -> Self:
        """Создает первую и единственную хромосому для первого существа."""

        return cls(GeneInterface.get_required_for_creature_gene_classes())

    @property
    def mutation_chance(self) -> float:
        return self.base_mutation_chance + sum(gene.mutation_chance for gene in self.genes)

    def get_disappearance_chance(self, genome: "Genome") -> float:
        if len(self.genes) == 0:
            disappearance_chance = self.base_disappearance_chance * 2
        else:
            disappearance_chance = self.base_disappearance_chance / len(self.genes)
            for gene in self.genes:
                if not gene.can_disappear(genome):
                    disappearance_chance = 0
                    break
        return disappearance_chance

    def mutate(self, genome: "Genome") -> None:
        # исчезновение генов
        if len(self.genes) > 0:
            amount = random.choices(range(len(self.genes)), [1 / 10**x for x in range(len(self.genes))])[0]
            weights = [gene.get_disappearance_chance(genome) for gene in self.genes]
            if sum(weights) > 0:
                disappearing_genes = set(random.choices(self.genes, weights, k = amount))
                self.gene_counter.subtract(x.name for x in disappearing_genes)
                self.genes = [gene for gene in self.genes if gene not in disappearing_genes]

        # добавляются новые гены
        mutate_number = random.randint(0, len(self.genes))
        if mutate_number == len(self.genes):
            available_gene_classes = GeneInterface.get_available_gene_classes(genome)
            weights = [gene.appearance_chance for gene in available_gene_classes]
            new_genes_number = 1 + random.choices(
                range(self.max_new_genes), [1 / 5**x for x in range(self.max_new_genes)]
            )[0]

            new_gene_classes = random.choices(available_gene_classes, weights, k = new_genes_number)
            self.gene_counter.update(x.name for x in new_gene_classes)
            self.genes.extend(GeneInterface.construct_genes(False, new_gene_classes))

        # мутации генов
        if len(self.genes) > 0:
            # noinspection DuplicatedCode
            amount = random.choices(range(len(self.genes)), [1 / 10**x for x in range(len(self.genes))])[0]
            amount = min(amount, len(self.genes))
            weights = [gene.mutation_chance for gene in self.genes]
            # если хромосома пустая или содержит лишь гены, которые не могут мутировать,
            # то мутировать нечему (секция добавления генов в начале метода)
            if sum(weights) > 0:
                genes_numbers = set(random.choices(range(len(self.genes)), weights, k = amount))
                for number in genes_numbers:
                    self.genes[number].mutate(genome)

    def apply_genes(self, genome: "Genome") -> None:
        """Записывает эффекты генов в хранилище."""

        for gene in self.genes:
            gene.apply(genome)
