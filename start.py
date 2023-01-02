import arcade

# noinspection PyUnresolvedReferences
import configure_django
from simulator.window import BaseWindow


# https://www.b-list.org/weblog/2007/sep/22/standalone-django-scripts/
def simulate():
    width = 50
    height = 50

    window = BaseWindow(width, height)
    try:
        window.start()
        arcade.run()
    except Exception as error:
        raise error
    finally:
        window.world.stop()
    print(f"Симуляция окончена. World id: {window.world.id}.")


if __name__ == "__main__":
    simulate()
