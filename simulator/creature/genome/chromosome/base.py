import random
from typing import Type

from simulator.creature.genome.chromosome.gene import BaseGene


class BaseChromosome:
    _mutation_chance = 0.02
    _disappearance_chance = 0.01
    # максимальное количество новых генов, которые могут появиться за одну мутацию
    max_new_genes = 5

    def __init__(self, genes: list[BaseGene]):
        self.genes = genes

    def __repr__(self) -> str:
        return repr(self.genes)

    def __len__(self) -> int:
        return len(self.genes)

    def __contains__(self, gene: Type[BaseGene] | BaseGene) -> bool:
        if isinstance(gene, type):
            gene_class = gene
        else:
            gene_class = gene.__class__
        genes_classes = [x.__class__ for x in self.genes]
        return gene_class in genes_classes

    def apply_genes(self, genome):
        """Записывает эффекты генов в хранилище."""

        for gene in self.genes:
            gene.apply(genome)
            gene.apply_resources_loss(genome)

    @property
    def disappearance_chance(self) -> float:
        if len(self) == 0:
            disappear_chance = self._disappearance_chance * 2
        else:
            disappear_chance = self._disappearance_chance / len(self)
            for gene in self.genes:
                if gene.disappearance_chance >= 0:
                    disappear_chance = 0
                    break
        return disappear_chance

    @property
    def mutation_chance(self) -> float:
        return self._mutation_chance + sum([gene.mutation_chance for gene in self.genes])

    def disappear(self) -> bool:
        can_disappear = False
        if random.random() < self.disappearance_chance:
            can_disappear = True
        return can_disappear

    # если возвращает True, хромосому необходимо удалить из генома
    def mutate(self, genome):
        # добавляются новые гены
        mutate_number = random.randint(0, len(self))
        if mutate_number == len(self):
            available_genes = BaseGene.get_available_genes(genome)
            new_genes_number = 1 + random.choices(
                range(self.max_new_genes), [1 / 5**x for x in range(self.max_new_genes)]
            )[0]
            weights = [gene.appearance_chance for gene in available_genes]

            new_genes = set(random.choices(available_genes, weights, k = new_genes_number))
            self.genes.extend(new_genes)

        # исчезновение генов
        # noinspection DuplicatedCode
        amount = random.choices(range(len(self)), [1 / 10**x for x in range(len(self))])[0]
        weights = [gene.disappearance_chance for gene in self.genes]
        if sum(weights) > 0:
            disappearing_genes = set(random.choices(self.genes, weights, k = amount))
            self.genes = [gene for gene in self.genes if gene not in disappearing_genes]

        # мутации генов
        amount = random.choices(range(len(self)), [1 / 10**x for x in range(len(self))])[0]
        amount = min(amount, len(self))
        weights = [gene.mutation_chance for gene in self.genes]
        # если хромосома пустая или содержит лишь гены, которые не могут мутировать,
        # то мутировать нечему (секция добавления генов в начале метода)
        if len(self) > 0 and sum(weights) > 0:
            genes_numbers = set(random.choices(range(len(self)), weights, k = amount))
            for number in genes_numbers:
                self.genes[number].mutate(genome)
