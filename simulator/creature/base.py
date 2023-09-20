import copy
import dataclasses
import enum
import math
import random
from typing import TYPE_CHECKING

import arcade
import imagesize
import pymunk

from core import models
from core.mixin import WorldObjectMixin
from core.physic import CreatureCharacteristics
from core.service import ObjectDescriptionReader
from evolution import settings
from simulator.creature.action import ActionInterface
from simulator.creature.bodypart import AddToNonExistentStoragesException, BodypartInterface, \
    RemoveFromNonExistentStorageException, StorageInterface
from simulator.creature.genome import Genome
from simulator.world_resource import ENERGY, Resources, WorldResource


# https://adamj.eu/tech/2021/05/13/python-type-hints-how-to-fix-circular-imports/
if TYPE_CHECKING:
    from simulator.world import SimulationWorld


@dataclasses.dataclass
class CreatureDescriptor:
    name: str
    action_duration: int


creature_descriptor = ObjectDescriptionReader[CreatureDescriptor]().read_folder_to_list(
    settings.CREATURE_DESCRIPTIONS_PATH,
    CreatureDescriptor
)[0]


class SimulationCreature(WorldObjectMixin, arcade.Sprite):
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
            world: "SimulationWorld",
            parents: list["SimulationCreature"] | None,
            world_generation: bool = False
    ) -> None:
        try:
            super().__init__(self.image_path)
            # такая ситуация подразумевается только при генерации мира
            if parents is None and world_generation:
                parents = []
            # такая ситуация подразумевается только при генерации мира
            if world_generation:
                genome = Genome.get_first_genome()
            else:
                genome = parents[0].genome.get_child_genome(parents)

            self.id = int(f"{world.id}{self.__class__.counter}")
            self.__class__.counter += 1

            # общая инициализация
            self.world = world
            # None == существо не стартовало (start()) в симуляции
            self.start_tick = None
            # None == существо не остановлено (stop()) в симуляции
            self.stop_tick = None
            # None == существо не умирало (kill()) в симуляции
            self.death_tick = None
            self.death_cause: SimulationCreature.DeathCause | None = None
            self.alive = True
            self.action: ActionInterface | None = None

            # инициализация генов
            self.parents = parents
            self.genome = genome
            # количество потомков, которые появляются при размножении
            self.children_amount: int | None = None
            # список потомков, которые появятся при следующем размножении
            self.next_children: list[SimulationCreature] | None = None
            self._reproduction_resources: Resources | None = None
            # todo: привязать к генам
            # коэффициент ресурсов, теряемых, при воспроизведении потомков
            # (теряется лишь (1 - reproduction_lost_coeff))
            self.reproduction_lost_coeff = 1.1
            # todo: привязать к генам
            # коэффициент ресурсов, необходимых для разрешения воспроизведения (не расходуются)
            self.reproduction_reserve_coeff = 1.5
            # todo: привязать к генам
            # количество энергии, затрачиваемой на каждого потомка, при воспроизведении
            self.reproduction_energy_lost = 20
            # количество определенное ресурса, которое существо может потребить за тик
            self.consumption_amount: Resources[int] | None = None
            # количество всех ресурсов, которое существо может потребить за тик
            self.consumption_limit: int | None = None
            self.apply_genes()

            # инициализация частей тела
            self.body: BodypartInterface | None = None
            self.storage: StorageInterface | None = None
            self._bodyparts: list[BodypartInterface] | None = None
            self.apply_bodyparts()
            # ресурсы, необходимые для воспроизводства существа
            self.resources = Resources.sum(x.resources for x in self.bodyparts)

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
            # (сколько энергии стоит восстановление единицы ресурса)
            self.energy_regenerate_cost = 1
            # ресурсы, возвращаемые в мир по окончании тика (только возвращаются в мир)
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

    def __repr__(self) -> str:
        return self.object_id

    @property
    def reproduction_resources(self) -> Resources[int]:
        """Ресурсы, необходимые для воспроизведения всех потомков, без учета коэффициентов."""

        if self._reproduction_resources is None:
            self._reproduction_resources = Resources.sum(child.resources for child in self.next_children)
            self.reproduction_resources[ENERGY] += int(self.reproduction_energy_lost * self.children_amount)
        return self._reproduction_resources

    @property
    def resources_loss(self) -> Resources[int]:
        if self._resources_loss is None:
            resources_loss = self.resources * self.genome.effects.resources_loss_coeff + \
                             self.resources_loss_accumulated + self.genome.effects.resources_loss

            resources_loss[ENERGY] = self.genome.effects.resources_loss[ENERGY] + \
                                     self.characteristics.volume * self.genome.effects.metabolism

            resources_loss *= self.action.duration
            resources_loss_rounded = resources_loss.round()
            self.resources_loss_accumulated = resources_loss - resources_loss_rounded
            self._resources_loss = resources_loss_rounded
        return self._resources_loss

    @property
    def damage(self) -> Resources[int]:
        return Resources.sum(x.damage for x in self.bodyparts)

    @property
    def remaining_resources(self) -> Resources[int]:
        """Ресурсы, которые сейчас находятся в частях тела, как их части."""
        # ресурсы существа, без тех, что хранятся в хранилищах

        return Resources.sum(x.remaining_resources for x in self.bodyparts)

    @property
    def extra_storage(self) -> Resources[int]:
        return Resources.sum(x.extra_storage for x in self.bodyparts)

    @property
    def bodyparts(self) -> list[BodypartInterface]:
        """Все части тела существа."""

        if self._bodyparts is None:
            self._bodyparts = [self.body]
            self._bodyparts.extend(self.body.all_dependent)
        return self._bodyparts

    @property
    def damaged_bodyparts(self) -> list[BodypartInterface]:
        """Части тела, получившие урон."""

        return [bodypart for bodypart in self.bodyparts if bodypart.damaged]

    @property
    def present_bodyparts(self) -> list[BodypartInterface]:
        """Присутствующие, не уничтоженные полностью, части тела."""

        return [bodypart for bodypart in self.bodyparts if not bodypart.destroyed]

    def save_to_db(self) -> None:
        self.db_instance = self.db_model(
            id = self.id,
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

    def apply_genes(self) -> None:
        """Применяет эффекты генов на существо."""

        self.genome.apply_genes()

        self.children_amount = self.genome.effects.children_amount
        self.consumption_amount = self.genome.effects.consumption_amount
        self.consumption_limit = self.genome.effects.consumption_limit
        self.color = self.genome.effects.color

    def apply_bodyparts(self) -> None:
        """Собирает тело и применяет эффекты частей тела на существо."""

        # создается тело
        self.body = BodypartInterface.construct_body(self)

        # собираются остальные части тела
        bodypart_names = copy.copy(self.genome.effects.bodyparts)
        bodypart_names.remove(self.body.name)
        self.body.construct(bodypart_names)

        # находится хранилище
        self.storage = StorageInterface.find_storage(self.bodyparts)

        # собирается хранилище
        for resource, amount in self.genome.effects.resource_storages.items():
            if amount > 0:
                self.storage.add_resource_storage(resource)

        # задаются емкости хранилищ ресурсов
        for resource, resource_storage in self.storage.items():
            extra_amount = self.extra_storage[resource]
            resource_storage.capacity = self.genome.effects.resource_storages[resource] + extra_amount

        # необходимо, чтобы список частей тела был пересобран, так как только в данной точке исполнения тело,
        # со всеми частями, собрано
        self._bodyparts = None
        for bodypart in self.bodyparts:
            bodypart.constructed = True

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
        self.save_to_db()

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
        self.next_children = [SimulationCreature(self.world, [self]) for _ in range(self.children_amount)]

    # todo: добавить обработку случаев, когда существо прерывается во время выполнения действия
    #  (возможно, в другом методе)
    def perform(self) -> None:
        """Симулирует жизнедеятельность существа."""

        try:
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

            if self.alive:
                self.action = ActionInterface.get_next_action(self)

            self.return_resources()
            if self.alive:
                self.update_physics()
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
            if amount < 0.9:
                can_consume = True
                break
        return can_consume

    def consume(self) -> None:
        """Симулирует потребление веществ существом."""

        chunk_resources = self.world.get_resources(self.position)
        chunk_resources_sum = sum(amount for resource, amount in chunk_resources.items() if not resource.is_energy)
        if chunk_resources_sum > 0:
            consumption_resources = Resources[int](
                {resource: min(
                    int(amount / chunk_resources_sum * self.consumption_limit * self.action.duration),
                    amount
                ) for resource, amount in chunk_resources.items()
                    if not self.storage[resource].destroyed and not resource.is_energy}
            )
            for resource, amount in self.consumption_amount.items():
                real_amount = int(amount * self.action.duration)
                if real_amount < consumption_resources[resource]:
                    consumption_resources[resource] = real_amount

            # забирает ресурсы из мира
            self.world.remove_resources(self.position, consumption_resources)

            # добавляет в свое хранилище
            self.storage.add_resources(consumption_resources)

            # тратит энергию за потребление ресурсов
            self.resources_loss_accumulated[ENERGY] += sum(consumption_resources.values()) * 0.01

    # оставлено, но не используется
    def get_consumption_resource(self) -> WorldResource | None:
        """Выбирает ресурс, который будет потреблен существом."""

        resources = []
        weights = []
        for resource in self.storage:
            if not self.storage[resource].destroyed and self.storage.fullness[resource] < 1 \
                    and self.world.get_resources(self.position)[resource] > 0:
                resources.append(resource)
                weights.append(1 - self.storage.fullness[resource])
        if len(resources) > 0:
            resource = random.choices(resources, weights)[0]
        else:
            resource = None
        return resource

    def can_regenerate(self) -> bool:
        return ENERGY in self.storage and not self.storage[ENERGY].empty and len(self.damaged_bodyparts) > 0

    def regenerate(self) -> None:
        # выбирается часть тела для регенерации
        bodypart = self.get_regeneration_bodypart()

        if bodypart is not None:
            regenerating_resources = Resources(
                {resource: int(self.genome.effects.regeneration_amount * self.action.duration)
                 for resource in self.storage.stored_resources}
            )

            for resource in regenerating_resources:
                # делается поправка на количество ресурса в хранилище
                if regenerating_resources[resource] > self.storage.stored_resources[resource]:
                    regenerating_resources[resource] = self.storage.stored_resources[resource]

            # проверяется доступное количество энергии
            if self.storage.stored_resources[ENERGY] < regenerating_resources[ENERGY] + \
                    sum(regenerating_resources.values()) * self.energy_regenerate_cost:
                reduction_coeff = (self.storage.stored_resources[ENERGY] /
                                   (regenerating_resources[ENERGY] +
                                    sum(regenerating_resources.values()) * self.energy_regenerate_cost))
                regenerating_resources = (regenerating_resources * reduction_coeff).round()

            extra_resources = bodypart.regenerate(regenerating_resources)
            spent_resources = regenerating_resources - extra_resources
            spent_resources[ENERGY] += int(sum(spent_resources.values()) * self.energy_regenerate_cost)
            self.storage.remove_resources(spent_resources)

    def get_regeneration_bodypart(self) -> BodypartInterface | None:
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

    def can_reproduce(self) -> bool:
        if self.children_amount > 0:
            for resource, amount in self.reproduction_resources.items():
                lower_bound = amount * self.reproduction_reserve_coeff * self.reproduction_lost_coeff
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

        # трата ресурсов на тела потомков
        reproduction_spending_resources = (self.reproduction_resources * self.reproduction_lost_coeff).round()
        self.storage.remove_resources(reproduction_spending_resources)
        # ресурсы, возвращаемые в мир
        self.returned_resources += reproduction_spending_resources - self.reproduction_resources

        try:
            # подготовка потомков
            for child, child_position, child_resources in \
                    zip(self.next_children, self.get_children_positions(), self.get_children_sharing_resources()):
                child.position = child_position
                # изымание ресурсов для потомка у родителя
                self.storage.remove_resources(child_resources)
                # передача потомку части ресурсов родителя
                child.storage.add_resources(child_resources)
                child.start()
                # todo: сообщать потомку момент инерции
                # todo: найти форму тела существа для более быстрых расчетов pymunk
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
        while sum(layers) < self.children_amount:
            layers.append(len(layers) * children_in_layer)
        layers = layers[1:-1]
        if sum(layers) != self.children_amount:
            layers.append(self.children_amount - sum(layers))
        return layers

    def get_children_sharing_resources(self) -> list[Resources]:
        if self.children_amount > 0:
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
                            resource: self.storage.stored_resources[resource] // sum(sharing_resources_map[resource], 1)
                            if resource in child.storage else 0 for resource in self.storage
                        }
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
        energy_consumption_amount = min(
            self.world.get_resource(self.position, ENERGY),
            int(self.consumption_amount[ENERGY] * self.action.duration)
        )
        self.storage.add_resource(ENERGY, energy_consumption_amount)
        self.world.remove_resource(self.position, ENERGY, energy_consumption_amount)

        lack_resources = Resources(
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
            except RemoveFromNonExistentStorageException as exception:
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
            for resource, amount in bodypart.remaining_resources.items():
                if amount < damage[resource]:
                    damage[resource] = amount
            damage_extra_resources = bodypart.make_damage(damage)
            resource_increment = damage + damage_extra_resources

            lack_resources += resource_increment
            lack_resources = Resources({resource: amount for resource, amount in lack_resources.items() if amount < 0})
            try:
                self.storage.add_resources(resource_increment)
            # ресурсы, которые не могут быть добавлены в хранилища существа,
            # так как хранилища были уничтожены, будут возвращены в мир
            except AddToNonExistentStoragesException as exception:
                self.returned_resources += exception.resources
        return lack_resources

    def get_autophagic_bodypart(self, lack_resources: Resources[int]) -> BodypartInterface:
        bodyparts = []
        for bodypart in self.present_bodyparts:
            for resource, amount in lack_resources.items():
                if amount > 0 >= bodypart.remaining_resources[resource]:
                    break
            else:
                bodyparts.append(bodypart)

        random.shuffle(bodyparts)
        return bodyparts[0]

    def return_resources(self) -> None:
        """Возвращает ресурсы в мир."""

        self.returned_resources += self.storage.extra_resources
        self.storage.remove_resources(self.storage.extra_resources)
        # энергия не может возвращаться в мир
        self.returned_resources[ENERGY] = 0
        self.world.add_resources(self.position, self.returned_resources)
        self.returned_resources = Resources[int]()

    def update_physics(self) -> None:
        self.physics_body.mass = self.characteristics.mass
