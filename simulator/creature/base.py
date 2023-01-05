import copy
import math
import random
from typing import TYPE_CHECKING

import arcade
import imagesize
import pymunk

from core import models
from core.mixin import DatabaseSavableMixin, WorldObjectMixin
from evolution import settings
from simulator.creature.bodypart import BaseBodypart, Body, Storage
from simulator.creature.genome import BaseGenome
from simulator.physic import BaseCreatureCharacteristics
from simulator.world_resource import BaseWorldResource, ENERGY, Resources


# https://adamj.eu/tech/2021/05/13/python-type-hints-how-to-fix-circular-imports/
if TYPE_CHECKING:
    from simulator.world import BaseSimulationWorld


class BaseSimulationCreature(WorldObjectMixin, DatabaseSavableMixin, arcade.Sprite):
    db_model = models.Creature
    counter = 0
    birth_counter = 0
    death_counter = 0
    image_path = f"{settings.SIMULATION_IMAGES_PATH}/BaseCreature.png"
    image_size = imagesize.get(image_path)

    # todo: структурировать код, упорядочить методы классов
    # position - центр существа
    def __init__(
            self,
            world: "BaseSimulationWorld",
            parents: list["BaseSimulationCreature"] | None,
            world_generation: bool = False,
            *args,
            **kwargs
    ):
        try:
            super().__init__(
                self.image_path,
                *args,
                **kwargs
            )
            # такая ситуация подразумевается только при генерации мира
            if parents is None and world_generation:
                parents = []
            # такая ситуация подразумевается только при генерации мира
            if world_generation:
                genome = BaseGenome(None, world_generation = True)
            else:
                # noinspection PyUnresolvedReferences
                genome = parents[0].genome.get_child_genome(parents)

            self.id = int(f"{world.id}{self.__class__.counter}")
            self.__class__.counter += 1

            # общая инициализация
            self.world = world
            self.start_tick = self.world.age
            self.stop_tick = self.world.age
            self.alive = True

            # инициализация генов
            self.parents = parents
            self.genome = genome
            self.children_number: int | None = None
            self.next_children: list[BaseSimulationCreature] | None = None
            # ресурсы, необходимые для воспроизведения всех потомков
            self._reproduction_resources: Resources | None = None
            # todo: привязать к генам
            self.reproduction_lost_coef = 1.05
            # todo: привязать к генам
            self.reproduction_reserve_coef = 1.1
            # todo: привязать к генам
            self.reproduction_energy_lost = 20
            self.consumption_amount: Resources | None = None
            self.apply_genes()

            # инициализация частей тела
            self.body: Body | None = None
            self.storage: Storage | None = None
            self.apply_bodyparts()

            # инициализация физических характеристик
            self.characteristics: BaseCreatureCharacteristics | None = None
            self.physics_body: pymunk.Body | None = None

            # инициализация ресурсов, которые будут тратиться каждый тик
            self._can_metabolize: bool | None = None
            # все траты ресурсов из-за восстановительных процессов и метаболизма в течении тика добавлять сюда
            # (забираются из хранилища, добавляются в returned_resources,
            # а потом (через returned_resources) возвращаются в мир)
            self.resources_loss_accumulated: Resources | None = None
            self._resources_loss: Resources | None = None
            # todo: привязать к генам
            # отношение количества регенерируемых ресурсов и энергии
            self.energy_regenerate_cost = 1
            # ресурсы, возвращаемые в мир по окончании тика (только возвращаются в мир)
            self.returned_resources = Resources()
        except Exception as error:
            error.init_creature = self
            raise error

    def __repr__(self) -> str:
        return self.object_id

    @property
    def reproduction_resources(self) -> Resources:
        if self._reproduction_resources is None:
            self._reproduction_resources = Resources()
            for child in self.next_children:
                self._reproduction_resources += child.resources
            self.reproduction_resources[ENERGY] += int(
                self.reproduction_energy_lost * self.reproduction_lost_coef * self.children_number
            )
        return self._reproduction_resources

    def fertilize(self):
        self.next_children = [self.__class__(self.world, [self]) for _ in range(self.children_number)]

    def prepare_physics(self):
        self.scale = (self.characteristics.radius * 2) / (sum(self.image_size) / 2)
        self.world.physics_engine.add_sprite(
            self,
            mass = self.characteristics.mass,
            # todo: добавить friction (шероховатость поверхности существа) в гены
            friction = 0.5,
            elasticity = self.characteristics.elasticity,
            # сюда передается радиус скругления углов для хитбокса, поэтому его передавать не надо
            # radius = self.characteristics.radius
        )
        self.physics_body = self.world.physics_engine.get_physics_object(self).body

    def update_physics(self):
        self.physics_body.mass = self.characteristics.mass

    def prepare_resources_loss(self):
        self.resources_loss_accumulated = Resources()

    @property
    def resources_loss(self) -> Resources:
        if self._resources_loss is None:
            resources_loss = self.resources * self.genome.effects.resources_loss_coef + \
                             self.resources_loss_accumulated + self.genome.effects.resources_loss

            resources_loss[ENERGY] = self.genome.effects.resources_loss[ENERGY] + \
                                     self.characteristics.volume * self.genome.effects.metabolism

            self.resources_loss_accumulated = resources_loss - resources_loss.round()
            self._resources_loss = resources_loss.round()
        return self._resources_loss

    def apply_bodyparts(self):
        """Применяет эффекты частей тела на существо."""

        # находит класс тела
        for bodypart_class in self.genome.effects.bodyparts:
            if issubclass(bodypart_class, Body):
                self.body = bodypart_class(self.genome.effects.size_coef, None)
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
                self.storage.add_resource_storage(resource, self.genome.effects.size_coef)

        # задаются емкости хранилищ ресурсов
        for resource, resource_storage in self.storage.items():
            extra_amount = self.extra_storage[resource]
            resource_storage.capacity = self.genome.effects.resource_storages[resource] + extra_amount

        for bodypart in self.bodyparts:
            bodypart.constructed = True

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

    def start(self):
        self.__class__.birth_counter += 1
        self.characteristics = BaseCreatureCharacteristics(
            self.bodyparts,
            self.genome.effects,
            self.world.characteristics,
        )
        self.prepare_physics()
        self.prepare_resources_loss()
        self.start_tick = self.world.age
        self.save_to_db()
        # todo: изменить логику оплодотворения после введения полового размножения
        self.fertilize()
        self.world.add_creature(self)

    def stop(self):
        self.stop_tick = self.world.age
        self.save_to_db()

    def save_to_db(self):
        self.db_instance = self.db_model(
            world = self.world.db_instance,
            start_tick = self.start_tick,
            stop_tick = self.stop_tick
        )
        self.db_instance.save()

    def kill(self):
        self.__class__.death_counter += 1
        self.returned_resources += self.body.destroy()

        self.alive = False
        self.stop()
        self.world.remove_creature(self)

    def can_regenerate(self) -> bool:
        return ENERGY in self.storage and not self.storage[ENERGY].empty

    def regenerate(self):
        # выбирается часть тела для регенерации
        bodypart = self.get_regeneration_bodypart()

        if bodypart is not None:
            regenerating_resources = Resources(
                {resource: self.genome.effects.regeneration_amount for resource in self.storage.stored_resources}
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
                    sum(regenerating_resources.values()) * self.energy_regenerate_cost:
                reduction_coef = self.storage.stored_resources[ENERGY] / \
                                 (regenerating_resources[ENERGY] +
                                  sum(regenerating_resources.values()) * self.energy_regenerate_cost)
                regenerating_resources = (regenerating_resources * reduction_coef).round()

            extra_resources = bodypart.regenerate(regenerating_resources)
            spent_resources = regenerating_resources - extra_resources
            spent_resources[ENERGY] += int(sum(spent_resources.values()) * self.energy_regenerate_cost)
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

    def can_metabolize(self) -> bool:
        if self._can_metabolize is None:
            # проверяется, может ли проходить процесс метаболизма с учетом наличия хранилищ ресурсов у существа
            if sum([resource not in self.storage for resource in self.resources]) > 0:
                self._can_metabolize = False
            else:
                self._can_metabolize = True
        return self._can_metabolize

    # noinspection PyMethodOverriding
    def on_update(self, delta_time: float):
        """Симулирует жизнедеятельность за один тик."""

        try:
            # todo: remove if not (math.isnan(self.position[0]) or math.isnan(self.position[1]))...
            if not (math.isnan(self.position[0]) or math.isnan(self.position[1])):
                if self.can_consume():
                    self.consume()
                if self.can_regenerate():
                    self.regenerate()
                if self.can_reproduce():
                    self.reproduce()

                if self.can_metabolize():
                    self.metabolize()
                else:
                    self.kill()

                self.return_resources()

                self.update_physics()
            else:
                # todo: remove print
                print("------------------")
                print(f"{self.world.age}")
                print(self)
                print(self.position)
                print("------------------")
        except Exception as error:
            error.creature = self
            raise error

    def return_resources(self):
        self.returned_resources += self.storage.extra_resources
        self.storage.remove_resources(self.storage.extra_resources)
        self.returned_resources[ENERGY] = 0
        self.world.add_resources(self.position, self.returned_resources)
        self.returned_resources = Resources()

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
                # чтобы проверилось, может ли существо дальше метаболизировать
                self._can_metabolize = None
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

    @property
    def resources(self) -> Resources:
        resources = Resources()
        for bodypart in self.bodyparts:
            resources += bodypart.resources
        return resources

    @property
    def damage(self) -> Resources:
        resources = Resources()
        for bodypart in self.bodyparts:
            resources += bodypart.damage
        return resources

    @property
    def remaining_resources(self) -> Resources:
        resources = Resources()
        for bodypart in self.bodyparts:
            resources += bodypart.remaining_resources
        return resources

    @property
    def extra_storage(self) -> Resources:
        extra_storage = Resources()
        for bodypart in self.bodyparts:
            extra_storage += bodypart.extra_storage
        return extra_storage

    def get_children_sharing_resources(self) -> list[Resources]:
        if self.children_number > 0:
            sharing_resources_map = {}
            for resource in self.storage:
                sharing_resources_map.update(
                    {resource: [1 if resource in child.storage else 0 for child in self.next_children]}
                )

            sharing_resources = []
            for child in self.next_children:
                sharing_resources.append(
                    Resources(
                        {
                            resource: self.storage.stored_resources[resource] // sum(sharing_resources_map[resource])
                            if resource in child.storage else 0 for resource in self.storage
                        }
                    )
                )
        else:
            sharing_resources = []
        return sharing_resources

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

    def get_children_positions(self) -> list[tuple[float, float]]:
        offset_coef = 0.5
        children_positions = []
        children_layers = self.get_children_layers()
        # располагает потомков равномерно по слоям
        for layer_number, children_in_layer in enumerate(children_layers):
            child_sector = math.pi * 2 / children_in_layer
            for number in range(children_in_layer):
                offset_x = self.characteristics.radius * 2 * math.cos(child_sector * number) \
                           * offset_coef * (layer_number + 1)
                offset_y = self.characteristics.radius * 2 * math.sin(child_sector * number) \
                           * offset_coef * (layer_number + 1)

                children_positions.append((self.position[0] + offset_x, self.position[1] + offset_y))
        return children_positions

    def can_reproduce(self) -> bool:
        if self.children_number > 0:
            can_reproduce = True
            for resource, amount in self.reproduction_resources.items():
                if resource not in self.storage or self.storage[resource].current <= amount:
                    can_reproduce = False
                    break
        else:
            can_reproduce = False
        return can_reproduce

    def reproduce(self):
        """Симулирует размножение существа."""

        # трата ресурсов на тела потомков
        self.storage.remove_resources(self.reproduction_resources)

        # подготовка потомков
        try:
            for child, child_resources, child_position in \
                    zip(self.next_children, self.get_children_sharing_resources(), self.get_children_positions()):
                child.position = child_position
                # изымание ресурсов для потомка у родителя
                self.storage.remove_resources(child_resources)
                # передача потомку части ресурсов родителя
                child.storage.add_resources(child_resources)
                child.start()
                # todo: сообщать потомку момент инерции
        except Exception as error:
            # noinspection PyUnboundLocalVariable
            error.child = child
            raise error

        # подготовка новых потомков
        self._reproduction_resources = None
        self.fertilize()

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
                weights.append(1 - self.storage.fullness[resource])
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

            consumption_resources = Resources({resource: consumption_amount})
            self.world.remove_resources(self.position, consumption_resources)

            # добавляет в свое хранилище
            self.storage.add_resources(consumption_resources)

            # тратит энергию за потребление ресурса
            self.resources_loss_accumulated[ENERGY] += consumption_amount * 0.01
