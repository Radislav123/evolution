import copy

import arcade

from core import models
from core.mixin import DatabaseSavableMixin, WorldObjectMixin
from simulator.creature import BaseSimulationCreature
from simulator.physic import BaseWorldCharacteristics
from simulator.world_resource import BaseWorldResource, CARBON, ENERGY, HYDROGEN, OXYGEN, ResourceAmount, Resources


class Switch:
    value: bool

    def __init__(self):
        self.value = False

    def __bool__(self) -> bool:
        return self.value

    def set(self):
        self.value = True

    def reset(self):
        self.value = False


class BaseSimulationWorld(DatabaseSavableMixin, WorldObjectMixin):
    db_model = models.World
    db_instance: models.World
    borders: arcade.SpriteList
    physics_engine: arcade.PymunkPhysicsEngine
    count_map_resources = Switch()
    map_resources: Resources[int] = None
    count_creatures_resources = Switch()
    creatures_resources: Resources[int] = None
    count_world_resources = Switch()
    world_resources: Resources[int] = None

    # width - минимальное значение ширины экрана - 120
    def __init__(self, width: int, height: int, center: tuple[int, int]):
        self._id = None
        self.age = 0
        self.width = width
        self.height = height
        self.center = center
        self.chunk_width = 50
        self.chunk_height = 50

        self.prepare_borders()
        # {creature.object_id: creature}
        self.creatures = arcade.SpriteList()
        self.characteristics = BaseWorldCharacteristics(0.1)
        self.prepare_physics_engine()
        self.chunks = BaseSimulationWorldChunk.cut_world(self)

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

    def prepare_borders(self):
        left, right, bottom, top = self.get_borders_coordinates()

        # инициализация спрайтов границ
        thickness = 100
        color = (0, 0, 0)

        left_border = arcade.SpriteSolidColor(
            thickness,
            self.height + thickness * 2,
            color
        )
        right_border = copy.deepcopy(left_border)
        bottom_border = arcade.SpriteSolidColor(
            self.width + thickness * 2,
            thickness,
            color
        )

        # размещение спрайтов границ
        top_border = copy.deepcopy(bottom_border)
        left_border.right = left
        left_border.bottom = bottom - thickness
        right_border.left = right
        right_border.bottom = bottom - thickness
        bottom_border.left = left - thickness
        bottom_border.top = bottom
        top_border.left = left - thickness
        top_border.bottom = top

        # добавление в список
        self.borders = arcade.SpriteList(use_spatial_hash = True)
        self.borders.append(left_border)
        self.borders.append(right_border)
        self.borders.append(bottom_border)
        self.borders.append(top_border)

    def prepare_physics_engine(self):
        self.physics_engine = arcade.PymunkPhysicsEngine(damping = 1 - self.characteristics.viscosity)
        self.physics_engine.add_sprite_list(
            self.borders,
            # todo: перенести в характеристики мира
            friction = 0,
            body_type = arcade.PymunkPhysicsEngine.STATIC
        )

    @property
    def id(self) -> int:
        if self._id is None:
            self._id = self.db_model.objects.count()
        return self._id

    def save_to_db(self):
        self.db_instance = self.db_model(id = self.id, stop_tick = self.age, width = self.width, height = self.height)
        self.db_instance.save()

    def start(self):
        self.save_to_db()
        self.spawn_start_creature()

    def stop(self):
        """Выполняет завершающие действия при окончании симуляции."""

        self.save_to_db()
        for creature in self.creatures:
            creature.stop()

    def spawn_start_creature(self):
        creature = BaseSimulationCreature(
            copy.copy(self.center),
            self,
            None,
            world_generation = True
        )
        creature.start()

    def add_creature(self, creature: BaseSimulationCreature):
        """Добавляет существо в мир."""

        self.creatures.append(creature)

    # если существо необходимо убить, то это нужно сделать отдельно
    def remove_creature(self, creature: BaseSimulationCreature):
        """Убирает существо из мира."""

        self.creatures.remove(creature)

    def on_update(self, delta_time: float):
        existing_creatures = copy.copy(self.creatures)
        for creature in existing_creatures:
            creature.on_update(delta_time)

        for line in self.chunks:
            for chunk in line:
                chunk.on_update()

        self.physics_engine.step()

        self.count_resources()
        self.age += 1

    def count_resources(self):
        if self.count_map_resources or self.count_world_resources:
            self.map_resources = Resources[int]()
            for line in self.chunks:
                for chunk in line:
                    self.map_resources += chunk.get_resources()

        if self.count_creatures_resources or self.count_world_resources:
            self.creatures_resources = Resources[int]()
            for creature in self.creatures:
                creature: BaseSimulationCreature
                self.creatures_resources += creature.remaining_resources
                self.creatures_resources += creature.storage.stored_resources

        if self.count_world_resources:
            self.world_resources = self.map_resources + self.creatures_resources

    def get_resources(self, position: tuple[float, float]) -> Resources[int]:
        """Возвращает ресурсы в чанке."""

        return self.position_to_chunk(position).get_resources()

    def add_resources(
            self,
            position: tuple[float, float],
            resources: Resources[int] | dict[BaseWorldResource, ResourceAmount[int] | int]
    ):
        """Добавляет ресурсы в чанк."""

        return self.position_to_chunk(position).add_resources(resources)

    def remove_resources(
            self,
            position: tuple[float, float],
            resources: Resources[int] | dict[BaseWorldResource, ResourceAmount[int] | int]
    ):
        """Убирает ресурсы из чанка."""

        return self.position_to_chunk(position).remove_resources(resources)

    def draw(self):
        self.borders.draw()
        # можно отрисовывать всех существ по отдельности, итерируясь по self.creatures,
        # что позволит переопределить метод draw существа (иначе, переопределение этого метода не влияет на отрисовку)
        self.creatures.draw()

        draw_chunks = True
        if draw_chunks:
            for line in self.chunks:
                for chunk in line:
                    chunk.draw()

    def position_to_chunk(self, position: tuple[float, float]) -> "BaseSimulationWorldChunk":
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


