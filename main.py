import pygame
from pygame import locals
from tap import Tap

from worlds.base import BaseWorld


class ArgumentParser(Tap):
    """Программа, симулирующая эволюцию"""

    ticks: int = 100  # количество тиков симуляции
    width: int = 1000  # размер нулевого измерения (вширь)
    height: int = 1000  # размер первого измерения (в высоту)
    # лучше вынести в отдельный файл настройку количества и типов существ
    # todo: добавить возможность загружать мир с существами для продолжения симуляции
    creatures_number: int = 1  # количество начальных существ


if __name__ == "__main__":
    pygame.init()
    args = ArgumentParser(description = ArgumentParser.__doc__).parse_args()
    world = BaseWorld(args.width, args.height)
    world.spawn_start_creations(args.creatures_number)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == locals.QUIT or (event.type == locals.KEYDOWN and event.key == locals.K_ESCAPE):
                running = False
            elif event.type == locals.KEYDOWN:
                for _, creature in world.creatures.items():
                    if event.key == locals.K_UP:
                        creature.rectangle.move_ip(0, -10)
                    if event.key == locals.K_DOWN:
                        creature.rectangle.move_ip(0, 10)
                    if event.key == locals.K_LEFT:
                        creature.rectangle.move_ip(-10, 0)
                    if event.key == locals.K_RIGHT:
                        creature.rectangle.move_ip(10, 0)
                    creature.print_position()

        world.tick()
        world.draw()

        pygame.display.flip()

    pygame.quit()
