from typing import TextIO

import arcade

# noinspection PyUnresolvedReferences
import configure_django
from simulator.creature import BaseSimulationCreature
from simulator.window import BaseWindow
from simulator.world import BaseSimulationWorld


SECTION_DELIMITER = "\n"


def log_error(error: Exception, file: TextIO):
    file.write("========== Error info ==========\n")
    file.write(f"{error}\n")


def log_window(window: BaseWindow, file: TextIO):
    file.write("========== Window info ==========\n")
    file.write(f"{window}\n")


def log_world(world: BaseSimulationWorld, file: TextIO):
    file.write("========== World info ==========\n")
    file.write(f"{world}\n")
    file.write(f"age: {world.age}, width: {world.width}, height: {world.height}\n")
    file.write(f"{world.characteristics}\n")


def log_creature(creature: BaseSimulationCreature, file: TextIO):
    file.write("========== Creature info ==========\n")
    file.write(f"{creature}\n")
    file.write(f"alive: {creature.alive}\n")
    file.write(f"{creature.characteristics}\n")
    file.write(f"parents: {creature.parents}\n")
    file.write(f"bodyparts: {creature.bodyparts}\n")


def log_error_info(error: Exception):
    with open("exception_info.txt", 'w') as file:
        log_error(error, file)
        file.write(SECTION_DELIMITER)
        if hasattr(error, "window"):
            log_window(error.window, file)
            file.write(SECTION_DELIMITER)
        if hasattr(error, "world"):
            log_world(error.world, file)
            file.write(SECTION_DELIMITER)
        if hasattr(error, "creature"):
            log_creature(error.creature, file)
            file.write(SECTION_DELIMITER)


# https://www.b-list.org/weblog/2007/sep/22/standalone-django-scripts/
def simulate():
    width = 500
    height = 500

    window = BaseWindow(width, height)
    try:
        window.start()
        arcade.run()
    except Exception as error:
        log_error_info(error)
        raise error
    finally:
        window.world.stop()
    print(f"Симуляция окончена. World id: {window.world.id}.")


if __name__ == "__main__":
    simulate()
