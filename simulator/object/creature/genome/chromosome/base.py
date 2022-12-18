from simulator.object.creature.genome.chromosome.gene.base import BaseGene


class BaseChromosome:
    def __init__(self):
        self.genes = [BaseGene()]
        self._mutate_chance = 0.02

    def __repr__(self) -> str:
        return repr(self.genes)

    @property
    def mutate_chance(self) -> float:
        return self._mutate_chance + sum([gene.mutate_chance for gene in self.genes])

    def mutate(self):
        # todo: write it
        pass
