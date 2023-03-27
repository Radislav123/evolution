import functools
from typing import Iterable

import arcade

from core import models
from core.physic import BaseWorldCharacteristics
from player.creature import BasePlaybackCreature
from simulator.world import BaseSimulationWorld


# todo: добавить историю перемещений существам
# todo: добавить воспроизведение перемещений существ
class BasePlaybackWorld:
    db_model = models.World
    borders: arcade.SpriteList
    creatures: arcade.SpriteList

    def __init__(self, world_id: int):
        self.id = world_id
        self.db_instance = models.World.objects.get(id = self.id)
        self.age = 0
        self.stop_tick = self.db_instance.stop_tick
        self.width = self.db_instance.width
        self.height = self.db_instance.height
        self.center = (self.db_instance.center_x, self.db_instance.center_y)
        self.chunk_width = self.db_instance.chunk_width
        self.chunk_height = self.db_instance.chunk_height

        # {creature.object_id: creature}
        creature_db_instances = models.Creature.objects.filter(world_id = self.id)
        self.creatures = arcade.SpriteList(capacity = len(creature_db_instances))
        self.load_creatures(creature_db_instances)

        characteristics = models.WorldCharacteristics.objects.get(world_id = self.id)
        self.characteristics = BaseWorldCharacteristics(
            characteristics.viscosity,
            characteristics.borders_friction,
            characteristics.borders_thickness,
            characteristics.resource_coef
        )
        self.get_borders_coordinates = functools.partial(getattr(BaseSimulationWorld, "get_borders_coordinates"), self)
        self.prepare_borders = functools.partial(getattr(BaseSimulationWorld, "prepare_borders"), self)
        self.prepare_borders()
        # todo: добавить чанки

    def load_creatures(self, creature_db_instances: Iterable[BasePlaybackCreature]):
        # todo: добавить сохранение родителей существ
        creature_parent = models.CreatureParent.objects.filter(world_id = self.id)
        not_instantiated_creatures = list(creature_db_instances)
        # существа без родителей
        for creature in creature_db_instances:
            if len(creature_parent.filter(creature = creature)) == 0:
                not_instantiated_creatures.remove(creature)
                self.creatures.append(
                    BasePlaybackCreature(
                        creature.id,
                        None,
                        self
                    )
                )

        # все остальные существа
        # todo: переделать для случаев с несколькими родителями
        while len(not_instantiated_creatures) > 0:
            for parent in self.creatures:
                children = creature_parent.filter(parent_id = parent.id)
                for child in children:
                    not_instantiated_creatures.remove(child)
                    self.creatures.append(
                        BasePlaybackCreature(
                            child.id,
                            [parent],
                            self
                        )
                    )
