import math
from typing import TYPE_CHECKING
from simulator.object.creature.genome.chromosome.gene.base import ChildrenNumberGene
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
from simulator.world_resource.base import BaseResource, CARBON, ENERGY, HYDROGEN, LIGHT, OXYGEN


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

    # position - левый верхний угол существа/спрайта
    def __init__(
            self,
            position: Position,
            world: "BaseSimulationWorld",
            parents: list["BaseSimulationCreature"] | None,
            genome: BaseGenome | None,
            storage: BaseSimulationStorage | None,
            world_generation: bool = False,
            *args,
            **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.id = int(f"{world.id}{self.__class__.counter}")
        self.__class__.counter += 1

        # ((consume, _storage, throw), (consume, _storage, throw), ...)
        self.consumption_formula = (
            {OXYGEN: 20, CARBON: 20, HYDROGEN: 20, LIGHT: 20},
            {OXYGEN: 10, CARBON: 10, HYDROGEN: 10, ENERGY: 10},
            {OXYGEN: 10, CARBON: 10, HYDROGEN: 10}
        )

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

        # такая ситуация подразумевается только при генерации мира
        if parents is None and world_generation:
            parents = []
        self.parents = parents

        # такая ситуация подразумевается только при генерации мира
        if genome is None and world_generation:
            genome = BaseGenome(self, None, world_generation = True)
        self.genome = genome

        # такая ситуация подразумевается только при генерации мира
        if storage is None and world_generation:
            start_resources = [
                (CARBON, 1000, 500),
                (OXYGEN, 1000, 500),
                (HYDROGEN, 1000, 500),
                (ENERGY, 1000, 500),
            ]
            storage = BaseSimulationStorage(self, start_resources)
        self.storage = storage

    def __repr__(self):
        return self.object_id

    @property
    def radius(self):
        return self.characteristics.radius

    def start(self):
        self.world.add_creature(self)
        self.start_tick = self.world.age

        # физические характеристики существа
        radius = (self.rect.width + self.rect.height) / 4
        self.characteristics = BaseCreatureCharacteristics(radius, 5, self.world.characteristics, self.storage)

        super().start()

        self.genome.apply_genes()
        self.storage.start()

    def stop(self):
        self.stop_tick = self.world.age
        super().stop()
        self.storage.stop()

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

    def save_to_db(self):
        self.db_instance = self.db_model(
            id = self.id,
            consumption_formula = self.pack_consumption_formula(),
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

    @property
    def children_number(self):
        return self.genome.get_genes(ChildrenNumberGene)[0].children_number

    def get_children_resources(self) -> list[list[tuple[BaseResource, int, int]]]:
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
        offset_coef = 1.2
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
        if self.storage[CARBON].is_full:
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
                [parent],
                parent.genome.get_child_genome([parent]),
                None
            )
            for position in parent.get_children_positions()
        ]

        children_resources = parent.get_children_resources()
        for child, child_resources in zip(children, children_resources):
            child.storage = parent.storage.__class__(child, child_resources)
            child.storage.creature = child
            child.genome.creature = child
            child.start()
            child.characteristics.speed = parent.characteristics.speed.copy()

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
        force_coef = self.characteristics.elasticity * other.characteristics.elasticity
        force = (self.radius + other.radius) * 2
        # x и y не перепутаны
        if self.position.y != other.position.y:
            force_x = force * force_coef / (self.position.y - other.position.y)
        else:
            force_x = force * force_coef * 2
        if self.position.x != other.position.x:
            force_y = force * force_coef / (self.position.x - other.position.x)
        else:
            force_y = force * force_coef * 2

        self.characteristics.force.accumulate(-force_x, -force_y)
        other.characteristics.force.accumulate(force_x, force_y)
