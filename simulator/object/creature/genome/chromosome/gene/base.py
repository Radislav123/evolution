

class BaseGene:
    def __init__(self):
        self._mutate_chance = 0.001

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}"

    @property
    def mutate_chance(self) -> float:
        return self._mutate_chance
