from django.db import models


class EvolutionModel(models.Model):
    """Базовый класс для всех моделей проекта."""

    class Meta:
        abstract = True

    _update_fields: list[str] = None
    unique_fields: list[str] = ["id"]

    @classmethod
    def get_update_fields(cls) -> list[str]:
        if cls._update_fields is None:
            cls._update_fields = [x.name for x in cls._meta.fields if x.name != "id"]
        return cls._update_fields


class HistoryModel(EvolutionModel):
    """Базовый класс для моделей представляющих историю изменений."""

    class Meta:
        abstract = True


class World(EvolutionModel):
    # соотносится с world.age
    stop_tick = models.PositiveIntegerField()
    width = models.PositiveIntegerField()
    height = models.PositiveIntegerField()
    center_x = models.PositiveIntegerField()
    center_y = models.PositiveIntegerField()
    chunk_width = models.PositiveIntegerField()
    chunk_height = models.PositiveIntegerField()


class WorldCharacteristics(EvolutionModel):
    world = models.ForeignKey(World, models.PROTECT, primary_key = True)
    viscosity = models.FloatField()
    borders_friction = models.FloatField()
    borders_thickness = models.PositiveIntegerField()
    resource_coeff = models.FloatField()


class WorldChunk(EvolutionModel):
    # левая граница
    left = models.PositiveIntegerField()
    # нижняя граница
    bottom = models.PositiveIntegerField()
    color_red = models.PositiveIntegerField()
    color_green = models.PositiveIntegerField()
    color_blue = models.PositiveIntegerField()


class Creature(EvolutionModel):
    world = models.ForeignKey(World, models.PROTECT)
    # существо появилось
    start_tick = models.PositiveIntegerField()
    # существо перестало существовать или симуляция приостановлена
    stop_tick = models.IntegerField()
    # существо умерло
    # -1 == существо не умирало в симуляции
    death_tick = models.IntegerField()


# родителей может быть разное количество
class CreatureParent(EvolutionModel):
    world = models.ForeignKey(World, models.PROTECT)
    creature = models.ForeignKey(Creature, models.PROTECT, related_name = "creature_itself", primary_key = True)
    parent = models.ForeignKey(Creature, models.PROTECT, related_name = "creature_parent")


class CreaturePositionHistory(HistoryModel):
    creature = models.ForeignKey(Creature, models.PROTECT)
    age = models.PositiveIntegerField()
    position_x = models.FloatField()
    position_y = models.FloatField()


# todo: сделать эту модель историей изменений (history)
class CreatureStorage(EvolutionModel):
    creature = models.OneToOneField(Creature, models.PROTECT, primary_key = True)


# todo: сделать эту модель историей (history)
class StoredResource(EvolutionModel):
    creature_storage = models.ForeignKey(CreatureStorage, models.PROTECT)
    # формула ресурса
    # O/C/H/light
    resource = models.CharField(max_length = 10)
    capacity = models.IntegerField()
    current = models.IntegerField()
