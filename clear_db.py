# noinspection PyUnresolvedReferences
import configure_django
from core import models


def main():
    models.CreaturePositionHistory.objects.all().delete()
    models.Creature.objects.all().delete()
    models.WorldCharacteristics.objects.all().delete()
    models.World.objects.all().delete()


if __name__ == "__main__":
    main()
