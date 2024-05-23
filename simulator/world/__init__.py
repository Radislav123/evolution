import dataclasses
import math
import random
from collections import defaultdict
from typing import Any, Sequence, Type

import arcade
import imagesize
from PIL import Image

from core import models
from core.hitbox import CustomHitBoxAlgorithm
from core.mixin import WorldObjectMixin
from core.physic.engine import PhysicsEngine
from core.physic.world import WorldCharacteristics
from core.service import EvolutionSpriteList, ObjectDescriptionReader
from evolution import settings
from simulator.creature import Creature
from simulator.creature.action import ActionInterface
from simulator.creature.bodypart import AddToNonExistentStorageException
from simulator.world_resource import ENERGY, RESOURCE_LIST, Resources


Position = tuple[float, float]
CREATURE_START_RESOURCES = Resources({resource: 100 for resource in RESOURCE_LIST})


class PositionToTileError(Exception):
    def __init__(self, position: tuple[float, float]):
        self.position = position
        super().__init__(f"There are no sprites at {self.position}.")


@dataclasses.dataclass
class WorldDescriptor:
    name: str
    radius: int
    viscosity: float
    border_friction: float
    # толщина границы в плитках
    border_thickness: int
    resource_density: float
    tile_radius: int
    seed: int
    tile_share_resources_period: int
    tile_share_resources_coeff: float


# todo: добавить выбор настроек мира
world_descriptor: WorldDescriptor = ObjectDescriptionReader[WorldDescriptor]().read_folder_to_list(
    settings.WORLD_DESCRIPTIONS_PATH,
    WorldDescriptor
)[0]


