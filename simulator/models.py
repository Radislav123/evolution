from django.db import models


class EvolutionModel(models.Model):
    class Meta:
        abstract = True


class ObjectModel(EvolutionModel):
    object_id = models.CharField(max_length = 100)

    class Meta:
        abstract = True


class World(ObjectModel):
    age = models.PositiveIntegerField()
    width = models.PositiveIntegerField()
    height = models.PositiveIntegerField()


class Creature(ObjectModel):
    # потребление|запасание|выбрасывание
    # <формула_количество.формула_количество...>|<формула_количество.формула_количество...>|<формула_количество.формула_количество...>
    # noinspection GrazieInspection
    # O_2.C_2.H_2.light_2|O_1.C_1.H_1.energy_1|O_1.C_1.H_1
    consumption_formula = models.CharField(max_length = 100)
    # изображение сохраняется последовательностью байтов (pygame.image.tobytes)
    surface = models.TextField()
    world = models.ForeignKey(World, models.PROTECT)


class CreatureParent(EvolutionModel):
    creature = models.ForeignKey(Creature, models.PROTECT, related_name = "creature_itself")
    parent = models.ForeignKey(Creature, models.PROTECT, related_name = "creature_parent")


class CreatureStorage(ObjectModel):
    creature = models.ForeignKey(Creature, models.PROTECT)


class StoredResource(EvolutionModel):
    # формула ресурса
    # O/C/H/light
    resource = models.CharField(max_length = 10)
    capacity = models.PositiveIntegerField()
    current = models.PositiveIntegerField()
    creature_storage = models.ForeignKey(CreatureStorage, models.PROTECT)


# характеризует сдвиг существа каждый тик
class CreatureMovement(EvolutionModel):
    age = models.IntegerField()
    creature = models.ForeignKey(Creature, models.PROTECT)
    x = models.IntegerField()
    y = models.IntegerField()
