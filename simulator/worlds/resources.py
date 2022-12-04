from dataclasses import dataclass


@dataclass
class BaseResource:
    name: str
    formula: str

    def __hash__(self):
        return hash(self.name)

    def __repr__(self):
        return self.name


@dataclass(eq = False, repr = False)
# все энергетические ресурсы конвертируемы друг в друга
class EnergyResource(BaseResource):
    formula: str = None


LIGHT = EnergyResource("Light")
ENERGY = EnergyResource("Energy")
# https://ru.wikipedia.org/wiki/%D0%A5%D0%B8%D0%BC%D0%B8%D1%87%D0%B5%D1%81%D0%BA%D0%B8%D0%B9_%D1%81%D0%BE%D1%81%D1%82%D0%B0%D0%B2_%D1%87%D0%B5%D0%BB%D0%BE%D0%B2%D0%B5%D0%BA%D0%B0
OXYGEN = BaseResource("Oxygen", "O")
CARBON = BaseResource("Carbon", "C")
HYDROGEN = BaseResource("Hydrogen", "H")
