from pathlib import Path

from core import models
from evolution import settings


class CreatureSurface:
    db_model = models.CreatureSurface

    @classmethod
    def from_pygame_surface(cls, surface: pygame.Surface) -> "CreatureSurface":
        new_surface = CreatureSurface(
            surface.get_size(),
            surface.get_flags(),
            surface
        )
        new_surface.blit(surface, surface.get_rect())
        return new_surface

    @classmethod
    def load_from_file(cls, width: int, height: int, color: list[int]) -> "CreatureSurface":
        """Загружает поверхность из файла."""

        filepath = f"{settings.SIMULATION_IMAGES_PATH}/BaseCreature.png"
        path = Path(filepath)
        surface = pygame.image.load(path).convert_alpha()
        surface = pygame.transform.scale(surface, (width, height))
        # https://stackoverflow.com/a/625476/13186004
        # https://stackoverflow.com/a/49017847/13186004
        surface.fill(color, special_flags = pygame.BLEND_RGB_MIN)
        surface = cls.from_pygame_surface(surface)
        return surface
