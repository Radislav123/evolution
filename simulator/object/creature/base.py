import math
import random
from typing import TYPE_CHECKING

import pygame

from core import models
from core.physic.base import BaseCreatureCharacteristics
from core.position import Position
from core.surface.base import CreatureSurface
from evolution import settings
from logger import BaseLogger
from player.object.creature.base import BasePlaybackCreature
from simulator.object.base import BaseSimulationObject
from simulator.object.creature.genome.base import BaseGenome
from simulator.object.creature.storage.base import BaseSimulationStorage
from simulator.world_resource.base import BaseWorldResource, CARBON


# https://adamj.eu/tech/2021/05/13/python-type-hints-how-to-fix-circular-imports/
if TYPE_CHECKING:
    from simulator.object.world.base import BaseSimulationWorld


class CollisionException(BaseException):
    pass


class BaseSimulationCreature(BaseSimulationObject, pygame.sprite.Sprite):
    db_model = models.Creature
    draw = BasePlaybackCreature.draw
    # физические характеристики существа
    characteristics: BaseCreatureCharacteristics
    counter: int = 0
    genome: BaseGenome
    children_number: int
    consumption_amount: int

    # position - левый верхний угол существа/спрайта
    def __init__(
            self,
            position: Position,
            world: "BaseSimulationWorld",
            parents: list["BaseSimulationCreature"] | None,
            world_generation: bool = False,
            *args,
            **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.id = int(f"{world.id}{self.__class__.counter}")
        self.__class__.counter += 1

        # origin_surface - хранится как эталон, от него делаются вращения и сохраняются в surface
        # не должно изменятся
        self.origin_surface = CreatureSurface.load_from_file(
            f"{settings.SIMULATION_IMAGES_PATH}/{self.__class__.__name__}.bmp"
        )
        # может быть изменено - оно отрисовывается на экране
        self.surface = self.origin_surface.copy()
        self.rect = self.surface.get_rect()
        self.start_x = position.x
        self.start_y = position.y
        self.rect.x = self.start_x - self.rect.width // 2
        self.rect.y = self.start_y - self.rect.height // 2
        self._position: Position | None = None

        self.world = world
        self.start_tick = self.world.age
        self.stop_tick = self.world.age
        self.screen = self.world.screen
        self.logger = BaseLogger(f"{self.world.object_id}.{self.object_id}")
        self.storage = BaseSimulationStorage()

        # такая ситуация подразумевается только при генерации мира
        if parents is None and world_generation:
            parents = []
        self.parents = parents

        # такая ситуация подразумевается только при генерации мира
        if world_generation:
            genome = BaseGenome(None, world_generation = True)
        else:
            genome = parents[0].genome.get_child_genome(parents)
        self.genome = genome

        self.apply_genes(world_generation)

        # физические характеристики существа
        # todo: переделать отображение картинки в соответствии с размером существа
        radius = self.genome.effects.size // 2
        self.characteristics = BaseCreatureCharacteristics(
            radius,
            self.genome.effects.elasticity,
            self.world.characteristics,
            self.storage
        )

    def apply_genes(self, world_generation: bool):
        self.genome.apply_genes()

        self.children_number = self.genome.effects.children_number
        self.consumption_amount = self.genome.effects.consumption_amount

        for resource in self.genome.effects.consumption_resources:
            current = 0
            capacity = 100
            if world_generation:
                current = capacity // 2
            self.storage.add_stored_resource(resource, current, capacity)

    # нужен для работы pygame.sprite.collide_circle
    @property
    def radius(self):
        return self.characteristics.radius

    def start(self):
        self.world.add_creature(self)
        self.start_tick = self.world.age

        super().start()
        self.storage.start(self)

    def stop(self):
        self.stop_tick = self.world.age
        super().stop()
        self.storage.stop(self)

    def save_to_db(self):
        self.db_instance = self.db_model(
            world = self.world.db_instance,
            start_tick = self.start_tick,
            stop_tick = self.stop_tick,
            start_x = self.start_x,
            start_y = self.start_y
        )
        self.db_instance.save()
        self.origin_surface.save_to_db(self.origin_surface, self.db_instance)

    def release_logs(self):
        super().release_logs()
        self.storage.release_logs()

    @property
    def position(self):
        """Центр существа."""

        if self._position is None:
            self._position = Position(self.rect.x + self.rect.width // 2, self.rect.y + self.rect.height // 2)
        return self._position

    def tick(self):
        """Симулирует жизнедеятельность за один тик."""

        if self.can_consume():
            self.consume()
        if self.can_reproduce():
            self.reproduce([self])

        self.characteristics.update_speed()
        if self.can_move():
            self.move()
        self.characteristics.update_accumulated_movement()
        self.characteristics.update_force()

    def can_move(self):
        return not self.characteristics.movement.less_then(1)

    def move(self):
        """Перемещает существо."""

        self.rect.move_ip(self.characteristics.round_movement.x, self.characteristics.round_movement.y)
        models.CreatureMovement(
            age = self.world.age,
            creature = self.db_instance,
            x = self.characteristics.round_movement.x,
            y = self.characteristics.round_movement.y
        ).save()
        self._position = None

    def get_children_resources(self) -> list[list[tuple[BaseWorldResource, int, int]]]:
        children_resources = []
        given_resources = {}

        for i in range(self.children_number):
            child_resources = []
            for world_resource, stored_resource in self.storage.items():
                child_resource_number = stored_resource.current // (self.children_number + 1)
                if world_resource in given_resources:
                    given_resources[world_resource] += child_resource_number
                else:
                    given_resources[world_resource] = child_resource_number
                child_resources.append((world_resource, stored_resource.capacity, child_resource_number))
            children_resources.append(child_resources)

        for world_resource, number in given_resources.items():
            self.storage.remove(world_resource, number)

        return children_resources

    def get_children_layers(self) -> list[int]:
        # максимально плотная упаковка кругов
        # https://ru.wikipedia.org/wiki/%D0%A3%D0%BF%D0%B0%D0%BA%D0%BE%D0%B2%D0%BA%D0%B0_%D0%BA%D1%80%D1%83%D0%B3%D0%BE%D0%B2
        children_in_layer = 6
        layers = []
        while sum(layers) < self.children_number:
            layers.append(len(layers) * children_in_layer)
        layers = layers[1:-1]
        if sum(layers) != self.children_number:
            layers.append(self.children_number - sum(layers))
        return layers

    def get_children_positions(self) -> list[Position]:
        # чтобы снизить нагрузку, можно изменить сдвиг до 1.2,
        # тогда существо будет появляться рядом и не будут рассчитываться столкновения
        offset_coef = 0.5
        children_positions = []
        children_layers = self.get_children_layers()
        # располагает потомков равномерно по слоям
        for layer_number, children_in_layer in enumerate(children_layers):
            child_sector = math.pi * 2 / children_in_layer
            for number in range(children_in_layer):
                offset_x = int(self.radius * 2 * math.cos(child_sector * number) * offset_coef * (layer_number + 1))
                offset_y = int(self.radius * 2 * math.sin(child_sector * number) * offset_coef * (layer_number + 1))
                children_positions.append(
                    Position(self.position.x + offset_x, self.position.y + offset_y)
                )
        return children_positions

    def can_reproduce(self) -> bool:
        if self.storage[CARBON].almost_full:
            return True
        return False

    @staticmethod
    def reproduce(parents: list["BaseSimulationCreature"]) -> list["BaseSimulationCreature"]:
        """Симулирует размножение существа."""

        parent = parents[0]
        children = [
            parent.__class__(
                position,
                parent.world,
                [parent]
            )
            for position in parent.get_children_positions()
        ]

        children_resources = parent.get_children_resources()
        for child, child_resources in zip(children, children_resources):
            child.start()
            child.characteristics.speed = parent.characteristics.speed.copy()

        return children

    def can_consume(self) -> bool:
        can_consume = True
        if self.storage.most_not_full is None:
            can_consume = False
        return can_consume

    def get_consumption_resource(self) -> BaseWorldResource:
        resources = list(self.storage.fullness.keys())
        weights = list(map(lambda x: 1 - x, self.storage.fullness.values()))
        return random.choices(resources, weights)[0]

    def consume(self):
        """Симулирует потребление веществ существом."""

        resource = self.get_consumption_resource()
        # забирает из мира ресурс
        self.world.remove_resource(self.position, resource, self.consumption_amount)
        # добавляет в свое хранилище
        extra = self.storage.add(resource, self.consumption_amount)
        # возвращает лишнее количество ресурса в мир
        if extra > 0:
            self.world.add_resource(self.position, resource, extra)

    def collision_interact(self, other: "BaseSimulationCreature"):
        force_coef = self.characteristics.elasticity * other.characteristics.elasticity * 100
        centers_distance_x = self.position.x - other.position.x
        centers_distance_y = self.position.y - other.position.y
        centers_distance = math.sqrt(centers_distance_x**2 + centers_distance_y**2)
        # случай, когда центры совпадают
        if centers_distance == 0:
            centers_distance = 0.5
            centers_distance_x = random.random() * 2 - 1
            centers_distance_y = random.random() * 2 - 1
        force = (self.radius + other.radius - centers_distance) * force_coef
        force_x = force / centers_distance * centers_distance_x
        force_y = force / centers_distance * centers_distance_y

        self.characteristics.force.accumulate(force_x, force_y)
        other.characteristics.force.accumulate(-force_x, -force_y)
