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
    # -1 == до рождения : world.creatures_before_live
    # 0 == жизнь : world.creatures_living
    # 1 == после жизни/существо умерло : world.creatures_dead
    live_status = -1

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

            # соотносится с models.CreaturePositionHistory
            self.position_history: dict[int, tuple[float, float]] = {}
            self.load_position_history()
            # todo: брать размеры тела (и считать радиус) из сохраненных генов
            radius = 10
            self.scale = (radius * 2) / (sum(self.image_size) / 2)
        except Exception as error:
            error.init_creature = self
            raise error

    def __repr__(self):
        return self.object_id

    def load_position_history(self):
        position_history_db_instances = models.CreaturePositionHistory.objects.filter(creature_id = self.id)
        for position in position_history_db_instances:
            self.position_history[position.age] = (position.position_x, position.position_y)

    # noinspection PyMethodOverriding
    def on_update(self, delta_time: float):
        self.update_live_status()
        self.update_position()

    def update_live_status(self):
        if self.live_status == -1 and self.world.age == self.start_tick:
            self.live_status = 0
            self.world.creatures_before_live.remove(self)
            self.world.creatures_living.append(self)
        elif self.live_status == 0 and self.world.age == self.death_tick:
            self.live_status = 1
            self.world.creatures_living.remove(self)
            self.world.creatures_dead.append(self)

    def update_position(self):
        if self.world.age in self.position_history:
            self.position = self.position_history[self.world.age]
