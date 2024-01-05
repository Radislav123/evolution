from typing import TextIO

import arcade

# noinspection PyUnresolvedReferences
import configure_django
from simulator.creature import Creature
from simulator.window import Window
from simulator.world import World


SECTION_DELIMITER = "\n"


def log_attributes(obj: object, file: TextIO):
    file.write("---------- Attributes info ----------\n")
    for attribute in obj.__dict__:
        file.write(f"{attribute}: {obj.__dict__[attribute]}\n")


def log_error(error: Exception, file: TextIO):
    file.write(f"{error.__class__.__name__}: {error}\n")


def log_window(window: Window, file: TextIO):
    file.write(f"{window}\n")


def log_world(world: World, file: TextIO):
    file.write(f"{world}\n")


def log_creature(creature: Creature, file: TextIO):
    file.write(f"{creature}\n")
    try:
        file.write(f"bodyparts: {creature.bodyparts}\n")
    except Exception as error:
        log_error(error, file)
    log_attributes(creature, file)
    log_genome(creature, file)
    log_action(creature, file)


def log_genome(creature: Creature, file: TextIO):
    file.write("~~~~~~~~~~ Genome info ~~~~~~~~~~\n")
    if hasattr(creature, "genome"):
        for attribute in creature.genome.__dict__:
            file.write(f"{attribute}: {creature.genome.__dict__[attribute]}\n")

    file.write("~~~~~~~~~~ Genome effects info ~~~~~~~~~~\n")
    if hasattr(creature, "genome"):
        for attribute in creature.genome.effects.__dict__:
            file.write(f"{attribute}: {creature.genome.effects.__dict__[attribute]}\n")


def log_action(creature: Creature, file: TextIO):
    file.write("~~~~~~~~~~ Action info ~~~~~~~~~~\n")
    if hasattr(creature, "action") and creature.action is not None:
        for attribute in creature.action.__dict__:
            file.write(f"{attribute}: {creature.action.__dict__[attribute]}\n")


# todo: сохранять в json-формате
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
            file.write(SECTION_DELIMITER)
        if hasattr(error, "parents"):
            file.write("========== Parents info ==========\n")
            for parent in error.parents:
                file.write("========== Parent info ==========\n")
                log_creature(parent, file)
                file.write(SECTION_DELIMITER)
        if hasattr(error, "child"):
            file.write("========== Child info ==========\n")
            log_creature(error.child, file)
            file.write(SECTION_DELIMITER)
        if hasattr(error, "next_children"):
            file.write("========== Next children info ==========\n")
            for next_child in error.next_children:
                file.write("========== Next child info ==========\n")
                log_creature(next_child, file)
                file.write(SECTION_DELIMITER)
        if hasattr(error, "init_creature"):
            file.write("========== Init creature info ==========\n")
            log_creature(error.init_creature, file)
            file.write(SECTION_DELIMITER)


# https://www.b-list.org/weblog/2007/sep/22/standalone-django-scripts/
def simulate():
    window_width = 800
    window_height = 600

    window = Window(window_width, window_height)
    try:
        window.start()
        arcade.run()
        window.stop()
    except Exception as error:
        window.stop()
        log_error_info(error)
        raise error
    finally:
        print(f"Симуляция окончена. Мир: {window.world.id}. Возраст мира: {window.world.age}")


if __name__ == "__main__":
    simulate()
