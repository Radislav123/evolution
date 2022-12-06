import pygame
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from simulator.object.world.base import BaseWorld, Mode


@method_decorator(csrf_exempt, name = "dispatch")
class SimulationView(View):
    url = "simulation/"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.http_method_names.append("start")

    # todo: добавить возможность загружать мир с существами для продолжения симуляции
    def start(
            self,
            request,
            ticks: int = 100,  # количество тиков симуляции
            width: int = 1000,  # размер нулевого измерения (вширь)
            height: int = 1000,  # размер первого измерения (в высоту)
            mode: str = Mode.INTERACTIVE.value
            # режим работы
    ):
        pygame.init()
        mode = Mode(mode)
        world = BaseWorld(width, height)
        world.start()

        try:
            for tick in range(ticks):
                world.tick()
                if mode is not Mode.RECORD:
                    world.draw()
                    pygame.display.flip()
        except Exception as error:
            raise error
        finally:
            world.stop()
            pygame.quit()

        return HttpResponse("The simulation is over.")