class World(WorldObjectMixin):
    db_model = models.World
    db_instance: db_model

    # width - минимальное значение ширины экрана - 120
    def __init__(self, window_center: Position) -> None:
        self.seed = world_descriptor.seed
        random.seed(self.seed)

        self._id = None
        self.age = 0
        self.radius = world_descriptor.radius
        # соотносится с центром окна
        self.center = window_center
        self.tile_radius = world_descriptor.tile_radius
        # количество тиков между перемещениями ресурсов
        self.tile_share_resources_period = world_descriptor.tile_share_resources_period
        # коэффициент разницы ресурсов, которые будут перемещены
        self.tile_share_resources_coeff = world_descriptor.tile_share_resources_coeff

        self.characteristics = WorldCharacteristics(
            world_descriptor.viscosity,
            world_descriptor.border_friction,
            world_descriptor.border_thickness,
            world_descriptor.resource_density
        )
        self.physics_engine = PhysicsEngine(damping = 1 - self.characteristics.viscosity)
        self.position_to_tile_cache: dict[tuple[int, int], WorldTile] = {}

        # copy.copy(self.creatures) может работать не правильно, так как SpriteList использует внутренний список
        # {creature.object_id: creature}
        self.creatures = EvolutionSpriteList[Creature]()
        self.processing_creatures: defaultdict[int, set[Creature]] = defaultdict(set)
        self.active_creatures: dict[int, Creature] | None = None

        # список плиток мира
        self.map_tiles = arcade.SpriteList[WorldTile](True)
        # список плиток границы мира
        self.border_tiles = arcade.SpriteList[BorderWorldTile](True)
        # список всех плиток
        self.all_tiles = arcade.SpriteList[WorldTile | BorderWorldTile](True)
        self.map_tile_borders = arcade.shape_list.ShapeElementList()
        self.cut()
        for tile in self.map_tiles:
            self.map_tile_borders.append(tile.border)

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
            tile_radius = self.tile_radius
        )
        self.db_instance.save()

    def save_objects_to_db(self) -> None:
        # todo: разделить на создаваемые и обновляемые объекты
        # todo: точно прописать для каждой модели поля, какие должны обновляться, а какие - нет
        for model, objects in self.object_to_save_to_db.items():
            model.objects.bulk_create(objects)

        self.object_to_save_to_db.clear()

    def start(self) -> None:
        """Выполняет подготовительные действия при начале симуляции."""

        self.save_to_db()
        self.characteristics.save_to_db(self)
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

        tile_resources_differance = Resources()
        tile_resources_differance.fill_all(0)
        tile_resources_differance += creature.resources + CREATURE_START_RESOURCES

        try:
            tile_resources = self.position_to_tile(position).resources
            for resource, amount in tile_resources.items():
                if amount < tile_resources_differance[resource]:
                    print("Can not spawn creature due to resources lack.")
                    break
            else:
                # ресурсы забираются безотлагательно
                tile_resources -= tile_resources_differance
                creature.position = position
                creature.start()
                creature.storage.add_resources(CREATURE_START_RESOURCES)
        except PositionToTileError:
            print(f"Can not spawn creature due to tile miss at {position}.")

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

            for tile in self.all_tiles:
                tile.on_update()

            if self.age % self.tile_share_resources_period == 0:
                self.share_tile_resources()

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

    def position_to_tile(self, position: Position) -> "WorldTile":
        point = (int(position[0]), int(position[1]))
        if point not in self.position_to_tile_cache:
            try:
                self.position_to_tile_cache[point] = arcade.get_sprites_at_point(point, self.all_tiles)[0]
            except IndexError as error:
                raise PositionToTileError(position) from error
        return self.position_to_tile_cache[point]

    def share_tile_resources(self) -> None:
        sharing_resources: list[tuple[WorldTile, WorldTile, Resources[int]]] = []
        for tile in self.all_tiles:
            for neighbor in tile.neighbors:
                difference = (tile.resources - neighbor.resources) * self.tile_share_resources_coeff
                difference.iround()
                sharing_resources.append((neighbor, tile, difference))

        for neighbor, tile, difference in sharing_resources:
            tile.resources -= difference
            neighbor.resources += difference

    # мир делится на шестиугольники
    # https://www.redblobgames.com/grids/hexagons/
    # todo: переименовать метод
    def cut(self) -> None:
        width = math.sqrt(3) * self.tile_radius
        height = 2 * self.tile_radius
        offsets = (
            (width / 2, height * 3 / 4),
            (width, 0),
            (width / 2, -height * 3 / 4),
            (-width / 2, -height * 3 / 4),
            (-width, 0),
            (-width / 2, height * 3 / 4)
        )
        tiles_in_radius = self.radius // self.tile_radius or 1

        tile_center = list(self.center)
        SimpleWorldTile(tile_center, self).register(True)

        for edge_size in range(1, tiles_in_radius + self.characteristics.border_thickness):
            if edge_size < tiles_in_radius:
                tile_class = SimpleWorldTile
            else:
                tile_class = BorderWorldTile

            tile_center[0] -= width

            for offset_x, offset_y in offsets:
                for _ in range(edge_size):
                    tile_center[0] += offset_x
                    tile_center[1] += offset_y
                    tile_class(tile_center, self).register(True)

        for tile in self.all_tiles:
            for offset_x, offset_y in offsets:
                try:
                    tile.neighbors.add(self.position_to_tile((tile.center_x + offset_x, tile.center_y + offset_y)))
                except PositionToTileError:
                    pass

    # для правильного физического взаимодействия объекты должны быть непрерывными
    @staticmethod
    def map_object_from_matrix(matrix: tuple[tuple[Any, ...], ...]) -> arcade.Sprite:
        # todo: изменить выбор класса при добавлении других типов объектов
        tile_class = BorderWorldTile
        default_image = tile_class.default_texture.image
        width = default_image.width
        height = default_image.height

        width_coeff = len(matrix[0]) + 0.5
        height_coeff = len(matrix) * 3 / 4 + 1 / 4
        image = Image.new("RGBA", (int(width * width_coeff), int(height * height_coeff)))

        for line_index, line in enumerate(matrix):
            for tile_index, tile in enumerate(line):
                if tile:
                    x = int((tile_index + line_index % 2 / 2) * width)
                    y = int((line_index * 3 / 4) * height)
                    image.paste(default_image, (x, y), default_image)

        texture = arcade.Texture(image, hit_box_algorithm = CustomHitBoxAlgorithm())
        sprite = arcade.Sprite(texture)
        sprite.width = (tile_class.default_width - tile_class.overlap_distance) * width_coeff
        sprite.height = (tile_class.default_height - tile_class.overlap_distance) * height_coeff
        sprite.color = tile_class.default_color

        return sprite

    def change_tiles_by_matrix(
            self,
            tile_class: type["WorldTile"],
            reference_tile: "WorldTile",
            matrix: tuple[tuple[Any, ...], ...]
    ) -> None:
        reference_position = reference_tile.position

        for line_index, line in enumerate(matrix):
            for tile_index, tile in enumerate(line):
                if tile:
                    x_offset = (tile_index + line_index % 2 / 2) * tile_class.default_width
                    y_offset = (line_index * 3 / 4) * tile_class.default_height
                    position = (reference_position[0] + x_offset, reference_position[1] + y_offset)

                    old_tile = self.position_to_tile(position)
                    position = old_tile.position
                    old_tile.unregister(True)

                    tile = tile_class(position, self)
                    tile.register(True)


