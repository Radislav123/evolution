import copy

import pygame

from core import models
from core.physic.base import BaseWorldCharacteristics
from core.position import Position
from logger import BaseLogger
from player.object.world.base import BasePlaybackWorld
from simulator.object.base import BaseSimulationObject
from simulator.object.creature.base import BaseSimulationCreature


class BaseSimulationWorld(BaseSimulationObject):
    db_model = models.World
    creatures_group: pygame.sprite.Group
    screen: pygame.Surface
    draw = BasePlaybackWorld.draw

    # width - минимальное значение ширины экрана - 120
    def __init__(self, width: int, height: int):
        self._id = None
        self.age = 0
        self.width = width
        self.height = height
        # {creature.object_id: creature}
        self.creatures: dict[str, BaseSimulationCreature] = {}
        self.logger = BaseLogger(self.object_id)

        self.creatures_group = pygame.sprite.Group()
        self.screen = pygame.display.set_mode((self.width, self.height))

        self.characteristics = BaseWorldCharacteristics(1)

    @property
    def id(self) -> int:
        if self._id is None:
            self._id = self.db_model.objects.count()
        return self._id

    def save_to_db(self):
        self.db_instance = self.db_model(id = self.id, stop_tick = self.age, width = self.width, height = self.height)
        self.db_instance.save()

    def start(self):
        super().start()
        self.spawn_start_creature()

    def stop(self):
        super().stop()

        for creature in self.creatures.values():
            creature.stop()

    def release_logs(self):
        super().release_logs()

    def spawn_start_creature(self):
        creature = BaseSimulationCreature(
            Position(self.width // 2, self.height // 2),
            self,
            None,
            None,
            None,
            world_generation = True
        )
        creature.start()

    def add_creature(self, creature: BaseSimulationCreature):
        """Добавляет существо в мир."""

        self.creatures[creature.object_id] = creature
        creature.add(self.creatures_group)

    def remove_creature(self, creature: BaseSimulationCreature):
        """Убирает существо из мира."""

        del self.creatures[creature.object_id]
        creature.kill()

    def tick(self):
        existing_creatures = copy.copy(self.creatures)
        for creature in existing_creatures.values():
            creature: BaseSimulationCreature
            creature.tick()

        existing_creatures = list(self.creatures.values())
        for i in range(len(existing_creatures)):
            for j in range(i + 1, len(existing_creatures)):
                creature_0 = existing_creatures[i]
                creature_1 = existing_creatures[j]
                if pygame.sprite.collide_circle(creature_0, creature_1):
                    creature_0.collision_interact(creature_1)

        self.age += 1

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def get_resource(self, position: Position, resource):
        """Возвращает количество ресурса в точке."""

        return 100

    def check_resource(self, position: Position, resource, number):
        """Проверяет, хватает ли ресурса в точке."""

        return self.get_resource(position, resource) >= number

    # todo: write it
    def add_resource(self, position: Position, resource, number):
        """Добавляет количество ресурса в точку."""

    # todo: write it
    def remove_resource(self, position: Position, resource, number):
        """Убирает количество ресурса из точки."""
