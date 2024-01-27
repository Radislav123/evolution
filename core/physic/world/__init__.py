from core import models
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from simulator.world import World


class WorldCharacteristics:
    """Физические характеристики мира."""

    db_model = models.WorldCharacteristics
    db_instance: db_model

    def __init__(self, viscosity: float, border_friction: float, border_thickness: int, resource_density: float):
        # вязкость
        # 1 - объекты теряют всю скорость после каждого тика
        # 0 - не теряют скорости вообще
        if not 0 <= viscosity <= 1:
            raise ValueError(f"Viscosity must belong to [0, 1], but {viscosity} was given")
        self.viscosity = viscosity
        self.border_friction = border_friction
        self.border_thickness = border_thickness
        self.resource_density = resource_density

    def __repr__(self) -> str:
        string = f"viscosity: {self.viscosity}, border friction: {self.border_friction}, "
        string += f"border thickness: {self.border_thickness}, resources coef: {self.resource_density}"
        return string

    def save_to_db(self, world: "World"):
        self.db_instance = self.db_model(
            world = world.db_instance,
            viscosity = self.viscosity,
            border_friction = self.border_friction,
            border_thickness = self.border_thickness,
            resource_coeff = self.resource_density
        )
        self.db_instance.save()
