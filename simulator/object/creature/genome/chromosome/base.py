import random

from simulator.object.creature.genome.chromosome.gene.base import BaseGene


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

    def apply_genes(self, genome):
        """Записывает эффекты генов в хранилище."""

        for gene in self.genes:
            gene.apply(genome)

    @property
    def disappear_chance(self) -> float:
        if len(self) == 0:
            disappear_chance = self._disappearance_chance * 2
        else:
            disappear_chance = self._disappearance_chance / len(self)
        return disappear_chance

    @property
    def mutation_chance(self) -> float:
        return self._mutation_chance + sum([gene.mutation_chance for gene in self.genes])

    def disappear(self) -> bool:
        can_disappear = False
        if random.random() < self.disappear_chance:
            can_disappear = True
        return can_disappear

    # если возвращает True, хромосому необходимо удалить из генома
    def mutate(self, genome) -> bool:
        if self.disappear():
            return True

        # добавляются новые гены
        mutate_number = random.randint(0, len(self))
        if mutate_number == len(self):
            available_genes = BaseGene.get_available_genes()
            new_genes_number = 1 + random.choices(
                range(self.max_new_genes), [1 / 5**x for x in range(self.max_new_genes)]
            )[0]
            weights = [gene.appearance_chance for gene in available_genes]

            new_genes = set(random.choices(available_genes, weights, k = new_genes_number))
            self.genes.extend(new_genes)

        # мутации генов
        amount = random.choices(range(len(self)), [1 / 10**x for x in range(len(self))])[0]
        genes_numbers = set(random.choices(list(range(len(self))), k = amount))
        for number in genes_numbers:
            gene_disappear = self.genes[number].mutate(genome)
            if gene_disappear:
                del self.genes[number]

        return False
