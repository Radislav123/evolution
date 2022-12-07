from pathlib import Path
from typing import TYPE_CHECKING

import pygame

from core import models
from evolution import settings
from logger import BaseLogger
from player.object.base import BasePlaybackObject

# https://adamj.eu/tech/2021/05/13/python-type-hints-how-to-fix-circular-imports/
if TYPE_CHECKING:
    from player.object.world.base import BasePlaybackObject


class BasePlaybackCreature(pygame.sprite.Sprite, BasePlaybackObject):
    db_model = models.Creature
    db_instance: models.Creature

    # position - левый верхний угол существа/спрайта
    def __init__(
            self,
            world: "BasePlaybackObject",
            parents: list["BasePlaybackCreature"] = None,
            *args
    ):
        super().__init__(*args)

        self.surface = pygame.image.frombytes(self.db_instance.image)
        self.rect = self.surface.get_rect()
        self.rect.x = position.x
        self.rect.y = position.y

        self.world = world
        self.screen = self.world.screen
        self.logger = BaseLogger(f"{self.world.object_id}.{self.object_id}_{self.logger_postfix}")
        self.parents = parents

        if last_child:
            self.save_to_db()

        # такая ситуация подразумевается только при генерации мира
        if storage is None and len(self.world.creatures) == 0:
            start_resources = [
                (CARBON, 100, 50),
                (OXYGEN, 100, 50),
                (HYDROGEN, 100, 50),
                (ENERGY, 100, 50),
            ]
            storage = BaseCreatureStorage(self, start_resources)
        self.storage = storage

    def __repr__(self):
        return self.object_id

    # потребление|запасание|выбрасывание
    # <формула_количество.формула_количество...>|<формула_количество.формула_количество...>|<формула_количество.формула_количество...>
    # noinspection GrazieInspection
    # O_2.C_2.H_2.light_2|O_1.C_1.H_1.energy_1|O_1.C_1.H_1
    def pack_consumption_formula(self) -> str:
        # сжатая формула
        formula = ""
        for resources in self.consumption_formula:
            formula_part = ""
            for resource, number in resources.items():
                formula_part += f"{resource.formula}_{number}."
            formula_part = formula_part[:-1]
            formula += f"{formula_part}|"
        formula = formula[:-1]
        return formula

    # todo: write it
    def unpack_consumption_formula(self) -> tuple[dict, dict, dict]:
        pass

    def save_to_db(self):
        self.db_instance = self.db_model(
            id = self.id,
            consumption_formula = self.pack_consumption_formula(),
            surface = pygame.image.tobytes(self.surface, settings.IMAGES_STORE_FORMAT),
            world = self.world.db_instance
        )
        self.db_instance.save()

    def release_logs(self):
        super().release_logs()
        self.storage.release_logs()

    @property
    def position(self):
        return Position(self.rect.x, self.rect.y)

    def spawn(self):
        self.world.add_creature(self)

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
        """Симулирует передвижение существа."""

        self.rect.move_ip(x, y)
        models.CreatureMovement(age = self.world.age, creature = self.db_instance, x = x, y = y).save()

    def get_children_resources(self, children_number: int) -> list[list[tuple[BaseResource, int, int]]]:
        children_resources = []
        for i in range(children_number):
            child_resources = []
            for world_resource, stored_resource in self.storage.items():
                child_resource_number = stored_resource.current//(children_number + 1)
                self.storage.remove(world_resource, child_resource_number)
                child_resources.append((world_resource, stored_resource.capacity, child_resource_number))
            children_resources.append(child_resources)

        return children_resources

    def can_reproduce(self) -> bool:
        if self.storage[CARBON].is_full:
            return True
        return False

    def reproduce(self) -> list["BaseSimulationCreature"]:
        """Симулирует размножение существа."""

        children_number = 1
        children = [
            self.__class__(
                Position(self.position.x + 1 + number, self.position.y),
                self.world,
                [self],
                None
            )
            for number in range(children_number)
        ]

        self.move(-1, 0)

        children_resources = self.get_children_resources(children_number)
        for child, child_resources in zip(children, children_resources):
            child.storage = self.storage.__class__(child, child_resources)
            child.storage.creature = child
            child.spawn()

        return children

    def can_consume(self) -> bool:
        can_consume = True
        for resource, number in self.consumption_formula[0].items():
            can_consume = can_consume and self.world.check_resource(self.position, resource, number)
        for resource, number in self.consumption_formula[1].items():
            can_consume = can_consume and self.storage.can_store(resource, number)
        return can_consume

    def consume(self):
        """Симулирует потребление веществ существом."""

        # забирает из мира ресурсы
        for resource, number in self.consumption_formula[0].items():
            self.world.remove_resource(self.position, resource, number)
        # добавляет в свое хранилище
        for resource, number in self.consumption_formula[1].items():
            self.storage.add(resource, number)
        # отдает ресурсы в мир
        for resource, number in self.consumption_formula[2].items():
            self.world.add_resource(self.position, resource, number)

    def collision_interact(self, other: "BaseSimulationCreature"):
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
