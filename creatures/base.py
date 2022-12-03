import pygame
from logging import Logger


class BaseCreature(pygame.sprite.Sprite):
    counter = 0

    def __init__(self, position: tuple[int, int], world, *args):
        super().__init__(*args)

        self.surface = pygame.Surface((50, 50))
        self.surface.fill((0, 0, 0))
        self.rectangle = self.surface.get_rect()
        self.rectangle.x = position[0]
        self.rectangle.y = position[1]

        self.world = world
        self.screen: pygame.Surface = world.screen
        self.logger: Logger = world.logger

        # должен быть уникальным для всех существ в мире
        self.id = f"{self.__class__.__name__}{BaseCreature.counter}"
        BaseCreature.counter += 1
        self.genes = None
        self.stats = None
        self.position = position

        self.logger.info(f"creature {self.id} was spawned")

    def draw(self):
        """Отрисовывает существо на экране."""
        self.screen.blit(self.surface, self.rectangle)

    def tick(self):
        """Симулирует жизнедеятельность за один тик."""

    # todo: remove this method
    def print_position(self):
        print(self.rectangle)
