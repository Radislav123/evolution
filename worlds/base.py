import pygame

from creatures.base import BaseCreature
from loggers.base import BaseLogger
from worlds.position import Position


class BaseWorld:
    # width - минимальное значение ширины экрана - 120
    def __init__(self, width = 1000, height = 1000, age = 0):
        self.screen = pygame.display.set_mode((width, height))
        self.age = age
        self.creatures: dict[str, BaseCreature] = {}
        self.logger = BaseLogger()

        self.logger.info("the world generates")
        self.logger.debug(f"world size - {self.screen.get_rect()[2]}:{self.screen.get_rect()[3]}")

    def spawn_start_creations(self, creatures_number: int) -> dict[BaseCreature]:
        creatures_positions = [
            Position(self.screen.get_width()//2 - creatures_number//2 + pos_0*100, self.screen.get_height()//2)
            for pos_0 in range(creatures_number)
        ]
        new_creatures_list = [BaseCreature(position, self) for position in creatures_positions]
        new_creatures = {creature.id: creature for creature in new_creatures_list}
        self.creatures.update(new_creatures)
        return new_creatures

    def tick(self):
        for _, creature in self.creatures.items():
            creature.tick()

    def draw(self):
        # залить фон белым
        self.screen.fill((255, 255, 255))
        for _, creature in self.creatures.items():
            creature.draw()

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def get_resource(self, position: Position, resource):
        """Возвращает количество единиц ресурса в точке."""
        return 100

    def check_resource(self, position: Position, resource, number):
        """Проверяет, хватает ли единиц ресурса в точке."""
        return self.get_resource(position, resource) >= number

    def remove_resource(self, position: Position, resource, number):
        """Убирает количество единиц ресурса из точки."""

    def add_resource(self, position: Position, resource, number):
        """Добавляет количество единиц ресурса в точку."""
