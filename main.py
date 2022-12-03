from tap import Tap

from creatures.base import BaseCreature
from worlds.base import BaseWorld


class ArgumentParser(Tap):
    """Программа, симулирующая эволюцию"""
    ticks: int = 100  # количество тиков симуляции
    dimension_0: int = 100  # размер нулевого измерения
    dimension_1: int = 100  # размер первого измерения
    # лучше вынести в отдельный файл
    creatures_number: int = 1  # количество начальных существ


def get_start_creatures(number: int):
    return [BaseCreature() for _ in range(number)]


if __name__ == "__main__":
    args = ArgumentParser().parse_args()
    world = BaseWorld(dimension_0 = args.dimension_0, dimension_1 = args.dimension_1)
    creatures = get_start_creatures(args.creatures_number)

    for tick in range(args.ticks):
        print(f"\ntime: {tick}")
        for creature in creatures:
            creature.tick()
