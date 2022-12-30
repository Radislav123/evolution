import copy

import arcade

from core import models
from core.mixin import DatabaseSavableMixin, WorldObjectMixin
from simulator.creature import BaseSimulationCreature
from simulator.physic import BaseWorldCharacteristics
from simulator.world_resource import CARBON, ENERGY, HYDROGEN, OXYGEN, Resources


class BaseSimulationWorld(DatabaseSavableMixin, WorldObjectMixin):
    db_model = models.World
    db_instance: models.World

    # width - минимальное значение ширины экрана - 120
    def __init__(self, width: int, height: int):
        self._id = None
        self.age = 0
        self.width = width
        self.height = height
        self.center = (width // 2, height // 2)
        self.chunk_width = 10
        self.chunk_height = 10

        # границы мира
        self.borders = BaseSimulationWorldBorders(0, self.width, 0, self.height)
        # {creature.object_id: creature}
        self.creatures = arcade.SpriteList()
        self.characteristics = BaseWorldCharacteristics(0.1)
        self.physics_engine = self.prepare_physics_engine()
        self.chunks = BaseSimulationWorldChunk.cut_world(self)

    def prepare_physics_engine(self) -> arcade.PymunkPhysicsEngine:
        physics_engine = arcade.PymunkPhysicsEngine(damping = 1 - self.characteristics.viscosity)
        return physics_engine

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

        self.physics_engine.step()

        for line in self.chunks:
            for chunk in line:
                chunk.on_update()

        self.age += 1

    def get_resources(self, position: tuple[float, float]) -> Resources[int]:
        """Возвращает ресурсы в чанке."""

        return self.position_to_chunk(position).get_resources()

    def add_resources(self, position: tuple[float, float], resources: Resources[int]):
        """Добавляет ресурсы в чанк."""

        return self.position_to_chunk(position).add_resources(resources)

    def remove_resources(self, position: tuple[float, float], resources: Resources[int]):
        """Убирает ресурсы из чанка."""

        return self.position_to_chunk(position).remove_resources(resources)

    def draw(self):
        # можно отрисовывать всех существ по отдельности, итерируясь по self.creatures,
        # что позволит переопределить метод draw существа (иначе, переопределение этого метода не влияет на отрисовку)
        self.creatures.draw()
        self.borders.draw()

        draw_chunks = False
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


class BaseSimulationWorldBorders:
    def __init__(self, left, right, bottom, top):
        # todo: использовать use_spatial_hash, когда буду переводить на спрайты
        self.left = left
        self.right = right
        self.bottom = bottom
        self.top = top
        self.color = (0, 0, 0)

    def draw(self):
        arcade.draw_xywh_rectangle_outline(
            self.left,
            self.bottom,
            self.right - self.left,
            self.top - self.bottom,
            self.color
        )


class BaseSimulationWorldChunk:
    def __init__(self, left_bottom: tuple[int, int], width: int, height: int):
        self.left = left_bottom[0]
        self.right = self.left + width - 1
        self.bottom = left_bottom[1]
        self.top = self.bottom + height - 1
        self.color = (0, 0, 0)
        self.default_resource_amount = (self.right - self.left + 1) * (self.top - self.bottom + 1) * 5
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

    def add_resources(self, resources: Resources[int]):
        self._resources += resources

    def remove_resources(self, resources: Resources[int]):
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
        chunks: list[list[cls]] = []

        left_bottom = list(world.center)
        while left_bottom[0] > world.borders.left:
            left_bottom[0] -= world.chunk_width
        while left_bottom[1] > world.borders.bottom:
            left_bottom[1] -= world.chunk_height

        for left in range(left_bottom[0], world.borders.right, world.chunk_width):
            line = len(chunks)
            chunks.append([])
            for bottom in range(left_bottom[1], world.borders.top, world.chunk_height):
                chunks[line].append(cls((left, bottom), world.chunk_width, world.chunk_height))

        return chunks
