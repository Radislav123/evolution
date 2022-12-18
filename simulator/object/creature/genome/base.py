from simulator.object.creature.genome.chromosome.base import BaseChromosome
import random
import copy
from typing import TYPE_CHECKING


# https://adamj.eu/tech/2021/05/13/python-type-hints-how-to-fix-circular-imports/
if TYPE_CHECKING:
    from simulator.object.creature.base import BaseSimulationCreature


class BaseGenome:
    def __init__(self, creature: "BaseSimulationCreature"):
        self.creature = creature

        self.chromosomes = [BaseChromosome()]
        # [0, 1]
        self._mutate_chance = 0.05

    def __repr__(self) -> str:
        string = ""
        for chromosome in self.chromosomes:
            string += f"{chromosome}\n"
        string = string[:-1]
        return string

    @property
    def mutate_chance(self) -> float:
        # todo: добавить возможность влияния внешних факторов на шанс мутации
        return self._mutate_chance + sum([chromosome.mutate_chance for chromosome in self.chromosomes])

    def mutate(self):
        mutate_number = random.randint(0, len(self.chromosomes))
        if mutate_number == len(self.chromosomes):
            self.chromosomes.append(BaseChromosome())
        else:
            self.chromosomes[mutate_number].mutate()

    def apply_genes(self):
        """Применяет эффекты генов на существо."""

    @staticmethod
    def get_child_genome(parents: list["BaseSimulationCreature"]) -> "BaseGenome":
        parent = parents[0]
        new_genome = parent.genome.__class__(None)
        new_genome.chromosomes = copy.deepcopy(parent.genome.chromosomes)
        if random.random() < new_genome.mutate_chance:
            new_genome.mutate()
        return new_genome
