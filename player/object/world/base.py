import pygame

from core import models
from logger import BaseLogger
from player.object import BasePlaybackObject
from player.object.creature import BasePlaybackCreature


class BasePlaybackWorld(BasePlaybackObject):
    db_model = models.World
    db_instance: models.World

    def __init__(self, db_id):
        super().__init__(db_id)
        self.age = 0
        self.stop_tick = self.db_instance.stop_tick
        self.width = self.db_instance.width
        self.height = self.db_instance.height

        self.logger = BaseLogger(self.object_id)
        self.screen = pygame.display.set_mode((self.width, self.height))

        # {creature.object_id: creature}
        self.creatures: dict[str, BasePlaybackCreature] = {}
        for creature_db_instance in models.Creature.objects.filter(world = self.db_instance):
            creature = BasePlaybackCreature(self, creature_db_instance.id)
            self.creatures[creature.object_id] = creature

    def tick(self):
        for creature in self.creatures.values():
            creature.tick()
        self.age += 1

    def draw(self):
        # залить фон белым
        self.screen.fill((255, 255, 255))
        for creature in self.creatures.values():
            creature.draw()

        pygame.display.flip()
