import dataclasses
import random
from typing import TYPE_CHECKING, Type

from core.service import ObjectDescriptionReader
from simulator.creature.genome.chromosome.gene import Gene


# https://adamj.eu/tech/2021/05/13/python-type-hints-how-to-fix-circular-imports/
if TYPE_CHECKING:
    from simulator.creature.genome import Genome


class BaseChromosome:
    @dataclasses.dataclass
    class Descriptor:
        name: str
        # [0, 1]
        base_mutation_chance: float
        base_disappearance_chance: float
        # максимальное количество новых генов, которые могут появиться за одну мутацию
        max_new_genes: int

    def __init__(self, genes: list[Gene]):
        descriptor = ObjectDescriptionReader[self.Descriptor]().read_folder_to_list(
            "creature/genome/chromosome",
            self.Descriptor
        )[0]

        self.base_mutation_chance = descriptor.base_mutation_chance
        self.base_disappearance_chance = descriptor.base_disappearance_chance
        self.max_new_genes = descriptor.max_new_genes
        self.genes = genes

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}: {self.genes}"

    def __len__(self) -> int:
        return len(self.genes)

    def __contains__(self, gene: Type[Gene] | Gene) -> bool:
        if isinstance(gene, type):
            gene_class = gene
        else:
            gene_class = gene.__class__
        genes_classes = [x.__class__ for x in self.genes]
        return gene_class in genes_classes

    @property
    def mutation_chance(self) -> float:
        return self.base_mutation_chance + sum([gene.mutation_chance for gene in self.genes])

    def get_disappearance_chance(self, genome: "Genome") -> float:
        if len(self) == 0:
            disappearance_chance = self.base_disappearance_chance * 2
        else:
            disappearance_chance = self.base_disappearance_chance / len(self)
            for gene in self.genes:
                if not gene.can_disappear(genome):
                    disappearance_chance = 0
                    break
        return disappearance_chance

    # если возвращает True, хромосому необходимо удалить из генома
    def mutate(self, genome: "Genome"):
        # добавляются новые гены
        mutate_number = random.randint(0, len(self))
        if mutate_number == len(self):
            available_genes = Gene.get_available_genes(genome)
            new_genes_number = 1 + random.choices(
                range(self.max_new_genes), [1 / 5**x for x in range(self.max_new_genes)]
            )[0]
            weights = [gene.appearance_chance for gene in available_genes]

            new_genes = set(random.choices(available_genes, weights, k = new_genes_number))
            self.genes.extend(new_genes)

        # исчезновение генов
        # noinspection DuplicatedCode
        amount = random.choices(range(len(self)), [1 / 10**x for x in range(len(self))])[0]
        weights = [gene.get_disappearance_chance(genome) for gene in self.genes]
        if sum(weights) > 0:
            disappearing_genes = set(random.choices(self.genes, weights, k = amount))
            self.genes = [gene for gene in self.genes if gene not in disappearing_genes]

        # мутации генов
        if len(self) > 0:
            amount = random.choices(range(len(self)), [1 / 10**x for x in range(len(self))])[0]
            amount = min(amount, len(self))
            weights = [gene.mutation_chance for gene in self.genes]
            # если хромосома пустая или содержит лишь гены, которые не могут мутировать,
            # то мутировать нечему (секция добавления генов в начале метода)
            if sum(weights) > 0:
                genes_numbers = set(random.choices(range(len(self)), weights, k = amount))
                for number in genes_numbers:
                    self.genes[number].mutate(genome)

    def apply_genes(self, genome):
        """Записывает эффекты генов в хранилище."""

        for gene in self.genes:
            gene.apply(genome)
            gene.apply_resources_loss(genome)
