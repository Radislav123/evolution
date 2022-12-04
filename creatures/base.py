from logging import Logger
from typing import TYPE_CHECKING

import pygame

from creatures.genome.base import BaseGenome
from worlds.position import Position
from worlds.resources import c6h12o6, co2, h2o, light, o2


# https://adamj.eu/tech/2021/05/13/python-type-hints-how-to-fix-circular-imports/
if TYPE_CHECKING:
    from worlds.base import BaseWorld


# https://ru.wikipedia.org/wiki/%D0%A4%D0%BE%D1%82%D0%BE%D1%81%D0%B8%D0%BD%D1%82%D0%B5%D0%B7
# todo: убрать наследование от Sprite, если оно не нужно
class BaseCreature(pygame.sprite.Sprite):
    # ((in, out), (in, out), ...)
    eat_reactions = (({h2o: 6, co2: 6, light: 1}, {c6h12o6: 1, o2: 6}), )
    counter = 0

    # position - центр существа
    def __init__(self, position: Position, world: "BaseWorld", *args):
        super().__init__(*args)

        # должен быть уникальным для всех существ в мире
        self.id = f"{self.__class__.__name__}{BaseCreature.counter}"
        BaseCreature.counter += 1
        self.genome = BaseGenome()
        self.position = position

        self.surface = pygame.Surface((5, 5))
        self.surface.fill((0, 0, 0))
        self.rectangle = self.surface.get_rect()
        self.rectangle.x = self.position.x - self.rectangle[2]//2
        self.rectangle.y = self.position.y - self.rectangle[3]//2

        self.world = world
        self.screen: pygame.Surface = world.screen
        self.logger: Logger = world.logger

        # насыщение с точки зрения питания
        self.max_saturation = 100
        self.min_saturation = 0
        self.min_saturation = self.max_saturation//2

        self.log_info(f"spawns at {self.position}")

    def log_info(self, message):
        self.logger.info(f"{self.id} - {message}")

    def draw(self):
        """Отрисовывает существо на экране."""
        self.screen.blit(self.surface, self.rectangle)

    def tick(self):
        """Симулирует жизнедеятельность за один тик."""
        if self.can_eat():
            self.eat()

    def can_eat(self) -> bool:
        can_eat = True
        for resource, number in self.eat_reactions[0][0].items():
            can_eat = can_eat and self.world.check_resource(self.position, resource, number)
        return can_eat

    def eat(self):
        for resource, number in self.eat_reactions[0][0].items():
            self.world.remove_resource(self.position, resource, number)
            self.log_info(f"eat {self.eat_reactions[0]}")

    # todo: remove this method
    def print_position(self):
        print(self.rectangle)
