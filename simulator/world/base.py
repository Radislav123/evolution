import copy
import dataclasses
import random
from collections import defaultdict
from typing import Type

import arcade

from core import models
from core.mixin import WorldObjectMixin
from core.physic import WorldCharacteristics
from core.service import EvolutionSpriteList, ObjectDescriptionReader
from evolution import settings
from simulator.creature import Creature
from simulator.creature.action import ActionInterface
from simulator.world_resource import ENERGY, RESOURCE_LIST, Resources, WorldResource


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
        # чанки мира по линиям
        self.chunks = WorldChunk.cut_world(self)
        # список всех чанков мира
        self.chunk_list = [chunk for line in self.chunks for chunk in line]

        # все объекты, которые должны сохраняться в БД, должны складываться сюда для ускорения записи в БД
        self.object_to_save_to_db: defaultdict[
            Type[models.EvolutionModel],
            list[models.EvolutionModel]
        ] = defaultdict(list)

    def __repr__(self) -> str:
        return f"{self.object_id}"

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
        for model, objects in self.object_to_save_to_db.items():
            model.objects.bulk_create(
                objects,
                update_conflicts = True,
                update_fields = model.get_update_fields(),
                unique_fields = model.unique_fields
            )
        self.object_to_save_to_db = defaultdict(list)

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

    def spawn_start_creature(self) -> None:
        creature = Creature(self, None, True)
        creature.position = self.center
        creature.storage.add_resources(CREATURE_START_RESOURCES)
        creature.start()
        chunk_resources = self.position_to_chunk(creature.position).resources
        chunk_resources -= creature.remaining_resources
        chunk_resources -= creature.storage.stored_resources

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

            for chunk in self.chunk_list:
                chunk.on_update()

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

    def draw(self) -> None:
        self.borders.draw()
        # можно отрисовывать всех существ по отдельности, итерируясь по self.creatures,
        # что позволит переопределить метод draw существа (иначе, переопределение этого метода не влияет на отрисовку)
        self.creatures.draw()

        draw_chunks = False
        if draw_chunks:
            for chunk in self.chunk_list:
                chunk.draw()

    def position_to_chunk(self, position: Position) -> "WorldChunk":
        x = int((position[0] - self.chunks[0][0].left) / self.chunk_width)
        y = int((position[1] - self.chunks[0][0].bottom) / self.chunk_height)
        if x < 0:
            x = 0
        if x > len(self.chunks) - 1:
            x = len(self.chunks) - 1
        if y < 0:
            y = 0
        if y > len(self.chunks[0]) - 1:
            y = len(self.chunks[0]) - 1
        return self.chunks[x][y]


class WorldChunk:
    def __init__(self, left_bottom: tuple[int, int], width: int, height: int, world: World) -> None:
        self.left = left_bottom[0]
        self.right = self.left + width - 1
        self.bottom = left_bottom[1]
        self.top = self.bottom + height - 1
        self.color = (100, 100, 100, 255)
        self.default_resource_amount = int(
            (self.right - self.left + 1) * (self.top - self.bottom + 1) * world.characteristics.resource_density
        )
        self.resources = Resources[int]({x: self.default_resource_amount for x in RESOURCE_LIST})

        self.add_resources_requests: dict[Creature, Resources[int]] = {}
        self.remove_resources_requests: dict[Creature, Resources[int]] = {}

    def __repr__(self) -> str:
        return f"{self.left, self.bottom, self.right, self.top}"

    # todo: добавить выравнивание количества ресурсов относительно соседних чанков
    def on_update(self) -> None:
        # todo: при выдаче ресурсов проверять, живо ли существо
        self.resources[ENERGY] = self.default_resource_amount

    def get_resource(self, resource: WorldResource) -> int:
        return self.resources[resource]

    def add_resource(self, resource: WorldResource, amount: int) -> None:
        self.resources[resource] += amount

    def remove_resource(self, resource: WorldResource, amount: int) -> None:
        self.resources[resource] -= amount
        if self.resources[resource] < 0:
            raise ValueError(f"{resource} in {self} can not be lower than 0, current is {self.resources[resource]}")

    def draw(self) -> None:
        arcade.draw_xywh_rectangle_outline(
            self.left,
            self.bottom,
            self.right - self.left,
            self.top - self.bottom,
            self.color
        )

    @classmethod
    def cut_world(cls, world: World) -> list[list["WorldChunk"]]:
        left, right, bottom, top = world.get_borders_coordinates()
        chunks: list[list[cls]] = []

        left_bottom = list(world.center)
        while left_bottom[0] > left:
            left_bottom[0] -= world.chunk_width
        while left_bottom[1] > bottom:
            left_bottom[1] -= world.chunk_height

        for left in range(left_bottom[0] - world.chunk_width, right + world.chunk_width, world.chunk_width):
            line = len(chunks)
            chunks.append([])
            for bottom in range(left_bottom[1] - world.chunk_height, top + world.chunk_height, world.chunk_height):
                chunks[line].append(cls((left, bottom), world.chunk_width, world.chunk_height, world))

        return chunks
