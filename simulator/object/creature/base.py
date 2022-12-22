import math
import random
from typing import TYPE_CHECKING

import pygame

from core import models
from core.physic.base import BaseCreatureCharacteristics
from core.position import Position
from core.surface.base import CreatureSurface
from logger import BaseLogger
from player.object.creature.base import BasePlaybackCreature
from simulator.object.base import BaseSimulationObject
from simulator.object.creature.bodypart.base import BaseBodypart
from simulator.object.creature.bodypart.storage import Storage
from simulator.object.creature.genome.base import BaseGenome
from simulator.world_resource.base import BaseWorldResource, ENERGY


# https://adamj.eu/tech/2021/05/13/python-type-hints-how-to-fix-circular-imports/
if TYPE_CHECKING:
    from simulator.object.world.base import BaseSimulationWorld


class CollisionException(BaseException):
    pass


class BaseSimulationCreature(BaseSimulationObject, pygame.sprite.Sprite):
    db_model = models.Creature
    draw = BasePlaybackCreature.draw
    origin_surface: CreatureSurface
    # может быть изменено - оно отрисовывается на экране
    surface: CreatureSurface
    rect: pygame.Rect
    counter: int = 0
    genome: BaseGenome
    children_number: int
    consumption_amount: int
    bodyparts: list[BaseBodypart]
    storage: Storage
    # todo: reproduction_lost_coef - перенести в гены
    reproduction_lost_coef = 1.05
    # todo: reproduction_reserve_coef - перенести в гены
    reproduction_reserve_coef = 1.1
    # todo: reproduction_energy_lost - перенести в гены
    reproduction_energy_lost = 20

    # position - центр существа/спрайта
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

        self.start_x = position.x
        self.start_y = position.y
        self._position: Position | None = None

        self.world = world
        self.start_tick = self.world.age
        self.stop_tick = self.world.age
        self.screen = self.world.screen
        self.logger = BaseLogger(f"{self.world.object_id}.{self.object_id}")

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

        self.apply_genes()
        self.apply_bodyparts()

        # физические характеристики существа
        # todo: переделать отображение картинки в соответствии с размером существа
        self.characteristics = BaseCreatureCharacteristics(
            self.bodyparts,
            self.genome.effects,
            self.world.characteristics,
        )
        self.characteristics.creature = self

        self.prepare_surface()

    def prepare_surface(self):
        """Подготавливает все, что нужно для отображения существа."""

        width = self.radius * 2
        height = self.radius * 2
        # origin_surface - хранится как эталон, от него делаются вращения и сохраняются в surface
        # не должно изменятся
        self.origin_surface = CreatureSurface.load_from_file(width, height)
        # может быть изменено - оно отрисовывается на экране
        self.surface = self.origin_surface.copy()
        self.rect = self.surface.get_rect()
        self.rect.x = self.start_x - self.rect.width // 2
        self.rect.y = self.start_y - self.rect.height // 2

    def apply_bodyparts(self):
        """Применяет эффекты частей тела на существо."""

        self.bodyparts = []
        for bodypart in [bodypart(self.genome.effects.size) for bodypart in self.genome.effects.bodyparts]:
            self.bodyparts.append(bodypart)
            if isinstance(bodypart, Storage):
                self.storage = bodypart
        for resource, capacity in self.genome.effects.resource_storages.items():
            self.storage.add_resource_storage(resource, self.genome.effects.size)
            self.bodyparts.append(self.storage[resource])

        for resource, resource_storage in self.storage.items():
            extra_amount = 0
            if resource in self.extra_storage:
                extra_amount = self.extra_storage[resource]
            resource_storage.capacity = self.genome.effects.resource_storages[resource] + extra_amount

    def apply_genes(self):
        """Применяет эффекты генов на существо."""

        self.genome.apply_genes()

        self.children_number = self.genome.effects.children_number
        self.consumption_amount = self.genome.effects.consumption_amount

    # нужен для работы pygame.sprite.collide_circle
    @property
    def radius(self) -> int:
        return self.characteristics.radius

    def start(self):
        self.world.add_creature(self)
        self.start_tick = self.world.age
        super().start()

    def stop(self):
        self.stop_tick = self.world.age
        super().stop()

    def save_to_db(self):
        self.db_instance = self.db_model(
            world = self.world.db_instance,
            start_tick = self.start_tick,
            stop_tick = self.stop_tick,
            start_x = self.start_x,
            start_y = self.start_y
        )
        self.db_instance.save()

    def release_logs(self):
        super().release_logs()

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
            self.reproduce()

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

    @property
    def resources(self) -> dict[BaseWorldResource, int]:
        resources = {}
        for bodypart in self.bodyparts:
            for resource, amount in bodypart.resources.items():
                if resource not in resources:
                    resources[resource] = amount
                else:
                    resources[resource] += amount
        return resources

    @property
    def extra_storage(self) -> dict[BaseWorldResource, int]:
        extra_storage = {}
        for bodypart in self.bodyparts:
            for resource, amount in bodypart.extra_storage.items():
                if resource not in extra_storage:
                    extra_storage[resource] = amount
                else:
                    extra_storage[resource] += amount
        return extra_storage

    def get_children_resources(self) -> list[list[tuple[BaseWorldResource, int, int]]]:
        children_resources = []
        given_resources = {}

        for i in range(self.children_number):
            child_resources = []
            for world_resource, resource_storage in self.storage.items():
                child_resource_amount = resource_storage.current // (self.children_number + 1)
                if world_resource in given_resources:
                    given_resources[world_resource] += child_resource_amount
                else:
                    given_resources[world_resource] = child_resource_amount
                child_resources.append((world_resource, resource_storage.capacity, child_resource_amount))
            children_resources.append(child_resources)

        for world_resource, amount in given_resources.items():
            self.storage.remove(world_resource, amount)

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
        can_reproduce = True
        for resource, amount in self.resources.items():
            if self.storage[resource].current < \
                    int(amount * self.children_number * self.reproduction_lost_coef * self.reproduction_reserve_coef):
                can_reproduce = False
                break
        if self.storage[ENERGY].current < \
                int(self.reproduction_energy_lost * self.reproduction_lost_coef * self.reproduction_reserve_coef):
            can_reproduce = False

        return can_reproduce

    def reproduce(self) -> list["BaseSimulationCreature"]:
        """Симулирует размножение существа."""

        children = [
            self.__class__(
                position,
                self.world,
                [self]
            )
            for position in self.get_children_positions()
        ]

        resources_lost = {ENERGY: int(self.reproduction_energy_lost * self.reproduction_lost_coef)}
        for child in children:
            for resource, amount in child.resources.items():
                if resource not in resources_lost:
                    resources_lost[resource] = amount
                else:
                    resources_lost[resource] += amount

        for resource, amount in resources_lost.items():
            self.storage.remove(resource, int(amount * self.reproduction_lost_coef))

        children_resources = self.get_children_resources()
        for child, child_resources in zip(children, children_resources):
            child.start()
            child.characteristics.speed = self.characteristics.speed.copy()

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
            self.storage.remove(resource, extra)
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
