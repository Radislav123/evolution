import copy

import pygame

from core import models
from logger import BaseLogger
from simulator.object.base import BaseSimulationObject
from simulator.object.creature.base import BaseSimulationCreature
from simulator.object.position import Position


class BaseSimulationWorld(BaseSimulationObject):
    db_model = models.World
    creatures_group: pygame.sprite.Group
    screen: pygame.Surface

    # width - минимальное значение ширины экрана - 120
    def __init__(self, width: int, height: int, age: int):
        self.age = age
        self.width = width
        self.height = height
        # {creature.object_id: creature}
        self.creatures: dict[str, BaseSimulationCreature] = {}
        self.logger = BaseLogger(f"{self.object_id}_{self.logger_postfix}")

        self.creatures_group = pygame.sprite.Group()
        self.screen = pygame.display.set_mode((self.width, self.height))

    def save_to_db(self):
        self.db_instance = self.db_model(id = self.id, age = self.age, width = self.width, height = self.height)
        self.db_instance.save()

    def start(self):
        super().start()
        self.spawn_start_creature()

        # тут должно быть только одно существо
        for creature in self.creatures.values():
            creature.start()

    def stop(self):
        super().stop()

        for creature in self.creatures.values():
            creature.stop()

    def release_logs(self):
        super().release_logs()

    def spawn_start_creature(self):
        creature = BaseSimulationCreature(Position(self.width//2, self.height//2), self)
        creature.spawn()

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
            if collided_creatures := pygame.sprite.spritecollide(creature, self.creatures_group, False):
                # всегда пересекается с собой
                collided_creatures.remove(creature)
                for other_creature in collided_creatures:
                    creature.collision_interact(other_creature)
        self.age += 1

    def draw(self):
        # залить фон белым
        self.screen.fill((255, 255, 255))
        for creature in self.creatures.values():
            creature.draw()

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
