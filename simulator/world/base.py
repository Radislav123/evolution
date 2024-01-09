import copy
import dataclasses
import random
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from typing import Type

import arcade

from core import models
from core.mixin import WorldObjectMixin
from core.physic import WorldCharacteristics
from core.service import EvolutionSpriteList, ObjectDescriptionReader
from evolution import settings
from simulator.creature import Creature
from simulator.creature.action import ActionInterface
from simulator.creature.bodypart import AddToNonExistentStorageException
from simulator.world_resource import ENERGY, RESOURCE_LIST, Resources


Position = tuple[float, float]
CREATURE_START_RESOURCES = Resources({resource: 100 for resource in RESOURCE_LIST})


@dataclasses.dataclass
class WorldDescriptor:
    name: str
    width: int
    height: int
    viscosity: float
    boarders_friction: float
    borders_thickness: int
    resource_density: float
    chunk_width: int
    chunk_height: int
    seed: int
    chunk_share_resources_period: int
    chunk_share_resources_coeff: float


# todo: добавить выбор настроек мира
world_descriptor: WorldDescriptor = ObjectDescriptionReader[WorldDescriptor]().read_folder_to_list(
    settings.WORLD_DESCRIPTIONS_PATH,
    WorldDescriptor
)[0]


class World(WorldObjectMixin):
    db_model = models.World
    db_instance: db_model
    borders: arcade.SpriteList
    physics_engine: arcade.PymunkPhysicsEngine

    # width - минимальное значение ширины экрана - 120
    def __init__(self, window_center: tuple[int, int]) -> None:
        self.seed = world_descriptor.seed
        random.seed(self.seed)

        self._id = None
        self.age = 0
        self.width = world_descriptor.width
        self.height = world_descriptor.height
        # соотносится с центром окна
        self.center = window_center
        self.chunk_width = world_descriptor.chunk_width
        self.chunk_height = world_descriptor.chunk_height
        # количество тиков между перемещениями ресурсов
        self.chunk_share_resources_period = world_descriptor.chunk_share_resources_period
        # коэффициент разницы ресурсов, которые будут перемещены
        self.chunk_share_resources_coeff = world_descriptor.chunk_share_resources_coeff
        self.position_to_chunk_cache: dict[tuple[int, int], WorldChunk] = {}

        # copy.copy(self.creatures) может работать не правильно, так как SpriteList использует внутренний список
        # {creature.object_id: creature}
        self.creatures = EvolutionSpriteList[Creature]()
        self.processing_creatures: defaultdict[int, set[Creature]] = defaultdict(set)
        self.active_creatures: dict[int, Creature] | None = None
        self.characteristics = WorldCharacteristics(
            world_descriptor.viscosity,
            world_descriptor.boarders_friction,
            world_descriptor.borders_thickness,
            world_descriptor.resource_density
        )
        self.prepare_borders()
        self.prepare_physics_engine()
        # список всех чанков мира
        self.chunks = arcade.SpriteList(True)
        self.chunks.extend(chunk for line in WorldChunk.cut_world(self) for chunk in line)
        self.chunk_borders = arcade.shape_list.ShapeElementList()
        for borders in (x for chunk in self.chunks for x in chunk.borders):
            self.chunk_borders.append(borders)

        # все объекты, которые должны сохраняться в БД, должны складываться сюда для ускорения записи в БД
        self.object_to_save_to_db: defaultdict[
            Type[models.EvolutionModel],
            list[models.EvolutionModel]
        ] = defaultdict(list)
        # todo: добавить количество потоков/ядер (max_workers) в настройки
        self.parallel_saver = ThreadPoolExecutor()

    @property
    def id(self) -> int:
        if self._id is None:
            self._id = self.db_model.objects.count()
        return self._id

    def save_to_db(self) -> None:
        self.db_instance = self.db_model(
            id = self.id,
            stop_tick = self.age,
            width = self.width,
            height = self.height,
            center_x = self.center[0],
            center_y = self.center[1],
            chunk_width = self.chunk_width,
            chunk_height = self.chunk_height
        )
        self.db_instance.save()
        self.characteristics.save_to_db(self)

    # левая, правая, нижняя, верхняя
    def get_borders_coordinates(self) -> tuple[int, int, int, int]:
        left_offset = self.width // 2
        right_offset = self.width - left_offset
        bottom_offset = self.height // 2
        top_offset = self.height - bottom_offset
        left = self.center[0] - left_offset
        right = self.center[0] + right_offset
        bottom = self.center[1] - bottom_offset
        top = self.center[1] + top_offset

        return left, right, bottom, top

    def prepare_borders(self) -> None:
        left, right, bottom, top = self.get_borders_coordinates()

        # инициализация спрайтов границ
        color = (200, 200, 200, 255)

        left_border = arcade.SpriteSolidColor(
            self.characteristics.borders_thickness,
            self.height + self.characteristics.borders_thickness * 2,
            color = color
        )
        right_border = copy.deepcopy(left_border)
        bottom_border = arcade.SpriteSolidColor(
            self.width + self.characteristics.borders_thickness * 2,
            self.characteristics.borders_thickness,
            color = color
        )
        top_border = copy.deepcopy(bottom_border)

        # размещение спрайтов границ
        left_border.right = left
        left_border.bottom = bottom - self.characteristics.borders_thickness
        right_border.left = right
        right_border.bottom = bottom - self.characteristics.borders_thickness
        bottom_border.left = left - self.characteristics.borders_thickness
        bottom_border.top = bottom
        top_border.left = left - self.characteristics.borders_thickness
        top_border.bottom = top

        # добавление в список
        self.borders = arcade.SpriteList(use_spatial_hash = True)
        self.borders.append(left_border)
        self.borders.append(right_border)
        self.borders.append(bottom_border)
        self.borders.append(top_border)

    def prepare_physics_engine(self) -> None:
        self.physics_engine = arcade.PymunkPhysicsEngine(damping = 1 - self.characteristics.viscosity)
        self.physics_engine.add_sprite_list(
            self.borders,
            friction = self.characteristics.borders_friction,
            body_type = arcade.PymunkPhysicsEngine.STATIC
        )

    def save_objects_to_db(self) -> None:
        # todo: разделить на создаваемые и обновляемые объекты
        # todo: точно прописать для каждой модели поля, какие должны обновляться, а какие - нет
        for model, objects in self.object_to_save_to_db.items():
            self.parallel_saver.submit(
                model.objects.bulk_create,
                objects,
                # update_conflicts = True,
                # update_fields = model.get_update_fields(),
                # unique_fields = model.unique_fields
            )
        self.object_to_save_to_db.clear()

    def start(self) -> None:
        """Выполняет подготовительные действия при начале симуляции."""

        self.save_to_db()
        self.spawn_start_creature()
        self.save_objects_to_db()

    def stop(self) -> None:
        """Выполняет завершающие действия при окончании симуляции."""

        self.save_to_db()
        for creature in self.creatures:
            creature.stop()
        self.save_objects_to_db()
        self.parallel_saver.shutdown()

    def spawn_start_creature(self) -> None:
        creature = Creature(self, None, True)
        creature.position = self.center
        creature.start()
        creature.storage.add_resources(CREATURE_START_RESOURCES)
        chunk_resources = self.position_to_chunk(creature.position).resources
        chunk_resources -= creature.remaining_resources
        chunk_resources -= creature.storage.current

    def add_creature(self, creature: Creature) -> None:
        """Добавляет существо в мир."""

        self.creatures.append(creature)

    # если существо необходимо убить, то это нужно сделать отдельно (creature.kill)
    def remove_creature(self, creature: Creature) -> None:
        """Убирает существо из мира."""

        self.creatures.remove(creature)
        if creature.action.stop_tick > self.age:
            self.processing_creatures[creature.action.stop_tick].remove(creature)
        self.physics_engine.remove_sprite(creature)

    def on_update(self) -> None:
        try:
            self.active_creatures = self.processing_creatures[self.age]

            for creature in self.creatures:
                creature.update_position_history()

            for creature in self.active_creatures:
                creature.perform()

            for chunk in self.chunks:
                chunk.on_update()

            for creature in self.active_creatures:
                if creature.alive:
                    creature.action = ActionInterface.get_next_action(creature)

            if self.age % self.chunk_share_resources_period == 0:
                self.share_chunk_resources()

            del self.processing_creatures[self.age]
            self.active_creatures = None
            # не передавать delta_time, так как физические расчеты должны быть привязаны не ко времени, а к тикам
            self.physics_engine.step()

            if self.age % 100 == 0:
                self.save_objects_to_db()
            self.age += 1
        except Exception as error:
            error.world = self
            raise error

    def position_to_chunk(self, position: Position) -> "WorldChunk":
        point = (int(position[0]), int(position[1]))
        if point not in self.position_to_chunk_cache:
            self.position_to_chunk_cache[point] = arcade.get_sprites_at_point(point, self.chunks)[0]
        return self.position_to_chunk_cache[point]

    def share_chunk_resources(self) -> None:
        sharing_resources: list[tuple[WorldChunk, WorldChunk, Resources[int]]] = []
        for chunk in self.chunks:
            for neighbor in chunk.neighbors:
                differance = (chunk.resources - neighbor.resources) * self.chunk_share_resources_coeff
                differance.iround()
                sharing_resources.append((neighbor, chunk, differance))

        for neighbor, chunk, differance in sharing_resources:
            chunk.resources -= differance
            neighbor.resources += differance


