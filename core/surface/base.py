from pathlib import Path

import pygame

from core import models
from evolution import settings


class CreatureSurface(pygame.Surface):
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
    def load_from_file(cls, width: int, height: int) -> "CreatureSurface":
        """Загружает поверхность из файла."""

        filepath = f"{settings.SIMULATION_IMAGES_PATH}/BaseCreature.png"
        path = Path(filepath)
        surface = pygame.image.load(path).convert_alpha()
        surface = pygame.transform.scale(surface, (width, height))
        surface = cls.from_pygame_surface(surface)
        return surface
