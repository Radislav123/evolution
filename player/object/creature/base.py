from typing import TYPE_CHECKING

import pygame

from core import models
from core.position import Position
from core.surface.base import CreatureSurface
from logger import BaseLogger
from player.object.base import BasePlaybackObject


# https://adamj.eu/tech/2021/05/13/python-type-hints-how-to-fix-circular-imports/
if TYPE_CHECKING:
    from player.object.world.base import BasePlaybackWorld


class BasePlaybackCreature(BasePlaybackObject, pygame.sprite.Sprite):
    db_model = models.Creature
    db_instance: models.Creature

    # position - левый верхний угол существа/спрайта
    def __init__(
            self,
            world: "BasePlaybackWorld",
            *args,
            **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.world = world
        self.screen = self.world.screen
        self.logger = BaseLogger(f"{self.world.object_id}.{self.object_id}")

        # origin_surface - хранится как эталон, от него делаются вращения и сохраняются в surface
        # не должно изменятся
        self.origin_surface = CreatureSurface.load_from_db(self.db_instance)
        # может быть изменено - оно отрисовывается на экране
        self.surface = self.origin_surface.copy()
        self.rect = self.surface.get_rect()
        self.rect.x = self.db_instance.start_x
        self.rect.y = self.db_instance.start_y

        self.start_tick = self.db_instance.start_tick
        self.stop_tick = self.db_instance.stop_tick

        self.movement_history = {
            movement.age: (movement.x, movement.y)
            for movement in models.CreatureMovement.objects.filter(creature = self.db_instance)
        }

    def __repr__(self):
        return self.object_id

    def is_alive(self) -> bool:
        """Проверяет живо ли существо в данный тик."""

        return self.start_tick <= self.world.age <= self.stop_tick

    @property
    def position(self):
        return Position(self.rect.x, self.rect.y)

    def draw(self):
        """Отрисовывает существо на экране."""

        self.screen.blit(self.surface, self.rect)

    def move(self, x, y):
        """Перемещает существо."""

        self.rect.move_ip(x, y)

    def tick(self):
        """Симулирует жизнедеятельность за один тик."""

        if self.is_alive():
            if self.world.age in self.movement_history:
                self.move(*self.movement_history[self.world.age])