class WorldTile(arcade.Sprite):
    image_path = settings.WORLD_TILE_IMAGE_PATH
    image_size = imagesize.get(image_path)
    default_color: tuple[int, int, int, int]
    default_border_color = (100, 100, 100, 255)
    default_texture = arcade.load_texture(image_path, hit_box_algorithm = arcade.hitbox.algo_detailed)
    overlap_distance = 1.5
    radius = world_descriptor.tile_radius
    default_width = math.sqrt(3) * radius + overlap_distance
    default_height = 2 * radius + overlap_distance

    # границы плиток должны задаваться с небольшим наслоением, так как границы не считаются их частью
    # если граница проходит по 400 координате, то 399.(9) принадлежит плитке, а 400 уже - нет
    def __init__(self, center: Position | Sequence[float | int], world: World) -> None:
        self.world = world
        super().__init__(self.default_texture, center_x = center[0], center_y = center[1])
        self.width = self.default_width
        self.height = self.default_height
        self.border_points = (
            (self.center_x - self.width / 2, self.center_y - self.height / 4),
            (self.center_x - self.width / 2, self.center_y + self.height / 4),
            (self.center_x, self.center_y + self.height / 2),
            (self.center_x + self.width / 2, self.center_y + self.height / 4),
            (self.center_x + self.width / 2, self.center_y - self.height / 4),
            (self.center_x, self.center_y - self.height / 2)
        )
        self.border = arcade.shape_list.create_line_loop(
            self.border_points,
            self.default_border_color,
            self.overlap_distance
        )

        self.default_resource_amount = int(
            self.radius**2 * 3 * math.sqrt(3) / 2 * self.world.characteristics.resource_density
        )
        self.resources = Resources[int]()
        self.resources.fill_all(self.default_resource_amount)
        self.remove_resources_requests: dict[Creature, Resources[int]] = {}
        self.add_resources_requests: dict[Creature, Resources[int]] = {}

        self.neighbors: set[WorldTile] = set()
        self.color = self.default_color

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

    def register(self, map_creation: bool) -> None:
        self.world.all_tiles.append(self)

    def unregister(self, map_creation: bool) -> None:
        self.remove_from_sprite_lists()


class SimpleWorldTile(WorldTile):
    default_color = (255, 255, 255, 255)

    def register(self, map_creation: bool) -> None:
        super().register(map_creation)
        self.world.map_tiles.append(self)
        if not map_creation:
            self.world.map_tile_borders.append(self.border)

    def unregister(self, map_creation: bool) -> None:
        super().unregister(map_creation)
        if not map_creation:
            self.world.map_tile_borders.remove(self.border)


class BorderWorldTile(WorldTile):
    default_color = (200, 200, 200, 255)

    def register(self, map_creation: bool) -> None:
        super().register(map_creation)
        self.world.border_tiles.append(self)
        self.world.physics_engine.add_sprite(
            self,
            friction = self.world.characteristics.border_friction,
            body_type = arcade.PymunkPhysicsEngine.STATIC
        )

    def unregister(self, map_creation: bool) -> None:
        super().unregister(map_creation)
        self.world.physics_engine.remove_sprite(self)
