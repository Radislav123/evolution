import logging
from pathlib import Path
from typing import TYPE_CHECKING

import pygame

from evolution.settings import IMAGES_PATH
from simulator.creatures.genome.base import BaseGenome
from simulator.creatures.resources import BaseCreatureStorage
from simulator.loggers.base import OBJECT_ID
from simulator.worlds.position import Position
from simulator.worlds.resources import CARBON, ENERGY, HYDROGEN, LIGHT, OXYGEN


# https://adamj.eu/tech/2021/05/13/python-type-hints-how-to-fix-circular-imports/
if TYPE_CHECKING:
    from simulator.worlds.base import BaseWorld


class CollisionException(BaseException):
    pass


# https://ru.wikipedia.org/wiki/%D0%A4%D0%BE%D1%82%D0%BE%D1%81%D0%B8%D0%BD%D1%82%D0%B5%D0%B7
class BaseCreature(pygame.sprite.Sprite):
    # ((consume, _storage, throw), (consume, _storage, throw), ...)
    counter = 0

    # position - левый верхний угол существа/спрайта
    def __init__(
            self,
            position: Position,
            world: "BaseWorld",
            parents: list["BaseCreature"] = None,
            storage: BaseCreatureStorage = None,
            *args
    ):
        super().__init__(*args)

        # должен быть уникальным для всех существ в мире
        self.id = f"{self.__class__.__name__}{self.counter}"
        self.__class__.counter += 1

        self.consumption_process = (
            {OXYGEN: 2, CARBON: 2, HYDROGEN: 2, LIGHT: 2},
            {OXYGEN: 1, CARBON: 1, HYDROGEN: 1, ENERGY: 1},
            {OXYGEN: 1, CARBON: 1, HYDROGEN: 1}
        )
        self.genome = BaseGenome()

        self.surface = pygame.image.load(Path(f"{IMAGES_PATH}/{self.__class__.__name__}.bmp")).convert()
        self.rect = self.surface.get_rect()
        self.rect.x = position.x
        self.rect.y = position.y

        self.world = world
        self.screen = world.screen
        self.logger = world.logger.logger.getChild(self.__class__.__name__)
        self.logger = logging.LoggerAdapter(self.logger, {OBJECT_ID: self.id})

        self.parents = parents

        # такая ситуация подразумевается только при генерации мира
        if storage is None:
            start_resources = [
                (CARBON, 100, 50),
                (OXYGEN, 100, 50),
                (HYDROGEN, 100, 50),
                (ENERGY, 100, 50),
            ]
            storage = BaseCreatureStorage(self, start_resources)
        self.storage = storage

    def __repr__(self):
        return self.id

    @property
    def position(self):
        return Position(self.rect.x, self.rect.y)

    def spawn(self):
        self.world.add_creature(self)
        self.storage.spawn()
        self.logger.info(f"spawns at {self.position}")

    def draw(self):
        """Отрисовывает существо на экране."""

        self.screen.blit(self.surface, self.rect)

    def tick(self):
        """Симулирует жизнедеятельность за один тик."""

        if self.can_consume():
            self.consume()
        if self.can_reproduce():
            self.reproduce()

    def move(self, x, y):
        self.rect.move_ip(x, y)

    def share_storage_with_children(self, children_number: int) -> list[BaseCreatureStorage]:
        new_storages = []
        for i in range(children_number):
            resources = []
            for world_resource, stored_resource in self.storage.items():
                child_resource_number = stored_resource.current//(children_number + 1)
                self.storage[world_resource].remove(child_resource_number)
                resources.append((world_resource, stored_resource.capacity, child_resource_number))
            new_storages.append(self.storage.__class__(None, resources))

        return new_storages

    def can_reproduce(self) -> bool:
        if self.storage[CARBON].is_full:
            return True
        return False

    def reproduce(self) -> list["BaseCreature"]:
        """Симулирует размножение существа."""

        newborns_number = 1
        children = [
            self.__class__(
                Position(self.position.x + 1 + count_storage[0], self.position.y),
                self.world, [self],
                count_storage[1]
            )
            for count_storage in enumerate(self.share_storage_with_children(newborns_number))
        ]

        self.move(-1, 0)

        for count, child in enumerate(children):
            child.storage.creature = child
            child.spawn()

        return children

    def can_consume(self) -> bool:
        can_consume = True
        for resource, number in self.consumption_process[0].items():
            can_consume = can_consume and self.world.check_resource(self.position, resource, number)
        for resource, number in self.consumption_process[1].items():
            can_consume = can_consume and self.storage.can_store(resource, number)
        return can_consume

    def consume(self):
        """Симулирует потребление веществ существом."""

        # забирает из мира ресурсы
        for resource, number in self.consumption_process[0].items():
            self.world.remove_resource(self.position, resource, number)
        # добавляет в свое хранилище
        for resource, number in self.consumption_process[1].items():
            self.storage.add_to_storage(resource, number)
        # отдает ресурсы в мир
        for resource, number in self.consumption_process[2].items():
            self.world.add_resource(self.position, resource, number)
        self.logger.info(
            f"consume: {self.consumption_process[0]}"
            f" | store: {self.consumption_process[1]}"
            f" | throw {self.consumption_process[2]}"
        )

    def collision_interact(self, other: "BaseCreature"):
        if self.position == other.position:
            raise CollisionException(f"{self} and {other} have identical positions")
        else:
            if self.position.x != other.position.x:
                x_move = (self.position.x - other.position.x)//abs(self.position.x - other.position.x)
            else:
                x_move = 0

            if self.position.y != other.position.y:
                y_move = (self.position.y - other.position.y)//abs(self.position.y - other.position.y)
            else:
                y_move = 0

            self.move(x_move, y_move)
            other.move(-x_move, -y_move)
