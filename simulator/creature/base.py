import copy
import dataclasses
import enum
import math
import random
from typing import TYPE_CHECKING, Union

import arcade
import imagesize
import pymunk

from core import models
from core.mixin import WorldObjectMixin
from core.physic import CreatureCharacteristics
from core.service import ObjectDescriptionReader
from evolution import settings
from simulator.creature.action import ActionInterface
from simulator.creature.bodypart import AddToDestroyedStorageException, BodypartInterface, \
    RemoveFromDestroyedStorageException, StorageInterface
from simulator.creature.genome import Genome
from simulator.world_resource import ENERGY, Resources


# https://adamj.eu/tech/2021/05/13/python-type-hints-how-to-fix-circular-imports/
if TYPE_CHECKING:
    from simulator.world import World
    from simulator.world import WorldChunk


@dataclasses.dataclass
class CreatureDescriptor:
    name: str
    action_duration: int


creature_descriptor = ObjectDescriptionReader[CreatureDescriptor]().read_folder_to_list(
    settings.CREATURE_DESCRIPTIONS_PATH,
    CreatureDescriptor
)[0]


class Creature(WorldObjectMixin, arcade.Sprite):
    class DeathCause(enum.Enum):
        AGE = 0
        CAN_NOT_METABOLISE = 1
        AUTOPHAGE_BODY = 2
        AUTOPHAGE_STORAGE = 3

    db_model = models.Creature
    position_history_db_model = models.CreaturePositionHistory
    db_instance: db_model
    counter = 0
    birth_counter = 0
    death_counter = 0
    image_path = settings.CREATURE_IMAGE_PATH
    image_size = imagesize.get(image_path)
    genome: Genome

    # position - центр существа
    def __init__(
            self,
            world: "World",
            parents: list["Creature"] | None,
            world_generation: bool = False
    ) -> None:
        try:
            super().__init__(self.image_path)
            self.__class__.counter += 1
            # такая ситуация подразумевается только при генерации мира
            if parents is None and world_generation:
                parents = []
            # такая ситуация подразумевается только при генерации мира
            if world_generation:
                genome = Genome.get_first_genome()
            else:
                genome = parents[0].genome.get_child_genome(parents)

            # общая инициализация
            self.world = world
            self.chunk: Union["WorldChunk", None] = None
            # None == существо не стартовало (start()) в симуляции
            self.start_tick = None
            # None == существо не остановлено (stop()) в симуляции
            self.stop_tick = None
            # None == существо не умирало (kill()) в симуляции
            self.death_tick = None
            self.death_cause: Creature.DeathCause | None = None
            self.alive = True
            self.action: ActionInterface | None = None

            # инициализация генов
            self.parents = parents
            self.genome = genome
            # список потомков, которые появятся при следующем размножении
            self.next_children: list[Creature] | None = None
            self._reproduction_resources: Resources | None = None
            # todo: привязать к генам
            # коэффициент ресурсов, теряемых, при воспроизведении потомков
            self.reproduction_lost_coeff = 0.1
            # todo: привязать к генам
            # коэффициент ресурсов, необходимых для разрешения воспроизведения (не расходуются)
            self.reproduction_reserve_coeff = 1.5
            # todo: привязать к генам
            # количество энергии, затрачиваемой на каждого потомка, при воспроизведении
            self.reproduction_energy_lost = 20
            self.genome.apply_genes()
            self.color = self.genome.effects.color

            # инициализация частей тела
            self.bodyparts: set[BodypartInterface] | None = None
            # not_damaged_bodyparts + damaged_bodyparts + destroyed_bodyparts = bodyparts
            # части тела, без урона
            self.not_damaged_bodyparts: set[BodypartInterface] | None = None
            # части тела, получившие урон, но не уничтоженные
            self.damaged_bodyparts: set[BodypartInterface] | None = None
            # полностью уничтоженные части тела
            self.destroyed_bodyparts: set[BodypartInterface] | None = None
            # присутствующие, не уничтоженные полностью, части тела
            self.present_bodyparts: set[BodypartInterface] | None = None
            self.body: BodypartInterface | None = None
            self.storage: StorageInterface | None = None
            self._regenerating_bodypart: BodypartInterface | None = None
            self.apply_bodyparts()
            # ресурсы, необходимые для воспроизводства существа
            self.resources = Resources[int].sum(x.resources for x in self.bodyparts)
            self._damage: Resources[int] | None = None
            self._remaining_resources: Resources[int] | None = None

            # инициализация физических характеристик
            self.characteristics: CreatureCharacteristics | None = None
            self.physics_body: pymunk.Body | None = None

            # инициализация ресурсов, которые будут тратиться каждый тик
            # все траты ресурсов из-за восстановительных процессов и метаболизма в течении тика добавлять сюда
            # (забираются из хранилища, добавляются в returned_resources,
            # а потом (через returned_resources) возвращаются в мир)
            self.resources_loss_accumulated: Resources[float] = Resources[float]()
            self._resources_loss: Resources[int] | None = None
            # todo: привязать к генам
            # отношение количества регенерируемых ресурсов и энергии
            # (сколько энергии стоит регенерация единицы ресурса)
            self.energy_regenerate_cost = 1
            # ресурсы, запрашиваемые из мира, по окончании тика (только заявка на получение ресурсов)
            self.requested_resources = Resources[int]()
            # ресурсы, возвращаемые в мир по окончании тика (только возвращаются в мир, не забираются из хранилища)
            self.returned_resources = Resources[int]()

            # соотносится с models.CreaturePositionHistory
            self.position_history: dict[int, tuple[float, float]] = {}
            # тик, на котором последний раз было движение/перемещение - для сохранения position.history
            self.last_movement_age = -1

            # todo: добавить ген предельного возраста
            # todo: переделать систему возраста - не должно быть прямой смерти из-за превышения лимита
            #  (болезни, увеличение расхода ресурсов, появление шанса умереть...)
            # максимальный возраст
            self.max_age = 1000
        except Exception as error:
            error.init_creature = self
            raise error

    @property
    def reproduction_resources(self) -> Resources[int]:
        """Ресурсы, необходимые для воспроизведения всех потомков, без учета коэффициентов."""

        if self._reproduction_resources is None:
            self._reproduction_resources = Resources[int].sum(child.resources for child in self.next_children)
            self.reproduction_resources[ENERGY] += int(
                self.reproduction_energy_lost * self.genome.effects.children_amount
            )
        return self._reproduction_resources

    @property
    def resources_loss(self) -> Resources[int]:
        if self._resources_loss is None:
            resources_loss = self.resources * self.genome.effects.resources_loss_coeff
            resources_loss[ENERGY] = sum(self.remaining_resources.values()) * self.genome.effects.metabolism
            resources_loss *= self.action.duration
            resources_loss += self.resources_loss_accumulated

            resources_loss_rounded = resources_loss.round()
            self.resources_loss_accumulated = resources_loss - resources_loss_rounded
            self._resources_loss = resources_loss_rounded
        return self._resources_loss

    @property
    def damage(self) -> Resources[int]:
        """Сумма урона всех частей тела существа."""

        if self._damage is None:
            self._damage = Resources[int].sum(x.damage for x in self.bodyparts)
        return self._damage

    @property
    def remaining_resources(self) -> Resources[int]:
        """Ресурсы, которые сейчас находятся в частях тела, как их части."""
        # ресурсы существа, без тех, что хранятся в хранилищах

        if self._remaining_resources is None:
            self._remaining_resources = Resources[int].sum(x.remaining_resources for x in self.bodyparts)
        return self._remaining_resources

    def request_to_save_to_db(self) -> None:
        self.db_instance = self.db_model(
            world = self.world.db_instance,
            start_tick = self.start_tick,
            stop_tick = self.stop_tick,
            death_tick = self.death_tick
        )
        self.world.object_to_save_to_db[self.db_model].append(self.db_instance)

        position_history = [
            self.position_history_db_model(
                creature = self.db_instance,
                age = tick,
                position_x = position[0],
                position_y = position[1]
            ) for tick, position in self.position_history.items()
        ]
        self.world.object_to_save_to_db[self.position_history_db_model].extend(position_history)

    def apply_bodyparts(self) -> None:
        """Собирает тело и применяет эффекты частей тела на существо."""

        # создается тело
        self.body = BodypartInterface.construct_body(self)

        # собираются остальные части тела
        bodypart_names = copy.copy(self.genome.effects.bodyparts)
        bodypart_names.remove(self.body.name)
        self.body.construct(bodypart_names)

        self.bodyparts = set(self.body.all_dependent)
        self.bodyparts.add(self.body)

        # находится хранилище
        self.storage = StorageInterface.find_storage(self.bodyparts)

        # todo: переделать, чтобы хранилища ресурсов были обычными частями тела
        # собирается хранилище
        for resource, amount in self.genome.effects.resource_storages.items():
            if amount > 0:
                self.storage.add_resource_storage(resource)

        # задаются емкости хранилищ ресурсов
        extra_storage = Resources[int].sum(x.extra_storage for x in self.bodyparts)
        for resource, resource_storage in self.storage.items():
            resource_storage.capacity = self.genome.effects.resource_storages[resource] + extra_storage[resource]
        self.bodyparts.update(self.storage.all_dependent)

        for bodypart in self.bodyparts:
            bodypart.constructed = True

        self.not_damaged_bodyparts = {bodypart for bodypart in self.bodyparts}
        self.damaged_bodyparts = set()
        self.destroyed_bodyparts = set()
        self.present_bodyparts = {bodypart for bodypart in self.bodyparts}

    def start(self) -> None:
        self.__class__.birth_counter += 1
        self.characteristics = CreatureCharacteristics(self)
        self.position_history[self.world.age] = self.position
        self.last_movement_age = self.world.age

        self.prepare_physics()
        self.start_tick = self.world.age
        # todo: изменить логику оплодотворения после введения полового размножения
        self.fertilize()
        self.world.add_creature(self)
        self.action = ActionInterface.get_wait_action(self)

    def stop(self) -> None:
        self.stop_tick = self.world.age
        self.request_to_save_to_db()

    # noinspection PyMethodOverriding
    def kill(self, death_cause: DeathCause) -> None:
        self.__class__.death_counter += 1
        self.returned_resources += self.body.destroy()

        self.alive = False
        self.death_cause = death_cause
        self.death_tick = self.world.age
        self.stop()
        self.world.remove_creature(self)

    def prepare_physics(self) -> None:
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

    def fertilize(self) -> None:
        # todo: переделать этот метод при добавлении полового размножения
        self.next_children = [Creature(self.world, [self])
                              for _ in range(self.genome.effects.children_amount)]

    # todo: добавить обработку случаев, когда существо прерывается во время выполнения действия
    #  (возможно, в другом методе)
    def perform(self) -> None:
        """Симулирует жизнедеятельность существа."""

        try:
            self.chunk = self.world.position_to_chunk(self.position)
            match self.action.type:
                case ActionInterface.Type.WAIT:
                    pass
                case ActionInterface.Type.CONSUME:
                    self.consume()
                case ActionInterface.Type.REGENERATE:
                    self.regenerate()
                case ActionInterface.Type.REPRODUCE:
                    self.reproduce()
                case _:
                    raise ValueError("Action is not selected.")

            if self.can_metabolise():
                self.metabolise()
                if self.alive and self.world.age - self.start_tick >= self.max_age:
                    self.kill(self.DeathCause.AGE)
            else:
                self.kill(self.DeathCause.CAN_NOT_METABOLISE)

            self.transfer_resources()
            if self.alive:
                self.update_physics()
            self.chunk = None
        except Exception as error:
            error.creature = self
            error.next_children = self.next_children
            error.parents = self.parents
            raise error

    def update_position_history(self) -> None:
        precision = 0.1
        difference_x = abs(self.position_history[self.last_movement_age][0] - self.position[0])
        difference_y = abs(self.position_history[self.last_movement_age][1] - self.position[1])
        if difference_x > precision and difference_y > precision:
            self.position_history[self.world.age] = self.position
            self.last_movement_age = self.world.age

    def can_consume(self) -> bool:
        can_consume = False
        for resource, amount in self.storage.fullness.items():
            if amount < 1.0 and resource != ENERGY:
                can_consume = True
                break
        return can_consume

    def consume(self) -> None:
        """Симулирует потребление веществ существом."""

        consumption_resources = self.genome.effects.consumption_amount * self.action.duration
        consumption_resources[ENERGY] = 0
        consumption_resource_sum = sum(consumption_resources.values())
        consumption_limit = self.genome.effects.consumption_limit * self.action.duration
        if consumption_resource_sum > consumption_limit:
            reduction_coeff = consumption_limit / consumption_resource_sum
            consumption_resources *= reduction_coeff
        consumption_resources.iround()

        # увеличивает запрос на получение ресурсов из мира
        self.requested_resources += consumption_resources

        # тратит энергию на попытку потребления ресурсов
        self.resources_loss_accumulated[ENERGY] += sum(consumption_resources.values()) * 0.01

    def can_regenerate(self) -> bool:
        return (self.genome.effects.regeneration_amount * self.genome.effects.regeneration_amount_coeff > 0
                and ENERGY in self.storage and not self.storage[ENERGY].empty
                and self.regenerating_bodypart is not None)

    def regenerate(self) -> None:
        regenerating_resource_amount = int(
            self.genome.effects.regeneration_amount * self.genome.effects.regeneration_amount_coeff
            * self.action.duration
        )
        regenerating_resources = Resources[int](
            {resource: min(
                regenerating_resource_amount,
                # делается поправка на количество ресурса в хранилище существа
                self.storage.stored_resources[resource]
            ) for resource in self.regenerating_bodypart.damage}
        )
        energy_cost = (regenerating_resources[ENERGY] + sum(regenerating_resources.values()) *
                       self.energy_regenerate_cost)
        # проверяется доступное количество энергии
        if self.storage.stored_resources[ENERGY] < energy_cost:
            reduction_coeff = self.storage.stored_resources[ENERGY] / energy_cost
            regenerating_resources *= reduction_coeff
            regenerating_resources.iround()

        extra_resources = self.regenerating_bodypart.regenerate(regenerating_resources)
        spent_resources = regenerating_resources - extra_resources
        self.storage.remove_resources(spent_resources)
        # тратит энергию на регенерацию
        self.resources_loss_accumulated[ENERGY] += int(sum(spent_resources.values()) * self.energy_regenerate_cost)

        self._regenerating_bodypart = None

    @property
    def regenerating_bodypart(self) -> BodypartInterface | None:
        if self._regenerating_bodypart is None:
            bodyparts = []
            for bodypart in self.damaged_bodyparts:
                for resource, damage_amount in bodypart.damage.items():
                    if damage_amount > 0 and not self.storage[resource].empty:
                        bodyparts.append(bodypart)
                        break
            else:
                # восстанавливает части тела только если все остальные целы
                for bodypart in self.destroyed_bodyparts:
                    for resource, damage_amount in bodypart.damage.items():
                        if damage_amount > 0 and not self.storage[resource].empty:
                            bodyparts.append(bodypart)
                            break

            if len(bodyparts) > 0:
                random.shuffle(bodyparts)
                self._regenerating_bodypart = bodyparts[0]
            else:
                self._regenerating_bodypart = None
        return self._regenerating_bodypart

    def can_reproduce(self) -> bool:
        if self.genome.effects.children_amount > 0:
            lower_bound_resources = self.reproduction_resources * self.reproduction_reserve_coeff
            lower_bound_resources *= (1 + self.reproduction_lost_coeff)
            lower_bound_resources += self.resources_loss
            for resource, lower_bound in lower_bound_resources.items():
                if (resource not in self.storage or self.storage[resource].current <= lower_bound
                        or self.storage[resource].capacity <= lower_bound):
                    can_reproduce = False
                    break
            else:
                can_reproduce = True
        else:
            can_reproduce = False
        return can_reproduce

    def reproduce(self) -> None:
        """Симулирует размножение существа."""

        # трата ресурсов на воспроизведение тел потомков (попутные потери ресурсов)
        self.resources_loss_accumulated += self.reproduction_resources * self.reproduction_lost_coeff
        # трата ресурсов на тела потомков
        self.storage.remove_resources(self.reproduction_resources)

        try:
            children_sharing_resources = self.get_children_sharing_resources()
            # подготовка потомков
            for child, child_position, child_sharing_resources in \
                    zip(self.next_children, self.get_children_positions(), children_sharing_resources):
                child.position = child_position
                # передача потомку части ресурсов родителя
                child.storage.add_resources(child_sharing_resources)
                child.start()
                # todo: сообщать потомку момент инерции
                # todo: найти форму тела существа для более быстрых расчетов pymunk

            # изымание ресурсов для всех потомков у родителя
            self.storage.remove_resources(Resources[int].sum(children_sharing_resources))
        except Exception as error:
            # noinspection PyUnboundLocalVariable
            error.child = child
            raise error

        # подготовка новых потомков
        self._reproduction_resources = None
        self.fertilize()

    def get_children_positions(self) -> list[tuple[float, float]]:
        offset_coeff = 0.5
        children_positions = []
        children_layers = self.get_children_layers()
        # располагает потомков равномерно по слоям
        for layer_number, children_in_layer in enumerate(children_layers):
            child_sector = math.pi * 2 / children_in_layer
            # сдвиг расположения первого/единственного потомка в слое,
            # чтобы первый/единственный потомок был не строго справа, а случайно на окружности
            first_layer_child_offset = random.random() * math.pi * 2
            for number in range(children_in_layer):
                offset_x = self.characteristics.radius * 2 * \
                           math.cos(child_sector * number + first_layer_child_offset) * \
                           offset_coeff * (layer_number + 1)
                offset_y = self.characteristics.radius * 2 * \
                           math.sin(child_sector * number + first_layer_child_offset) * \
                           offset_coeff * (layer_number + 1)

                children_positions.append((self.position[0] + offset_x, self.position[1] + offset_y))
        return children_positions

    def get_children_layers(self) -> list[int]:
        # максимально плотная упаковка кругов
        # https://ru.wikipedia.org/wiki/%D0%A3%D0%BF%D0%B0%D0%BA%D0%BE%D0%B2%D0%BA%D0%B0_%D0%BA%D1%80%D1%83%D0%B3%D0%BE%D0%B2
        children_in_layer = 6
        layers = []
        while sum(layers) < self.genome.effects.children_amount:
            layers.append(len(layers) * children_in_layer)
        layers = layers[1:-1]
        if sum(layers) != self.genome.effects.children_amount:
            layers.append(self.genome.effects.children_amount - sum(layers))
        return layers

    def get_children_sharing_resources(self) -> list[Resources]:
        if self.genome.effects.children_amount > 0:
            sharing_resources_map = {}
            for resource in self.storage:
                sharing_resources_map.update(
                    {resource: [1 if resource in child.storage else 0 for child in self.next_children]}
                )

            sharing_resources = []
            free_resources = self.storage.stored_resources - self.resources_loss
            for child in self.next_children:
                sharing_resources.append(
                    Resources(
                        {resource: free_resources[resource] // sum(sharing_resources_map[resource], 1)
                        if resource in child.storage else 0 for resource in self.storage}
                    )
                )
        else:
            sharing_resources = []
        return sharing_resources

    def can_metabolise(self) -> bool:
        """
        Проверяет, может ли проходить процесс метаболизма с учетом наличия хранилищ ресурсов у существа
        и достаточности ресурсов существа и хранимых ресурсов.
        """

        missing_storages_amount = sum(
            (resource not in self.storage or self.storage[resource].destroyed) for resource in self.resources
        )
        lacking_resources = self.remaining_resources + self.storage.stored_resources - self.resources_loss
        lacking_resources_count = sum(1 for x in lacking_resources.values() if x < 0)
        if missing_storages_amount > 0 or lacking_resources_count > 0:
            can_metabolize = False
        else:
            can_metabolize = True
        return can_metabolize

    def metabolise(self) -> None:
        # todo: вынести энергетический обмен в отдельный метод при добавлении других способов, кроме фотосинтеза
        self.requested_resources[ENERGY] += int(self.genome.effects.consumption_amount[ENERGY] * self.action.duration)

        lack_resources = Resources[int](
            {resource: amount for resource, amount in
             (self.storage.stored_resources - self.resources_loss).items() if amount < 0}
        )

        if len(lack_resources) > 0:
            lack_resources = self.autophage(lack_resources)
        if len(lack_resources) > 0 or self.body.destroyed:
            self.kill(self.DeathCause.AUTOPHAGE_BODY)
        else:
            try:
                self.returned_resources += self.resources_loss
                self.storage.remove_resources(self.resources_loss)
            except RemoveFromDestroyedStorageException as exception:
                self.returned_resources -= exception.resources
                self.kill(self.DeathCause.AUTOPHAGE_STORAGE)

        self._resources_loss = None

    # https://ru.wikipedia.org/wiki/%D0%90%D1%83%D1%82%D0%BE%D1%84%D0%B0%D0%B3%D0%B8%D1%8F
    def autophage(self, lack_resources: Resources[int]) -> Resources[int]:
        """Существо попытается восполнить недостаток ресурсов в хранилище за счет частей тела."""

        while not self.body.destroyed and len(lack_resources) > 0:
            bodypart = self.get_autophagic_bodypart(lack_resources)
            damage = -lack_resources
            # коррекция урона с учетом наличия ресурсов в части тела
            for resource, amount in damage.items():
                amount_in_bodypart = bodypart.remaining_resources[resource]
                if amount_in_bodypart < amount:
                    damage[resource] = amount_in_bodypart
            damage_extra_resources = bodypart.make_damage(damage)
            resource_increment = damage + damage_extra_resources

            lack_resources += resource_increment
            for resource, amount in lack_resources.items():
                if amount >= 0:
                    lack_resources[resource] = 0
            try:
                self.storage.add_resources(resource_increment)
            # ресурсы, которые не могут быть добавлены в хранилища существа,
            # так как хранилища были уничтожены, будут возвращены в мир
            except AddToDestroyedStorageException as exception:
                self.returned_resources += exception.resources
        return lack_resources

    def get_autophagic_bodypart(self, lack_resources: Resources[int]) -> BodypartInterface:
        bodyparts = []
        for bodypart in self.present_bodyparts:
            for resource, amount in lack_resources.items():
                if amount > 0 and bodypart.remaining_resources[resource] > 0:
                    break
            else:
                bodyparts.append(bodypart)

        random.shuffle(bodyparts)
        return bodyparts[0]

    def transfer_resources(self) -> None:
        """Обмениваем ресурсами с миром."""

        chunk = self.world.position_to_chunk(self.position)

        # запрос на получение ресурсов делается, только если существо живо
        if self.alive:
            chunk.remove_resources_requests[self] = self.requested_resources
            self.requested_resources = Resources[int]()

        # запрос на возвращение ресурсов
        extra_resources = self.storage.extra_resources
        self.returned_resources += extra_resources
        self.storage.remove_resources(extra_resources)
        # энергия не может возвращаться в мир
        self.returned_resources[ENERGY] = 0
        chunk.add_resources_requests[self] = self.returned_resources
        self.returned_resources = Resources[int]()

    def update_physics(self) -> None:
        self.physics_body.mass = self.characteristics.mass
