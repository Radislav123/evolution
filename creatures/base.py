import pygame


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
        self.screen = world.screen

        BaseCreature.counter += 1
        # должен быть уникальным для всех существ в мире
        self.id = f"{self.__class__}.{BaseCreature.counter}"
        self.genes = None
        self.stats = None
        self.position = position

    def draw(self):
        """Отрисовывает существо на экране."""
        self.screen.blit(self.surface, self.rectangle)

    def tick(self):
        """Симулирует жизнедеятельность за один тик."""
        pass

    def print_position(self):
        print(self.rectangle)
