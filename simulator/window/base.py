import arcade

from simulator.world import BaseSimulationWorld


class BaseWindow(arcade.Window):
    def __init__(self, width: int, height: int):
        super().__init__(width, height, center_window = True)

        background_color = (255, 255, 255)
        arcade.set_background_color(background_color)

        self.world: BaseSimulationWorld | None = None

    def start(self):
        self.world = BaseSimulationWorld(self.width, self.height)
        self.world.start()

    def show_world_age(self):
        color = (0, 0, 0)
        offset = (10, 10)
        font_size = 12
        arcade.draw_text(
            self.world.age,
            self.world.borders.left + offset[0],
            self.world.borders.top - offset[1] - font_size,
            color,
            font_size
        )

    def on_draw(self):
        self.clear()
        self.world.draw()
        self.show_world_age()

    def on_update(self, delta_time: float):
        # todo: return when engine will be set
        # self.physics_engine.update()
        self.world.on_update(delta_time)
