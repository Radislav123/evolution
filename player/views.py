from django.http import HttpRequest, HttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt


@method_decorator(csrf_exempt, name = "dispatch")
class PlaybackView(View):
    url = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.http_method_names.append("play")

    # noinspection PyTypeChecker
    @staticmethod
    def process_parameters(request: HttpRequest):
        parameters = request.GET
        world_db_id = int(parameters["world_db_id"])
        # ticks per second
        tps = int(parameters["tps"])
        return world_db_id, tps

    def play(self, request: HttpRequest):
        world_db_id, tps = self.process_parameters(request)

        # return HttpResponse(f"Воспроизведение окончено. World id {world.id}.")
        return HttpResponse(f"Воспроизведение окончено. World id .")
