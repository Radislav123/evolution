import copy

import pygame

from core import models
from core.position import Position
from logger import BaseLogger
from simulator.object import BaseSimulationObject
from simulator.object.creature import BaseSimulationCreature
from simulator.physic import BaseWorldCharacteristics
from simulator.world_resource import BaseWorldResource, CARBON, ENERGY, HYDROGEN, OXYGEN


class BaseSimulationWorld(BaseSimulationObject):
    db_model = models.World
    creatures_group: pygame.sprite.Group
    screen: pygame.Surface

    # width - минимальное значение ширины экрана - 120
    def __init__(self, width: int, height: int):
        self._id = None
        self.age = 0
        self.width = width
        self.height = height
        self.center = Position(width // 2, height // 2)
        self.chunk_width = 10
        self.chunk_height = 10

        # границы мира
        self.borders = BaseSimulationWorldBorders(0, self.width, 0, self.height)

        # {creature.object_id: creature}
        self.creatures: dict[str, BaseSimulationCreature] = {}
        self.logger = BaseLogger(self.object_id)

        self.creatures_group = pygame.sprite.Group()
        self.screen = pygame.display.set_mode((self.width, self.height))

        self.characteristics = BaseWorldCharacteristics(1)
        self.chunks = BaseSimulationWorldChunk.cut_world(self)

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
            copy.copy(self.center),
            self,
            None,
            world_generation = True
        )
        creature.start()

    def add_creature(self, creature: BaseSimulationCreature):
        """Добавляет существо в мир."""

        self.creatures[creature.object_id] = creature
        creature.add(self.creatures_group)

    # если существо необходимо убить, то это нужно сделать отдельно
    def remove_creature(self, creature: BaseSimulationCreature):
        """Убирает существо из мира."""

        del self.creatures[creature.object_id]

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

        for line in self.chunks:
            for chunk in line:
                chunk.tick()

        self.age += 1

    def get_resources(self, position: Position) -> dict[BaseWorldResource, int]:
        """Возвращает ресурсы в чанке."""

        return self.position_to_chunk(position).get_resources()

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def get_resource(self, position: Position, resource) -> int:
        """Возвращает ресурс в чанке."""

        return self.position_to_chunk(position).get_resource(resource)

    def add_resources(self, position: Position, resources: dict[BaseWorldResource, int]):
        """Добавляет ресурсы в чанк."""

        return self.position_to_chunk(position).add_resources(resources)

    def add_resource(self, position: Position, resource: BaseWorldResource, amount: int):
        """Добавляет ресурс в чанк."""

        return self.position_to_chunk(position).add_resource(resource, amount)

    def remove_resources(self, position: Position, resources: dict[BaseWorldResource, int]):
        """Убирает ресурсы из чанка."""

        return self.position_to_chunk(position).remove_resources(resources)

    def remove_resource(self, position: Position, resource: BaseWorldResource, amount: int):
        """Убирает ресурс из чанка."""

        return self.position_to_chunk(position).remove_resource(resource, amount)

    def draw(self):
        # залить фон белым
        self.screen.fill((255, 255, 255))
        for creature in self.creatures.values():
            creature.draw()

        self.borders.draw(self.screen)

        draw_chunks = False
        if draw_chunks:
            for line in self.chunks:
                for chunk in line:
                    chunk.draw(self.screen)

        pygame.display.flip()

    def position_to_chunk(self, position: Position) -> "BaseSimulationWorldChunk":
        x = (position.x - self.chunks[0][0].left) // self.chunk_width
        y = (position.y - self.chunks[0][0].top) // self.chunk_height
        if x < 0:
            x = 0
        if x > len(self.chunks) - 1:
            x = len(self.chunks) - 1
        if y < 0:
            y = 0
        if y > len(self.chunks[0]) - 1:
            y = len(self.chunks[0]) - 1
        return self.chunks[x][y]


class BaseSimulationWorldBorders:
    def __init__(self, left, right, top, bottom):
        self.left = left
        self.right = right
        self.top = top
        self.bottom = bottom
        self.color = (0, 0, 0)
        self.width = 1

    def draw(self, surface):
        rect = pygame.Rect(
            (self.left, self.top),
            (self.right - self.left, self.bottom - self.top)
        )
        pygame.draw.rect(surface, self.color, rect, self.width)


class BaseSimulationWorldChunk:
    def __init__(self, left_top: Position, width: int, height: int):
        self.color = (0, 0, 0)
        self.left = left_top.x
        self.right = self.left + width - 1
        self.top = left_top.y
        self.bottom = self.top + height - 1
        self.default_resource_amount = (self.right - self.left + 1) * (self.bottom - self.top + 1) * 5
        self.resources = {
            ENERGY: self.default_resource_amount,
            CARBON: self.default_resource_amount,
            OXYGEN: self.default_resource_amount,
            HYDROGEN: self.default_resource_amount
        }

    def __repr__(self) -> str:
        return f"{self.left, self.top, self.right, self.bottom}"

    def tick(self):
        self.resources[ENERGY] = self.default_resource_amount

    def get_resources(self) -> dict[BaseWorldResource, int]:
        return copy.copy(self.resources)

    def get_resource(self, resource: BaseWorldResource) -> int:
        return self.resources[resource]

    def add_resources(self, resources: dict[BaseWorldResource, int]):
        for resource, amount in resources.items():
            self.add_resource(resource, amount)

    def add_resource(self, resource: BaseWorldResource, amount: int):
        self.resources[resource] += amount

    def remove_resources(self, resources: dict[BaseWorldResource, int]):
        for resource, amount in resources.items():
            self.remove_resource(resource, amount)

    def remove_resource(self, resource: BaseWorldResource, amount: int):
        self.resources[resource] -= amount
        if self.resources[resource] < 0:
            raise ValueError(f"{self}: {resource} lack is {-self.resources[resource]}")

    def draw(self, surface):
        rect = pygame.Rect(
            (self.left - 1, self.top - 1),
            (self.right - self.left + 2, self.bottom - self.top + 2)
        )
        pygame.draw.rect(surface, self.color, rect, 1)

    @classmethod
    def cut_world(cls, world: BaseSimulationWorld) -> list[list["BaseSimulationWorldChunk"]]:
        chunks: list[list[cls]] = []

        left_top = copy.copy(world.center)
        while left_top.x > world.borders.left:
            left_top.x -= world.chunk_width
        while left_top.y > world.borders.top:
            left_top.y -= world.chunk_height

        for left in range(left_top.x, world.borders.right, world.chunk_width):
            line = len(chunks)
            chunks.append([])
            for top in range(left_top.y, world.borders.bottom, world.chunk_height):
                chunks[line].append(cls(Position(left, top), world.chunk_width, world.chunk_height))

        return chunks
