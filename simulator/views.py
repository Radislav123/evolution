import pygame
from django.http import HttpRequest, HttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from simulator.object.world.base import BaseSimulationWorld


@method_decorator(csrf_exempt, name = "dispatch")
class SimulationView(View):
    url = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.http_method_names.append("simulate")

    # noinspection PyTypeChecker
    @staticmethod
    def process_parameters(request: HttpRequest):
        parameters = request.GET
        ticks = int(parameters["ticks"])
        width = int(parameters["width"])
        height = int(parameters["height"])
        draw = bool(int(parameters["draw"]))
        # ticks per second
        tps = int(parameters["tps"])
        return ticks, width, height, draw, tps

    # todo: добавить возможность загружать мир с существами для продолжения симуляции
    def simulate(self, request: HttpRequest):
        ticks, width, height, draw, tps = self.process_parameters(request)

        pygame.init()
        world = BaseSimulationWorld(width, height)
        if not draw:
            pygame.display.set_mode(flags = pygame.HIDDEN)
        world.start()
        clock = pygame.time.Clock()

        try:
            for tick in range(ticks):
                # чтобы окно не зависало (freeze)
                pygame.event.pump()
                world.tick()
                if draw:
                    world.draw()
                clock.tick(tps)
        except Exception as error:
            raise error
        finally:
            world.stop()
            pygame.quit()

        return HttpResponse("Симуляция окончена.")
