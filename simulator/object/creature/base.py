import copy
import math
import random
from typing import TYPE_CHECKING

import pygame

from core import models
from core.position import Position
from core.surface import CreatureSurface
from logger import BaseLogger
from simulator.object import BaseSimulationObject
from simulator.object.creature.bodypart import BaseBodypart, Body, Storage
from simulator.object.creature.genome import BaseGenome
from simulator.physic import BaseCreatureCharacteristics
from simulator.world_resource import BaseWorldResource, ENERGY, Resources


# https://adamj.eu/tech/2021/05/13/python-type-hints-how-to-fix-circular-imports/
if TYPE_CHECKING:
    from simulator.object.world import BaseSimulationWorld


class CollisionException(BaseException):
    pass


class BaseSimulationCreature(BaseSimulationObject, pygame.sprite.Sprite):
    db_model = models.Creature
    origin_surface: CreatureSurface
    # может быть изменено - оно отрисовывается на экране
    surface: CreatureSurface
    rect: pygame.Rect
    counter: int = 0
    genome: BaseGenome
    children_number: int
    consumption_amount: Resources[int]
    bodyparts: list[BaseBodypart]
    storage: Storage
    # todo: привязать к генам
    reproduction_lost_coef = 1.05
    # todo: привязать к генам
    reproduction_reserve_coef = 1.1
    # todo: привязать к генам
    reproduction_energy_lost = 20
    color: list[int]
    alive = True
    # все траты ресурсов в течении тика добавлять сюда
    # (забираются из хранилища, добавляются в returned_resources, а потом (через returned_resources) возвращаются в мир)
    resources_loss_accumulated: Resources[float]
    _resources_loss: Resources[int] | None
    body: Body
    # todo: привязать к генам
    # отношение количества регенерируемых ресурсов и энергии
    energy_regenerate_cost = 1

    # position - центр существа
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
        self.characteristics = BaseCreatureCharacteristics(
            self.bodyparts,
            self.genome.effects,
            self.world.characteristics,
        )
        self.characteristics.creature = self

        self.prepare_surface()
        self.prepare_resources_loss()
        # ресурсы, возвращаемые в мир по окончании тика (только возвращаются в мир)
        self.returned_resources = Resources[int]()

    def prepare_resources_loss(self):
        self.resources_loss_accumulated = Resources[float]()
        self._resources_loss = None

    @property
    def resources_loss(self) -> Resources[int]:
        if self._resources_loss is None:
            resources_loss = self.resources * self.genome.effects.resources_loss_coef + \
                             self.resources_loss_accumulated + self.genome.effects.resources_loss

            resources_loss[ENERGY] = self.genome.effects.resources_loss[ENERGY] + \
                                     self.characteristics.volume * self.genome.effects.metabolism

            self.resources_loss_accumulated = resources_loss - resources_loss.round()
            self._resources_loss = resources_loss.round()
        return copy.copy(self._resources_loss)

    def prepare_surface(self):
        """Подготавливает все, что нужно для отображения существа."""

        width = self.radius * 2
        height = self.radius * 2
        # origin_surface - хранится как эталон, от него делаются вращения и сохраняются в surface
        # не должно изменятся
        self.origin_surface = CreatureSurface.load_from_file(width, height, self.color)
        # может быть изменено - оно отрисовывается на экране
        self.surface = self.origin_surface.copy()
        self.rect = self.surface.get_rect()
        self.rect.x = self.start_x - self.rect.width // 2
        self.rect.y = self.start_y - self.rect.height // 2

    def apply_bodyparts(self):
        """Применяет эффекты частей тела на существо."""

        # находит класс тела
        for bodypart_class in self.genome.effects.bodyparts:
            if issubclass(bodypart_class, Body):
                self.body = bodypart_class(self.genome.effects.size, None)
                break

        # собирается тело
        bodypart_classes = copy.copy(self.genome.effects.bodyparts)
        bodypart_classes.remove(self.body.__class__)
        self.body.construct(bodypart_classes, self)

        # находится хранилище
        for bodypart in self.bodyparts:
            if isinstance(bodypart, Storage):
                self.storage = bodypart
                break

        # собирается хранилище
        for resource, amount in self.genome.effects.resource_storages.items():
            if amount > 0:
                self.storage.add_resource_storage(resource, self.genome.effects.size)

        # задаются емкости хранилищ ресурсов
        for resource, resource_storage in self.storage.items():
            extra_amount = self.extra_storage[resource]
            resource_storage.capacity = self.genome.effects.resource_storages[resource] + extra_amount

    def apply_genes(self):
        """Применяет эффекты генов на существо."""

        self.genome.apply_genes()

        self.children_number = self.genome.effects.children_number
        self.consumption_amount = self.genome.effects.consumption_amount
        self.color = self.genome.effects.color

    @property
    def bodyparts(self) -> list[BaseBodypart]:
        bodyparts = [self.body]
        bodyparts.extend(self.body.all_dependent)
        return bodyparts

    # нужен для работы pygame.sprite.collide_circle
    # todo: изменять размер отрисовываемого существа при изменении объема (уничтожение/восстановление части тела)
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

    def kill(self):
        super().kill()

        return_resources = self.body.destroy()
        self.returned_resources += return_resources

        self.alive = False
        self.stop()
        self.world.remove_creature(self)

    @property
    def position(self) -> Position:
        """Центр существа."""

        if self._position is None:
            self._position = Position(self.rect.x + self.rect.width // 2, self.rect.y + self.rect.height // 2)
        return self._position

    def can_regenerate(self) -> bool:
        return not self.storage[ENERGY].empty

    def regenerate(self):
        # выбирается часть тела для регенерации
        bodypart = self.get_regeneration_bodypart()

        if bodypart is not None:
            regenerating_resources = Resources[int](
                {
                    resource: self.genome.effects.regeneration_amount for resource in self.storage.stored_resources
                }
            )

            for resource in regenerating_resources:
                # делается поправка на количество ресурса в хранилище
                if regenerating_resources[resource] > self.storage.stored_resources[resource]:
                    regenerating_resources[resource] = self.storage.stored_resources[resource]
                # делается поправка на урон части тела
                if regenerating_resources[resource] > bodypart.damage[resource]:
                    regenerating_resources[resource] = bodypart.damage[resource]

            # проверяется доступное количество энергии
            if self.storage.stored_resources[ENERGY] < regenerating_resources[ENERGY] + \
                    regenerating_resources.sum() * self.energy_regenerate_cost:
                reduction_coef = self.storage.stored_resources[ENERGY] / \
                                 (regenerating_resources[ENERGY] +
                                  regenerating_resources.sum() * self.energy_regenerate_cost)
                regenerating_resources = regenerating_resources * reduction_coef
                regenerating_resources.round_ip()

            extra_resources = bodypart.regenerate(regenerating_resources)
            spent_resources = regenerating_resources - extra_resources
            spent_resources[ENERGY] += int(spent_resources.sum() * self.energy_regenerate_cost)
            self.storage.remove_resources(spent_resources)

    def get_regeneration_bodypart(self) -> BaseBodypart | None:
        bodyparts = []
        for bodypart in self.damaged_bodyparts:
            append = False
            for resource, damage_amount in bodypart.damage.items():
                if damage_amount > 0 and not self.storage[resource].empty:
                    append = True
                    break
            if append:
                bodyparts.append(bodypart)

        random.shuffle(bodyparts)
        if len(bodyparts) > 0:
            bodypart = bodyparts[0]
        else:
            bodypart = None
        return bodypart

    @property
    def damaged_bodyparts(self) -> list[BaseBodypart]:
        return [bodypart for bodypart in self.bodyparts if bodypart.damaged]

    def tick(self):
        """Симулирует жизнедеятельность за один тик."""

        if self.can_consume():
            self.consume()
        if self.can_regenerate():
            self.regenerate()
        if self.can_reproduce():
            self.reproduce()

        self.interact_world_borders()
        self.characteristics.update_speed()
        self.characteristics.update_force()
        if self.can_move():
            self.move()
        self.characteristics.update_accumulated_movement()

        self.metabolize()
        self.return_resources()

    def return_resources(self):
        self.storage.remove_resources(self.storage.extra_resources)
        self.returned_resources += self.storage.extra_resources
        self.returned_resources[ENERGY] = 0
        self.world.add_resources(self.position, self.returned_resources)
        self.returned_resources = Resources[int]()

    def interact_world_borders(self):
        """Расчет пересечения границы мира существом."""

        force_x = 0
        force_y = 0

        force_coef = self.characteristics.elasticity * 100
        cross_left = self.position.x - self.radius - self.world.borders.left
        cross_right = self.position.x + self.radius - self.world.borders.right
        cross_top = self.position.y - self.radius - self.world.borders.top
        cross_bottom = self.position.y + self.radius - self.world.borders.bottom

        if cross_left < 0:
            force_x -= cross_left
        if cross_right > 0:
            force_x -= cross_right
        if cross_top < 0:
            force_y -= cross_top
        if cross_bottom > 0:
            force_y -= cross_bottom

        force_x *= force_coef
        force_y *= force_coef

        self.characteristics.force.accumulate(force_x, force_y)

    @property
    def present_bodyparts(self) -> list[BaseBodypart]:
        return [bodypart for bodypart in self.bodyparts if not bodypart.destroyed]

    def get_autophagic_bodypart(self) -> BaseBodypart:
        bodyparts = []
        for bodypart in self.present_bodyparts:
            append = True
            for resource, amount in self.storage.lack_resources.items():
                if amount > 0 >= bodypart.resources[resource]:
                    append = False
                    break
            if append:
                bodyparts.append(bodypart)

        random.shuffle(bodyparts)
        bodypart = bodyparts[0]
        return bodypart

    # https://ru.wikipedia.org/wiki/%D0%90%D1%83%D1%82%D0%BE%D1%84%D0%B0%D0%B3%D0%B8%D1%8F
    # если возвращается отрицательное количество ресурса, значит существу не хватает ресурсов частей тела,
    # чтобы восполнить потерю -> оно должно умереть
    def autophage(self):
        """Существо попытается восполнить недостаток ресурсов в хранилище за счет частей тела."""

        # todo: заменить len(self.storage.lack) > 0, когда уберу ENERGY из Body там (len(self.storage.lack))
        #  будет учитываться еще и ENERGY, дефицит которой должен будет обрабатываться иначе
        while not self.body.destroyed and len(self.storage.lack_resources) > 0:
            bodypart = self.get_autophagic_bodypart()
            damage = self.storage.lack_resources
            for resource, amount in bodypart.remaining_resources.items():
                if amount < damage[resource]:
                    damage[resource] = amount
            extra_resources = bodypart.make_damage(damage)
            # часть тела была уничтожена (доедена)
            if len(extra_resources) > 0:
                self.storage.add_resources(extra_resources)
            # ресурсов части тела хватило, чтобы покрыть дефицит
            else:
                self.storage.add_resources(damage)

    def metabolize(self):
        self.storage.remove_resources(self.resources_loss)
        self.returned_resources += self.resources_loss

        if len(self.storage.lack_resources) > 0:
            self.autophage()

        # todo: заменить len(self.storage.lack) > 0, когда уберу ENERGY из Body там (len(self.storage.lack))
        #  будет учитываться еще и ENERGY, дефицит которой должен будет обрабатываться иначе
        if len(self.storage.lack_resources) > 0 or self.body.destroyed:
            self.kill()

        self._resources_loss = None

    def can_move(self) -> bool:
        return not self.characteristics.movement.less_then(1)

    def move(self):
        """Перемещает существо."""

        self.rect.move_ip(self.characteristics.movement.round().x, self.characteristics.movement.round().y)
        models.CreatureMovement(
            age = self.world.age,
            creature = self.db_instance,
            x = self.characteristics.movement.round().x,
            y = self.characteristics.movement.round().y
        ).save()
        self._position = None

    @property
    def resources(self) -> Resources[int]:
        resources = Resources[int]()
        for bodypart in self.bodyparts:
            resources += bodypart.resources
        return resources

    @property
    def extra_storage(self) -> Resources[int]:
        extra_storage = Resources[int]()
        for bodypart in self.bodyparts:
            extra_storage += bodypart.extra_storage
        return extra_storage

    def get_children_resources(self) -> list[Resources[int]]:
        children_resources = [self.storage.stored_resources // (self.children_number + 1)] * self.children_number
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
        needed_resources = self.resources * self.children_number * self.reproduction_lost_coef * \
                           self.reproduction_reserve_coef
        # todo: убрать self.resources[ENERGY], когда уберу ENERGY из ресурсов Body
        needed_resources[ENERGY] = self.resources[ENERGY] * self.reproduction_lost_coef * \
                                   self.reproduction_reserve_coef + self.reproduction_energy_lost * self.children_number
        needed_resources.round_ip()

        for resource, amount in needed_resources.items():
            if self.storage[resource].current <= amount:
                can_reproduce = False
                break

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

        for child, child_resources in zip(children, self.get_children_resources()):
            child.start()
            self.storage.remove_resources(
                child_resources + {ENERGY: self.reproduction_energy_lost * self.reproduction_lost_coef}
            )
            child.storage.add_resources(child_resources)
            child.characteristics.speed = self.characteristics.speed.copy()

        return children

    def can_consume(self) -> bool:
        can_consume = False
        for resource, amount in self.storage.fullness.items():
            if amount < 1:
                can_consume = True
                break
        return can_consume

    def get_consumption_resource(self) -> BaseWorldResource | None:
        resources = []
        weights = []
        for resource in self.storage:
            if 0 <= self.storage.fullness[resource] < 1 and self.world.get_resources(self.position)[resource] > 0:
                resources.append(resource)
                weights.append(1 - self.storage.fullness[resource].amount)
        if len(resources) > 0:
            resource = random.choices(resources, weights)[0]
        else:
            resource = None
        return resource

    def consume(self):
        """Симулирует потребление веществ существом."""

        resource = self.get_consumption_resource()
        if resource is not None:
            # забирает из мира ресурс
            available_amount = self.world.get_resources(self.position)[resource]
            if available_amount >= self.consumption_amount[resource]:
                consumption_amount = self.consumption_amount[resource]
            else:
                consumption_amount = available_amount
            self.world.remove_resources(self.position, Resources[int]({resource: consumption_amount}))

            # добавляет в свое хранилище
            self.storage.add_resources({resource: consumption_amount})

            # тратит энергию за потребление ресурса
            self.resources_loss_accumulated[ENERGY] += consumption_amount * 0.01

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

    def draw(self):
        """Отрисовывает существо на экране."""

        self.screen.blit(self.surface, self.rect)
