from dataclasses import dataclass


@dataclass
class BaseWorldResource:
    name: str
    formula: str
    volume = 1
    mass = 1

    def __hash__(self):
        return hash(self.name)

    def __repr__(self):
        return self.name


@dataclass(eq = False, repr = False)
class EnergyResource(BaseWorldResource):
    formula: str = None
    volume = 0
    mass = 0

    def __init__(self, name):
        super().__init__(name, self.formula)
        self.formula = self.name.lower()


LIGHT = EnergyResource("Light")
ENERGY = EnergyResource("Energy")
# https://ru.wikipedia.org/wiki/%D0%A5%D0%B8%D0%BC%D0%B8%D1%87%D0%B5%D1%81%D0%BA%D0%B8%D0%B9_%D1%81%D0%BE%D1%81%D1%82%D0%B0%D0%B2_%D1%87%D0%B5%D0%BB%D0%BE%D0%B2%D0%B5%D0%BA%D0%B0
OXYGEN = BaseWorldResource("Oxygen", "O")
CARBON = BaseWorldResource("Carbon", "C")
HYDROGEN = BaseWorldResource("Hydrogen", "H")
