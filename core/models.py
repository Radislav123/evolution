from django.db import models


class EvolutionModel(models.Model):
    class Meta:
        abstract = True


class ObjectModel(EvolutionModel):
    class Meta:
        abstract = True


class World(ObjectModel):
    stop_tick = models.PositiveIntegerField()
    width = models.PositiveIntegerField()
    height = models.PositiveIntegerField()


class Creature(ObjectModel):
    # потребление|запасание|выбрасывание
    # <формула_количество.формула_количество...>|<формула_количество.формула_количество...>|<формула_количество.формула_количество...>
    # noinspection GrazieInspection
    # O_2.C_2.H_2.light_2|O_1.C_1.H_1.energy_1|O_1.C_1.H_1
    consumption_formula = models.CharField(max_length = 100)
    world = models.ForeignKey(World, models.RESTRICT)
    # существо появилось
    start_tick = models.IntegerField()
    # существо перестало существовать
    stop_tick = models.IntegerField()
    start_x = models.PositiveIntegerField()
    start_y = models.PositiveIntegerField()


class CreatureSurface(EvolutionModel):
    creature = models.OneToOneField(Creature, models.RESTRICT, primary_key = True)
    # изображение сохраняется последовательностью байтов (pygame.image.tobytes)
    image = models.BinaryField()
    width = models.IntegerField()
    height = models.IntegerField()


class CreatureParent(EvolutionModel):
    creature = models.ForeignKey(Creature, models.RESTRICT, related_name = "creature_itself")
    parent = models.ForeignKey(Creature, models.RESTRICT, related_name = "creature_parent")


class CreatureStorage(ObjectModel):
    creature = models.OneToOneField(Creature, models.RESTRICT, primary_key = True)


class StoredResource(EvolutionModel):
    creature_storage = models.ForeignKey(CreatureStorage, models.RESTRICT)
    # формула ресурса
    # O/C/H/light
    resource = models.CharField(max_length = 10)
    capacity = models.PositiveIntegerField()
    current = models.PositiveIntegerField()


# характеризует сдвиг существа каждый тик
class CreatureMovement(EvolutionModel):
    creature = models.ForeignKey(Creature, models.RESTRICT)
    age = models.IntegerField()
    x = models.IntegerField()
    y = models.IntegerField()

    def __str__(self):
        return f"creature: {self.creature}, age: {self.age}, x: {self.x}, y: {self.y}"
