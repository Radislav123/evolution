import arcade
from django.http import HttpRequest, HttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from core.force_server_update import reload_server
from simulator.window import BaseWindow


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

        window = BaseWindow(width, height)
        try:
            window.start()
            arcade.run()
        except Exception as error:
            raise error
        finally:
            window.world.stop()
            reload_server()

        return HttpResponse(f"Симуляция окончена. World id: {window.world.id}.")
