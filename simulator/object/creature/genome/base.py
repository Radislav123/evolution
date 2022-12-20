import copy
import random
from typing import TYPE_CHECKING, Type, TypeVar

from simulator.object.creature.genome.chromosome.base import BaseChromosome
from simulator.object.creature.genome.chromosome.gene.base import BaseGene


# https://adamj.eu/tech/2021/05/13/python-type-hints-how-to-fix-circular-imports/
if TYPE_CHECKING:
    from simulator.object.creature.base import BaseSimulationCreature

GENE_CLASS = TypeVar("GENE_CLASS")


class GenomeEffects:
    """Хранилище эффектов генома."""
    children_number = 0
    size = 0
    elasticity = 0.0
    consumption_amount = 0


class BaseGenome:
    # [0, 1]
    _mutation_chance = 0.05
    # максимальное количество новых хромосом, которые могут появиться за одну мутацию
    max_new_chromosomes = 3

    def __init__(self, chromosomes: list[BaseChromosome] | None, world_generation: bool = False):
        self.effects = GenomeEffects()
        # такая ситуация подразумевается только при генерации мира
        if world_generation:
            chromosomes = [BaseChromosome(BaseGene.get_required_genes())]
        self.chromosomes = chromosomes

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
    def mutation_chance(self) -> float:
        # todo: добавить возможность влияния внешних факторов на шанс мутации
        return self._mutation_chance + sum([chromosome.mutation_chance for chromosome in self.chromosomes])

    def mutate(self):
        # добавляются новые хромосомы
        mutate_number = random.randint(0, len(self))
        if mutate_number == len(self):
            new_chromosomes_number = 1 + random.choices(
                range(self.max_new_chromosomes), [1 / 10**x for x in range(self.max_new_chromosomes)]
            )[0]
            self.chromosomes.extend([BaseChromosome([])] * new_chromosomes_number)

        # мутации хромосом
        amount = random.choices(range(len(self)), [1 / 10**x for x in range(len(self))])[0]
        chromosomes_numbers = random.sample(list(range(len(self))), k = amount)
        for number in chromosomes_numbers:
            chromosome_disappear = self.chromosomes[number].mutate(self)
            if chromosome_disappear:
                del self.chromosomes[number]

    def apply_genes(self):
        """Записывает эффекты генов в хранилище."""

        for chromosome in self.chromosomes:
            chromosome.apply_genes(self)

    @staticmethod
    def get_child_genome(parents: list["BaseSimulationCreature"]) -> "BaseGenome":
        parent = parents[0]
        new_genome = parent.genome.__class__(None, copy.deepcopy(parent.genome.chromosomes))
        if random.random() < new_genome.mutation_chance:
            new_genome.mutate()
        return new_genome
