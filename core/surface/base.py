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
    def save_to_db(cls, surface: "CreatureSurface", creature_db_instance) -> db_model:
        """Сохраняет или обновляет поверхность в БД."""

        db_instance = cls.db_model(
            creature = creature_db_instance,
            image = pygame.image.tobytes(surface, settings.IMAGES_STORE_FORMAT),
            width = surface.get_width(),
            height = surface.get_height()
        )
        db_instance.save()
        return db_instance

    @classmethod
    def load_from_db(cls, creature_db_instance) -> "CreatureSurface":
        """Загружает поверхность из БД."""

        db_instance = cls.db_model.objects.get(creature = creature_db_instance)
        surface = pygame.image.frombytes(
            db_instance.image.tobytes(),
            (db_instance.width, db_instance.height),
            settings.IMAGES_STORE_FORMAT
        ).convert()
        surface = cls.from_pygame_surface(surface)
        return surface

    @classmethod
    def load_from_file(cls, filepath: str) -> "CreatureSurface":
        """Загружает поверхность из файла."""

        path = Path(filepath)
        surface = pygame.image.load(path)
        surface = cls.from_pygame_surface(surface)
        return surface
