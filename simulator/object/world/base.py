import copy
from enum import Enum

import pygame

from simulator import models
from simulator.logger.base import BaseLogger
from simulator.object.base import Object
from simulator.object.creature.base import BaseCreature
from simulator.object.position import Position


class Mode(Enum):
    # interactive - симуляция идет и сразу отрисовывается
    # record - симуляция записывается в БД
    # play - воспроизведение записанной симуляции
    INTERACTIVE = "interactive"
    RECORD = "record"
    PLAY = "play"


class BaseWorld(Object):
    db_model = models.World
    creatures_group: pygame.sprite.Group
    screen: pygame.Surface

    # width - минимальное значение ширины экрана - 120
    def __init__(self, width = 1000, height = 1000, age = 0, db_instance: db_model = None):
        self.age = age
        self.width = width
        self.height = height
        # {creature.object_id: creature}
        self.creatures: dict[str, BaseCreature] = {}
        self.logger = BaseLogger(self.object_id)

        self.creatures_group = pygame.sprite.Group()
        self.screen = pygame.display.set_mode((self.width, self.height))

        self.post_init()

    def save_to_db(self):
        self.db_instance = self.db_model(id = self.id, age = self.age, width = self.width, height = self.height)
        self.db_instance.save()

    def start(self):
        """Выполняет подготовительные действия при начале симуляции."""

        self.spawn_start_creature()

    def stop(self):
        """Выполняет завершающие действия при окончании симуляции."""

        self.release_logs()

    def release_logs(self):
        super().release_logs()
        for creature in self.creatures.values():
            creature.release_logs()

    def spawn_start_creature(self):
        creature = BaseCreature(Position(self.width//2, self.height//2), self)
        creature.spawn()

    def add_creature(self, creature: BaseCreature):
        """Добавляет существо в мир."""

        self.creatures[creature.object_id] = creature
        creature.add(self.creatures_group)

    def remove_creature(self, creature: BaseCreature):
        """Убирает существо из мира."""

        del self.creatures[creature.object_id]
        creature.kill()

    def tick(self):
        existing_creatures = copy.copy(self.creatures)
        for creature in existing_creatures.values():
            creature: BaseCreature
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
