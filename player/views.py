import pygame
from django.http import HttpRequest, HttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from player.object.world.base import BasePlaybackWorld


@method_decorator(csrf_exempt, name = "dispatch")
class PlaybackView(View):
    url = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.http_method_names.append("playback")

    # noinspection PyTypeChecker
    @staticmethod
    def process_parameters(request: HttpRequest):
        parameters = request.GET
        world_id = int(parameters["world_id"])
        return world_id

    def playback(self, request: HttpRequest):
        world_id = self.process_parameters(request)

        pygame.init()
        world = BasePlaybackWorld(world_id)
        world.start()

        try:
            for tick in world.age:
                world.tick()
                world.draw()
                pygame.display.flip()
        except Exception as error:
            raise error
        finally:
            world.stop()
            pygame.quit()

        return HttpResponse("Воспроизведение окончено.")
