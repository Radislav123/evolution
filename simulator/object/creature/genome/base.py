import copy
import random
from typing import TYPE_CHECKING, Type, TypeVar

from simulator.object.creature.genome.chromosome.base import BaseChromosome
from simulator.object.creature.genome.chromosome.gene.base import BaseGene


# https://adamj.eu/tech/2021/05/13/python-type-hints-how-to-fix-circular-imports/
if TYPE_CHECKING:
    from simulator.object.creature.base import BaseSimulationCreature

GENE_CLASS = TypeVar("GENE_CLASS")


class BaseGenome:
    def __init__(
            self,
            creature: "BaseSimulationCreature",
            chromosomes: list[BaseChromosome] | None,
            world_generation: bool = False
    ):
        self.creature = creature

        # такая ситуация подразумевается только при генерации мира
        if world_generation:
            chromosomes = [BaseChromosome(BaseGene.get_required_genes())]
        self.chromosomes = chromosomes
        # [0, 1]
        self._mutate_chance = 0.05

    def __repr__(self) -> str:
        string = ""
        for chromosome in self.chromosomes:
            string += f"{chromosome}\n"
        string = string[:-1]
        return string

    def __len__(self) -> int:
        return len(self.chromosomes)

    def get_genes(self, gene_class: Type[GENE_CLASS]) -> list[GENE_CLASS]:
        genes = []
        for chromosome in self.chromosomes:
            genes.extend([x for x in chromosome.genes if isinstance(x, gene_class)])
        return genes

    @property
    def mutate_chance(self) -> float:
        # todo: добавить возможность влияния внешних факторов на шанс мутации
        return self._mutate_chance + sum([chromosome.mutate_chance for chromosome in self.chromosomes])

    def mutate(self):
        mutate_number = random.randint(0, len(self))
        if mutate_number == len(self):
            self.chromosomes.append(BaseChromosome([]))
        else:
            chromosome_disappear = self.chromosomes[mutate_number].mutate(self)
            if chromosome_disappear:
                del self.chromosomes[mutate_number]

    def apply_genes(self):
        """Применяет эффекты генов на существо."""

    @staticmethod
    def get_child_genome(parents: list["BaseSimulationCreature"]) -> "BaseGenome":
        parent = parents[0]
        new_genome = parent.genome.__class__(None, copy.deepcopy(parent.genome.chromosomes))
        if random.random() < new_genome.mutate_chance:
            new_genome.mutate()
        return new_genome
