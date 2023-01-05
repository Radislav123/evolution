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
    file.write(f"{error.__class__.__name__}: {error}\n")


def log_window(window: BaseWindow, file: TextIO):
    file.write(f"{window}\n")


def log_world(world: BaseSimulationWorld, file: TextIO):
    file.write(f"{world}\n")


def log_creature(creature: BaseSimulationCreature, file: TextIO):
    file.write(f"{creature}\n")
    try:
        file.write(f"bodyparts: {creature.bodyparts}\n")
    except Exception as error:
        log_error(error, file)


def log_genome_effects(creature: BaseSimulationCreature, file: TextIO):
    file.write("~~~~~~~~~~ Genome effects info ~~~~~~~~~~\n")
    for attribute in creature.genome.effects.__dict__:
        file.write(f"{attribute}: {creature.genome.effects.__dict__[attribute]}\n")


def log_error_info(error: Exception):
    with open("exception_info.txt", 'w') as file:
        file.write("========== Error info ==========\n")
        log_error(error, file)
        log_attributes(error, file)
        file.write(SECTION_DELIMITER)
        if hasattr(error, "window"):
            file.write("========== Window info ==========\n")
            log_window(error.window, file)
            log_attributes(error.window, file)
            file.write(SECTION_DELIMITER)
        if hasattr(error, "world"):
            file.write("========== World info ==========\n")
            log_world(error.world, file)
            log_attributes(error.world, file)
            file.write(SECTION_DELIMITER)
        if hasattr(error, "creature"):
            file.write("========== Creature info ==========\n")
            log_creature(error.creature, file)
            log_attributes(error.creature, file)
            log_genome_effects(error.creature, file)
            file.write(SECTION_DELIMITER)
        if hasattr(error, "child"):
            file.write("========== Child info ==========\n")
            log_creature(error.child, file)
            log_attributes(error.child, file)
            log_genome_effects(error.child, file)
            file.write(SECTION_DELIMITER)
        if hasattr(error, "init_creature"):
            file.write("========== Init creature info ==========\n")
            log_creature(error.init_creature, file)
            log_attributes(error.init_creature, file)
            log_genome_effects(error.init_creature, file)
            file.write(SECTION_DELIMITER)


# https://www.b-list.org/weblog/2007/sep/22/standalone-django-scripts/
def simulate():
    width = 100
    height = 100

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
