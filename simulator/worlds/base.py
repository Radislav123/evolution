import copy
import logging
from enum import Enum

import pygame

from simulator.creatures.base import BaseCreature
from simulator.loggers.base import BaseLogger, OBJECT_ID
from simulator.worlds.position import Position


class Mode(Enum):
    # interactive - симуляция идет и сразу отрисовывается
    # record - симуляция записывается в БД
    # play - воспроизведение записанной симуляции
    INTERACTIVE = "interactive"
    RECORD = "record"
    PLAY = "play"


class BaseWorld:
    counter = 0

    # width - минимальное значение ширины экрана - 120
    def __init__(self, mode: Mode, width = 1000, height = 1000, age = 0):
        self.id = f"{self.__class__.__name__}{self.counter}"
        self.__class__.counter += 1

        self.mode = mode
        self.age = age

        self.screen = pygame.display.set_mode((width, height))
        # {creature.id: creature}
        self.creatures: dict[str, BaseCreature] = {}
        self.logger = BaseLogger(self.__class__.__name__)
        self.logger = logging.LoggerAdapter(self.logger, {OBJECT_ID: self.id})

        self.logger.info("the world generates")
        self.logger.debug(f"world size - {self.screen.get_rect()[2]}:{self.screen.get_rect()[3]}")

        self.creatures_group = pygame.sprite.Group()

    def __repr__(self):
        return self.id

    def spawn_start_creatures(self, creatures_number: int):
        creatures_positions = [
            Position(self.screen.get_width()//2 - creatures_number//2 + pos_0, self.screen.get_height()//2)
            for pos_0 in range(creatures_number)
        ]
        new_creatures_list = [BaseCreature(position, self) for position in creatures_positions]
        new_creatures = {creature.id: creature for creature in new_creatures_list}

        for creature in new_creatures.values():
            creature.spawn()

    def add_creature(self, creature: BaseCreature):
        """Добавляет существо в мир."""

        self.creatures[creature.id] = creature
        creature.add(self.creatures_group)

    def remove_creature(self, creature: BaseCreature):
        """Убирает существо из мира."""

        del self.creatures[creature.id]
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

        old = self.get_resource(position, resource)
        self.logger.info(f"{self} {resource} store {old} -> {old + number}")

    # todo: write it
    def remove_resource(self, position: Position, resource, number):
        """Убирает количество ресурса из точки."""

        old = self.get_resource(position, resource)
        self.logger.info(f"{self} {resource} store {old} -> {old - number}")