class WorldChunk(arcade.SpriteSolidColor):
    def __init__(self, left_bottom: tuple[int, int], world: World) -> None:
        self.world = world
        # границы чанков должны задаваться с небольшим наслоением, так как границы не считаются их частью
        # если граница проходит по 400 координате, то 300.(9) принадлежит чанку, а 400 уже - нет
        super().__init__(self.world.chunk_width + 1, self.world.chunk_height + 1, color = (100, 100, 100, 255))
        self.left = left_bottom[0] - 0.5
        self.bottom = left_bottom[1] - 0.5
        # todo: изменить формулу расчета
        self.default_resource_amount = int(
            (self.right - self.left + 1) * (self.top - self.bottom + 1) * self.world.characteristics.resource_density
        )
        self.resources = Resources[int]({x: self.default_resource_amount for x in RESOURCE_LIST})
        self.borders = arcade.shape_list.ShapeElementList()
        self.borders.append(
            arcade.shape_list.create_line_loop(
                [(self.left, self.bottom), (self.left, self.top), (self.right, self.top), (self.right, self.bottom)],
                self.color,
                1.1
            )
        )

        self.remove_resources_requests: dict[Creature, Resources[int]] = {}
        self.add_resources_requests: dict[Creature, Resources[int]] = {}

        self.neighbors: set[WorldChunk] = set()

    def __repr__(self) -> str:
        return f"{self.left, self.bottom, self.right, self.top}"

    def on_update(self, delta_time: float = 1 / 60) -> None:
        # выдача ресурсов существам
        requested_resources = Resources[int].sum(self.remove_resources_requests.values())
        not_enough = set(
            resource for resource, requested_amount in requested_resources.items()
            if requested_amount > self.resources[resource]
        )
        for creature, creature_request in self.remove_resources_requests.items():
            if creature.alive:
                removed_resources = Resources[int](
                    {
                        resource: self.resources[resource] // requested_resources[resource] * amount
                        if resource in not_enough else amount for resource, amount in creature_request.items()
                    }
                )
                try:
                    creature.storage.add_resources(removed_resources)
                except AddToNonExistentStorageException as exception:
                    removed_resources -= exception.resources
                self.resources -= removed_resources

        # получение ресурсов от существ
        self.resources += Resources[int].sum(self.add_resources_requests.values())

        self.resources[ENERGY] = self.default_resource_amount
        self.remove_resources_requests = {}
        self.add_resources_requests = {}

        for resource, amount in self.resources.items():
            if amount < 0:
                raise ValueError(f"Resource amount can not be below zero, but there is {self.resources}.")

    # todo: перенести этот метод в World
    # todo: резать мир на шестиугольники
    # todo: сделать генерацию границ
    @classmethod
    def cut_world(cls, world: World) -> tuple[tuple["WorldChunk", ...], ...]:
        left, right, bottom, top = world.get_borders_coordinates()

        left_bottom = list(world.center)
        while left_bottom[0] > left:
            left_bottom[0] -= world.chunk_width
        while left_bottom[1] > bottom:
            left_bottom[1] -= world.chunk_height

        chunks = tuple(
            tuple(
                cls((left, bottom), world) for bottom in
                range(left_bottom[1] - world.chunk_height, top + world.chunk_height, world.chunk_height)
            ) for left in range(left_bottom[0] - world.chunk_width, right + world.chunk_width, world.chunk_width)
        )

        width = len(chunks)
        height = len(chunks[0])
        for x in range(width):
            for y in range(height):
                if x > 0:
                    chunks[x][y].neighbors.add(chunks[x - 1][y])
                if x < width - 1:
                    chunks[x][y].neighbors.add(chunks[x + 1][y])
                if y > 0:
                    chunks[x][y].neighbors.add(chunks[x][y - 1])
                if y < height - 1:
                    chunks[x][y].neighbors.add(chunks[x][y + 1])

        return chunks
