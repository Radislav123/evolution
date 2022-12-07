import pygame

from core import models
from evolution import settings


class Surface(pygame.Surface):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ORIGIN = self.copy()

    def convert(self, surface: pygame.Surface) -> pygame.Surface:
        new_surface = super().convert()
        new_surface.ORIGIN = self.ORIGIN
        return new_surface

    def save_to_db(self, object_id: str) -> models.Surface:
        """Сохраняет или обновляет объект в БД."""

        db_instance = models.Surface(
            object_id = object_id,
            image = pygame.image.tobytes(self.ORIGIN, settings.IMAGES_STORE_FORMAT),
            width = self.ORIGIN.get_width(),
            height = self.ORIGIN.get_height()
        )
        db_instance.save()
        return db_instance
