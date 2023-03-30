import arcade

from evolution import settings
from player.world import BasePlaybackWorld, WorldHistoryEndException


class BasePlaybackWindow(arcade.Window):
    # desired_tps = int(1 / update_rate)
    # update_rate = 1 / tps
    desired_tps: int

    def __init__(self, width: int, height: int):
        super().__init__(width, height, center_window = True)

        self.world: BasePlaybackWorld | None = None
        # показывает, есть ли у воспроизводимого мира дальнейшая история
        self.history_end = False

        self.set_tps(settings.MAX_TPS)
        background_color = (255, 255, 255)
        arcade.set_background_color(background_color)

    def start(self, world_id: int):
        center = (self.width // 2, self.height // 2)

        self.world = BasePlaybackWorld(world_id)

    def on_draw(self):
        self.clear()
        self.world.draw()

    def on_update(self, delta_time: float):
        try:
            if not self.history_end:
                self.world.on_update(delta_time)
        except Exception as error:
            error.window = self
            if isinstance(error, WorldHistoryEndException):
                self.history_end = True
            else:
                raise error

    def set_tps(self, tps: int):
        self.desired_tps = tps
        self.set_update_rate(1 / tps)
