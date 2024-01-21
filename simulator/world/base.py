import dataclasses
import math
import random
from collections import defaultdict
from typing import Type

import arcade
import imagesize

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


class PositionToChunkError(Exception):
    def __init__(self, position: tuple[float, float]):
        self.position = position
        super().__init__(f"There are no sprites at {self.position}.")


@dataclasses.dataclass
class WorldDescriptor:
    name: str
    radius: int
    viscosity: float
    border_friction: float
    # толщина границы в чанках
    border_thickness: int
    resource_density: float
    chunk_radius: int
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
    physics_engine: arcade.PymunkPhysicsEngine

    # width - минимальное значение ширины экрана - 120
    def __init__(self, window_center: tuple[int, int]) -> None:
        self.seed = world_descriptor.seed
        random.seed(self.seed)

        self._id = None
        self.age = 0
        self.radius = world_descriptor.radius
        # соотносится с центром окна
        self.center = window_center
        self.chunk_radius = world_descriptor.chunk_radius
        # количество тиков между перемещениями ресурсов
        self.chunk_share_resources_period = world_descriptor.chunk_share_resources_period
        # коэффициент разницы ресурсов, которые будут перемещены
        self.chunk_share_resources_coeff = world_descriptor.chunk_share_resources_coeff

        # copy.copy(self.creatures) может работать не правильно, так как SpriteList использует внутренний список
        # {creature.object_id: creature}
        self.creatures = EvolutionSpriteList[Creature]()
        self.processing_creatures: defaultdict[int, set[Creature]] = defaultdict(set)
        self.active_creatures: dict[int, Creature] | None = None
        self.characteristics = WorldCharacteristics(
            world_descriptor.viscosity,
            world_descriptor.border_friction,
            world_descriptor.border_thickness,
            world_descriptor.resource_density
        )

        # список чанков мира
        self.chunks = arcade.SpriteList[WorldChunk](True)
        # список чанков границы мира
        self.border_chunks = arcade.SpriteList[WorldBorderChunk](True)
        # список всех чанков
        self.all_chunks = arcade.SpriteList[WorldChunk | WorldBorderChunk](True)
        self.position_to_chunk_cache: dict[tuple[int, int], WorldChunk] = {}
        self.cut()
        self.chunk_borders = arcade.shape_list.ShapeElementList()
        for borders in (x for chunk in self.chunks for x in chunk.borders):
            self.chunk_borders.append(borders)

        self.prepare_physics()

        # все объекты, которые должны сохраняться в БД, должны складываться сюда для ускорения записи в БД
        self.object_to_save_to_db: defaultdict[
            Type[models.EvolutionModel],
            list[models.EvolutionModel]
        ] = defaultdict(list)

    @property
    def id(self) -> int:
        if self._id is None:
            self._id = self.db_model.objects.count()
        return self._id

    def save_to_db(self) -> None:
        self.db_instance = self.db_model(
            id = self.id,
            stop_tick = self.age,
            radius = self.radius,
            center_x = self.center[0],
            center_y = self.center[1],
            chunk_radius = self.chunk_radius
        )
        self.db_instance.save()
        self.characteristics.save_to_db(self)

    def prepare_physics(self) -> None:
        self.physics_engine = arcade.PymunkPhysicsEngine(damping = 1 - self.characteristics.viscosity)
        self.physics_engine.add_sprite_list(
            self.border_chunks,
            friction = self.characteristics.border_friction,
            body_type = arcade.PymunkPhysicsEngine.STATIC
        )

    def save_objects_to_db(self) -> None:
        # todo: разделить на создаваемые и обновляемые объекты
        # todo: точно прописать для каждой модели поля, какие должны обновляться, а какие - нет
        for model, objects in self.object_to_save_to_db.items():
            model.objects.bulk_create(objects)

        self.object_to_save_to_db.clear()

    def start(self) -> None:
        """Выполняет подготовительные действия при начале симуляции."""

        self.save_to_db()
        self.spawn_start_creature(self.center)
        self.save_objects_to_db()

    def stop(self) -> None:
        """Выполняет завершающие действия при окончании симуляции."""

        self.save_to_db()
        for creature in self.creatures:
            creature.stop()
        self.save_objects_to_db()

    def spawn_start_creature(self, position: Position) -> None:
        creature = Creature(self, None, True)

        chunk_resources_differance = Resources()
        chunk_resources_differance.fill_all(0)
        chunk_resources_differance += creature.resources + CREATURE_START_RESOURCES

        try:
            chunk_resources = self.position_to_chunk(position).resources
            for resource, amount in chunk_resources.items():
                if amount < chunk_resources_differance[resource]:
                    print("Can not spawn creature due to resources lack.")
                    break
            else:
                # ресурсы забираются безотлагательно
                chunk_resources -= chunk_resources_differance
                creature.position = position
                creature.start()
                creature.storage.add_resources(CREATURE_START_RESOURCES)
        except PositionToChunkError:
            print(f"Can not spawn creature due to chunk miss at {position}.")

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

            for chunk in self.all_chunks:
                chunk.on_update()

            if self.age % self.chunk_share_resources_period == 0:
                self.share_chunk_resources()

            for creature in self.active_creatures:
                if creature.alive:
                    creature.action = ActionInterface.get_next_action(creature)

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
            try:
                self.position_to_chunk_cache[point] = arcade.get_sprites_at_point(point, self.all_chunks)[0]
            except IndexError as error:
                raise PositionToChunkError(position) from error
        return self.position_to_chunk_cache[point]

    def share_chunk_resources(self) -> None:
        sharing_resources: list[tuple[WorldChunk, WorldChunk, Resources[int]]] = []
        for chunk in self.all_chunks:
            for neighbor in chunk.neighbors:
                differance = (chunk.resources - neighbor.resources) * self.chunk_share_resources_coeff
                differance.iround()
                sharing_resources.append((neighbor, chunk, differance))

        for neighbor, chunk, differance in sharing_resources:
            chunk.resources -= differance
            neighbor.resources += differance

    # мир делится на шестиугольники
    # https://www.redblobgames.com/grids/hexagons/
    def cut(self) -> None:
        width = math.sqrt(3) * self.chunk_radius
        height = 2 * self.chunk_radius
        offsets = (
            (width / 2, height * 3 / 4),
            (width, 0),
            (width / 2, -height * 3 / 4),
            (-width / 2, -height * 3 / 4),
            (-width, 0),
            (-width / 2, height * 3 / 4)
        )
        chunks_in_radius = self.radius // self.chunk_radius

        chunk_center = list(self.center)
        self.chunks.append(WorldChunk(chunk_center, self))

        for edge_size in range(1, chunks_in_radius + self.characteristics.border_thickness):
            if edge_size < chunks_in_radius:
                chunks_list = self.chunks
                chunk_class = WorldChunk
            else:
                chunks_list = self.border_chunks
                chunk_class = WorldBorderChunk

            chunk_center[0] -= width

            for offset_x, offset_y in offsets:
                for _ in range(edge_size):
                    chunk_center[0] += offset_x
                    chunk_center[1] += offset_y
                    chunks_list.append(chunk_class(chunk_center, self))

        self.all_chunks.extend(self.chunks)
        self.all_chunks.extend(self.border_chunks)

        for chunk in self.all_chunks:
            for offset_x, offset_y in offsets:
                try:
                    chunk.neighbors.add(self.position_to_chunk((chunk.center_x + offset_x, chunk.center_y + offset_y)))
                except PositionToChunkError:
                    pass


