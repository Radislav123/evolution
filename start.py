from typing import TextIO

import arcade

# noinspection PyUnresolvedReferences
import configure_django
from simulator.creature import BaseSimulationCreature
from simulator.window import BaseWindow
from simulator.world import BaseSimulationWorld


SECTION_DELIMITER = "\n"


def log_attributes(obj: object, file: TextIO):
    file.write("---------- Attributes info ----------\n")
    for attribute in obj.__dict__:
        file.write(f"{attribute}: {obj.__dict__[attribute]}\n")


def log_error(error: Exception, file: TextIO):
    file.write("========== Error info ==========\n")
    file.write(f"{error}\n")


def log_window(window: BaseWindow, file: TextIO):
    file.write("========== Window info ==========\n")
    file.write(f"{window}\n")


def log_world(world: BaseSimulationWorld, file: TextIO):
    file.write("========== World info ==========\n")
    file.write(f"{world}\n")


def log_creature(creature: BaseSimulationCreature, file: TextIO):
    file.write("========== Creature info ==========\n")
    file.write(f"{creature}\n")


def log_child(child: BaseSimulationCreature, file: TextIO):
    file.write("========== Child info ==========\n")
    file.write(f"{child}\n")


def log_error_info(error: Exception):
    with open("exception_info.txt", 'w') as file:
        log_error(error, file)
        log_attributes(error, file)
        file.write(SECTION_DELIMITER)
        if hasattr(error, "window"):
            log_window(error.window, file)
            log_attributes(error.window, file)
            file.write(SECTION_DELIMITER)
        if hasattr(error, "world"):
            log_world(error.world, file)
            log_attributes(error.world, file)
            file.write(SECTION_DELIMITER)
        if hasattr(error, "creature"):
            log_creature(error.creature, file)
            log_attributes(error.creature, file)
            file.write(SECTION_DELIMITER)
        if hasattr(error, "child"):
            log_creature(error.child, file)
            log_attributes(error.child, file)
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
