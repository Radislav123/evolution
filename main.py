import pygame
from tap import Tap
from typing_extensions import Literal

from worlds.base import BaseWorld, Mode


class ArgumentParser(Tap):
    """Программа, симулирующая эволюцию"""

    ticks: int = 100  # количество тиков симуляции
    width: int = 1000  # размер нулевого измерения (вширь)
    height: int = 1000  # размер первого измерения (в высоту)
    # todo: вынести в отдельный файл настройку количества и типов существ
    # todo: добавить возможность загружать мир с существами для продолжения симуляции
    creatures_number: int = 1  # количество начальных существ
    # noinspection PyTypeHints
    mode: Literal[Mode.INTERACTIVE.value, Mode.RECORD.value, Mode.PLAY.value] = Mode.INTERACTIVE.value  # режим работы


if __name__ == "__main__":
    pygame.init()
    args = ArgumentParser(description = ArgumentParser.__doc__).parse_args()
    world = BaseWorld(args.mode, args.width, args.height)
    world.spawn_start_creatures(args.creatures_number)

    for tick in range(args.ticks):
        world.tick()
        world.draw()
        pygame.display.flip()

    pygame.quit()
