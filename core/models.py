from django.db import models


class EvolutionModel(models.Model):
    class Meta:
        abstract = True


class World(EvolutionModel):
    stop_tick = models.PositiveIntegerField()
    width = models.PositiveIntegerField()
    height = models.PositiveIntegerField()


class Creature(EvolutionModel):
    world = models.ForeignKey(World, models.RESTRICT)
    # существо появилось
    start_tick = models.IntegerField()
    # существо перестало существовать
    stop_tick = models.IntegerField()


class CreatureParent(EvolutionModel):
    creature = models.ForeignKey(Creature, models.RESTRICT, related_name = "creature_itself", primary_key = True)
    parent = models.ForeignKey(Creature, models.RESTRICT, related_name = "creature_parent")


class CreatureStorage(EvolutionModel):
    creature = models.OneToOneField(Creature, models.RESTRICT, primary_key = True)


class StoredResource(EvolutionModel):
    creature_storage = models.ForeignKey(CreatureStorage, models.RESTRICT)
    # формула ресурса
    # O/C/H/light
    resource = models.CharField(max_length = 10)
    capacity = models.IntegerField()
    current = models.IntegerField()