class WorldChunk(arcade.Sprite):
    image_path = settings.WORLD_CHUNK_IMAGE_PATH
    image_size = imagesize.get(image_path)
    default_texture = arcade.load_texture(image_path, hit_box_algorithm = arcade.hitbox.algo_detailed)

    # границы чанков должны задаваться с небольшим наслоением, так как границы не считаются их частью
    # если граница проходит по 400 координате, то 399.(9) принадлежит чанку, а 400 уже - нет
    def __init__(self, center: list[int, int], world: World) -> None:
        self.world = world
        self.radius = self.world.chunk_radius
        super().__init__(self.default_texture, center_x = center[0], center_y = center[1])
        self.overlap_distance = 1.5
        self.width = math.sqrt(3) * self.radius + self.overlap_distance
        self.height = 2 * self.radius + self.overlap_distance
        self.borders = arcade.shape_list.ShapeElementList()
        self.border_points = (
            (self.center_x - self.width / 2, self.center_y - self.height / 4),
            (self.center_x - self.width / 2, self.center_y + self.height / 4),
            (self.center_x, self.center_y + self.height / 2),
            (self.center_x + self.width / 2, self.center_y + self.height / 4),
            (self.center_x + self.width / 2, self.center_y - self.height / 4),
            (self.center_x, self.center_y - self.height / 2)
        )
        self.borders.append(
            arcade.shape_list.create_line_loop(self.border_points, (100, 100, 100, 255), self.overlap_distance)
        )

        self.default_resource_amount = int(
            self.radius**2 * 3 * math.sqrt(3) / 2 * self.world.characteristics.resource_density
        )
        self.resources = Resources[int]()
        self.resources.fill_all(self.default_resource_amount)
        self.remove_resources_requests: dict[Creature, Resources[int]] = {}
        self.add_resources_requests: dict[Creature, Resources[int]] = {}

        self.neighbors: set[WorldChunk] = set()

    def __repr__(self) -> str:
        return f"{self.center_x, self.center_y}"

    def on_update(self, delta_time: float = 1 / 60) -> None:
        # выдача ресурсов существам
        requested_resources = Resources[int].sum(self.remove_resources_requests.values())
        not_enough = set(
            resource for resource, requested_amount in requested_resources.items()
            if requested_amount > self.resources[resource]
        )
        for creature, creature_request in self.remove_resources_requests.items():
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


class WorldBorderChunk(WorldChunk):
    default_color = (200, 200, 200, 255)

    def __init__(self, center: list[int, int], world: World) -> None:
        super().__init__(center, world)
        self.color = self.default_color
