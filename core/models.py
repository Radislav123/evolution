from django.db import models


class EvolutionModel(models.Model):
    """Базовый класс для всех моделей проекта."""

    class Meta:
        abstract = True

    _update_fields: list[str] = None
    unique_fields: set[str] = {"id"}

    @classmethod
    def get_update_fields(cls) -> list[str]:
        if cls._update_fields is None:
            cls._update_fields = [x.name for x in cls._meta.fields if x.name not in cls.unique_fields]
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


class Creature(EvolutionModel):
    world = models.ForeignKey(World, models.PROTECT)
    # существо появилось
    start_tick = models.PositiveIntegerField(null = True)
    # существо перестало существовать или симуляция приостановлена
    stop_tick = models.IntegerField(null = True)
    # существо умерло
    death_tick = models.IntegerField(null = True)


class CreaturePositionHistory(HistoryModel):
    creature = models.ForeignKey(Creature, models.PROTECT)
    age = models.PositiveIntegerField()
    position_x = models.FloatField()
    position_y = models.FloatField()
