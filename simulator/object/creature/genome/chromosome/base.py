import random

from simulator.object.creature.genome.chromosome.gene.base import BaseGene


class BaseChromosome:
    def __init__(self, genes: list[BaseGene]):
        self.genes = genes
        self._mutate_chance = 0.02
        self._disappear_chance = 0.1

    def __repr__(self) -> str:
        return repr(self.genes)

    def __len__(self) -> int:
        return len(self.genes)

    def apply_genes(self, creature):
        """Применяет эффекты генов на существо."""

        for gene in self.genes:
            gene.apply(creature)

    @property
    def disappear_chance(self):
        if len(self) == 0:
            return 0
        else:
            return self._disappear_chance

    @property
    def mutate_chance(self) -> float:
        return self._mutate_chance + sum([gene.mutate_chance for gene in self.genes])

    # если возвращает True, хромосому необходимо удалить из генома
    def mutate(self, genome) -> bool:
        if len(self) == 0:
            if random.random() < self.disappear_chance:
                return True

        mutate_number = random.randint(0, len(self))
        if mutate_number == len(self):
            # todo: проверить это, когда будут доступные гены для добавления
            if False:
                available_genes = BaseGene.get_available_genes()
                self.genes.append(available_genes[random.randint(0, len(available_genes) - 1)])
        else:
            gene_disappear = self.genes[mutate_number].mutate(genome)
            if gene_disappear:
                del self.genes[mutate_number]

        return False
