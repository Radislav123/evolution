import pygame
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from simulator.worlds.base import BaseWorld, Mode


@method_decorator(csrf_exempt, name = "dispatch")
class SimulationView(View):
    url = "simulation/"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.http_method_names.append("start")

    def start(
            self,
            request,
            ticks: int = 100,  # количество тиков симуляции
            width: int = 1000,  # размер нулевого измерения (вширь)
            height: int = 1000,  # размер первого измерения (в высоту)
            # todo: вынести в отдельный файл настройку количества и типов существ
            # todo: добавить возможность загружать мир с существами для продолжения симуляции
            creatures_number: int = 1,  # количество начальных существ
            mode: str = Mode.RECORD.value
            # режим работы
    ):
        pygame.init()
        mode = Mode(mode)
        world = BaseWorld(mode, width, height)
        world.spawn_start_creatures(creatures_number)

        for tick in range(ticks):
            world.tick()
            if mode is not Mode.RECORD:
                world.draw()
                pygame.display.flip()

        pygame.quit()
        return HttpResponse("The simulation is over.")
