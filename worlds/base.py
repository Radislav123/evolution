from creatures.base import BaseCreature
import pygame


class BaseWorld:
    def __init__(self, width = 1000, height = 1000, age = 0):
        self.screen = pygame.display.set_mode((width, height))
        self.age = age
        self.creatures: dict[str, BaseCreature] = {}

    def get_creatures_positions(self, creatures_number: int) -> list[tuple[int, int]]:
        return [(self.screen.get_width()//2 - creatures_number//2 + pos_0, self.screen.get_height()//2)
                for pos_0 in range(creatures_number)]

    def create_creatures(self, creatures_number: int) -> dict[BaseCreature]:
        new_creatures_list = [BaseCreature(position, self) for position in self.get_creatures_positions(creatures_number)]
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