class BaseSimulationWorldChunk:
    def __init__(self, left_bottom: tuple[int, int], width: int, height: int):
        self.left = left_bottom[0]
        self.right = self.left + width - 1
        self.bottom = left_bottom[1]
        self.top = self.bottom + height - 1
        self.color = (100, 100, 100)
        resource_coef = 0.1
        self.default_resource_amount = int((self.right - self.left + 1) * (self.top - self.bottom + 1) * resource_coef)
        self._resources = Resources[int](
            {
                ENERGY: self.default_resource_amount,
                CARBON: self.default_resource_amount,
                OXYGEN: self.default_resource_amount,
                HYDROGEN: self.default_resource_amount
            }
        )

    def __repr__(self) -> str:
        return f"{self.left, self.bottom, self.right, self.top}"

    def on_update(self):
        self._resources[ENERGY] = self.default_resource_amount

    def get_resources(self) -> Resources[int]:
        return copy.deepcopy(self._resources)

    def add_resources(self, resources: Resources[int] | dict[BaseWorldResource, ResourceAmount[int] | int]):
        self._resources += resources

    def remove_resources(self, resources: Resources[int] | dict[BaseWorldResource, ResourceAmount[int] | int]):
        self._resources -= resources

    def draw(self):
        arcade.draw_xywh_rectangle_outline(
            self.left,
            self.bottom,
            self.right - self.left,
            self.top - self.bottom,
            self.color
        )

    @classmethod
    def cut_world(cls, world: BaseSimulationWorld) -> list[list["BaseSimulationWorldChunk"]]:
        left, right, bottom, top = world.get_borders_coordinates()
        chunks: list[list[cls]] = []

        left_bottom = list(world.center)
        while left_bottom[0] > left:
            left_bottom[0] -= world.chunk_width
        while left_bottom[1] > bottom:
            left_bottom[1] -= world.chunk_height

        for left in range(left_bottom[0], right, world.chunk_width):
            line = len(chunks)
            chunks.append([])
            for bottom in range(left_bottom[1], top, world.chunk_height):
                chunks[line].append(cls((left, bottom), world.chunk_width, world.chunk_height))

        return chunks
