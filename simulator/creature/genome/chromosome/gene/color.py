import abc

from simulator.creature.genome.chromosome.gene import Gene, StepGeneMixin


class ColorGene(StepGeneMixin, Gene, abc.ABC):
    required_for_creature = False
    step = 10
    # сейчас вырабатываемый пигмент не дает расхода ресурсов
    # потом можно будет добавить следующее - пигмент является синтезируемым веществом, накапливаемом в организме
    effect_attribute_name = None
    current = 0
    # RGB - red, green, blue - 0, 1, 2
    color_number: int

    def apply(self, genome):
        genome.effects.color[self.color_number] += self.current

    @classmethod
    def correct(cls, genome):
        pass

    def mutate(self, genome):
        self.current += self.make_step()
        if self.current < 0:
            self.current = 0


class RedGene(ColorGene):
    abstract = False
    color_number = 0


class GreenGene(ColorGene):
    abstract = False
    color_number = 1


class BlueGene(ColorGene):
    abstract = False
    color_number = 2


class MixColorGene(ColorGene):
    # разложение цвета на базовые (предполагается, что их сумма равна 1)
    red: float
    green: float
    blue: float

    def apply(self, genome):
        genome.effects.color[0] += int(self.current * self.red)
        genome.effects.color[1] += int(self.current * self.green)
        genome.effects.color[2] += int(self.current * self.blue)


class YellowGene(MixColorGene):
    abstract = False
    red = 0.5
    green = 0.5
    blue = 0


class CyanGene(MixColorGene):
    abstract = False
    red = 0
    green = 0.5
    blue = 0.5


class MagentaGene(MixColorGene):
    abstract = False
    red = 0.5
    green = 0
    blue = 0.5
