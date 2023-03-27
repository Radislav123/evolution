from typing import TYPE_CHECKING

import arcade
import imagesize

from core import models
from core.mixin import WorldObjectMixin
from evolution import settings


if TYPE_CHECKING:
    from player.world import BasePlaybackWorld


class BasePlaybackCreature(WorldObjectMixin, arcade.Sprite):
    db_model = models.Creature
    image_path = settings.CREATURE_IMAGE_PATH
    image_size = imagesize.get(image_path)

    def __init__(self, creature_id: int, parents: list["BasePlaybackCreature"] | None, world: "BasePlaybackWorld"):
        try:
            super().__init__(self.image_path)

            self.id = creature_id
            self.parents = parents
            self.world = world
            self.db_instance = models.Creature.objects.get(id = self.id)
            self.start_tick = self.db_instance.start_tick
            self.stop_tick = self.db_instance.stop_tick
            self.death_tick = self.db_instance.death_tick
        except Exception as error:
            error.init_creature = self
            raise error

    def __repr__(self):
        return self.object_id
