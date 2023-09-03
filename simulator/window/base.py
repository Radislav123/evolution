import abc

import arcade

from simulator.creature import BaseSimulationCreature
from simulator.world import BaseSimulationWorld
from evolution import settings


class BaseTextTab(abc.ABC):
    # 00 - левый нижний угол (tabs[0], corner 0)
    # 01 - левый верхний угол (tabs[1], corner 1)
    # 10 - правый нижний угол (tabs[2], corner 2)
    # 11 - правый верхний угол (tabs[3], corner 3)
    # 01 11
    # 00 10
    # tabs[n] = {level: tab,..}
    tabs: list[dict[int, "BaseTextTab"]] = [{level: None for level in range(5)} for _ in range(4)]
    # расстояние между плашками
    level_gap = 10
    # расстояние от края окна
    window_border_gap = 10
    # todo: исправить наложение строк с ресурсами на карте и tps
    default_font_size = 12

    # corner - смотреть offset класса
    # level - номер плашки, считая от выбранного угла
    def __init__(
            self, window: "BaseSimulationWindow", corner: int, level: int, font_size: int = default_font_size,
            show = True
    ) -> None:
        self.window = window
        self.corner = corner
        self.level = level
        self.font_size = font_size
        self.show = show
        self.tabs[corner][level] = self

        color = (0, 0, 0)
        self.text = arcade.Text("", 0, 0, color, font_size)

    @property
    @abc.abstractmethod
    def string(self) -> str:
        raise NotImplementedError()

    @classmethod
    def calculate_positions(cls) -> None:
        for corner in cls.tabs:
            offset_y = 0
            for tab in corner.values():
                if tab is None:
                    offset_y += cls.level_gap + cls.default_font_size
                else:
                    if tab.corner in [0, 1]:
                        start_x = tab.window_border_gap
                        anchor_x = "left"
                    else:
                        start_x = tab.window.width - tab.window_border_gap
                        anchor_x = "right"
                    if tab.corner in [0, 2]:
                        start_y = tab.window_border_gap + offset_y
                        anchor_y = "baseline"
                    else:
                        start_y = tab.window.height - tab.window_border_gap - offset_y
                        anchor_y = "top"
                    offset_y += tab.level_gap + tab.font_size

                    tab.text.x = start_x
                    tab.text.y = start_y
                    tab.text.anchor_x = anchor_x
                    tab.text.anchor_y = anchor_y

    def draw(self) -> None:
        if self.show:
            self.text.text = self.string
            self.text.draw()

    @classmethod
    def draw_all(cls) -> None:
        for corner in cls.tabs:
            for tab in corner.values():
                if tab is not None:
                    tab.draw()


class WorldAgeTab(BaseTextTab):
    @property
    def string(self) -> str:
        return self.window.world.age


class CreaturesCounterTab(BaseTextTab):
    @property
    def string(self) -> str:
        return f"Сейчас существ: {BaseSimulationCreature.birth_counter - BaseSimulationCreature.death_counter}"


class CreaturesBirthDeathCounterTab(BaseTextTab):
    @property
    def string(self) -> str:
        return f"Появилось: {BaseSimulationCreature.birth_counter}, умерло: {BaseSimulationCreature.death_counter}"


class MapResourcesCounterTab(BaseTextTab):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if self.show:
            self.window.world.count_map_resources.set()

    @property
    def string(self) -> str:
        return f"Ресурсы на карте: {self.window.world.map_resources}"


class CreaturesResourcesCounterTab(BaseTextTab):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if self.show:
            self.window.world.count_creatures_resources.set()

    @property
    def string(self) -> str:
        return f"Ресурсы существ: {self.window.world.creatures_resources}"


class WorldResourcesCounterTab(BaseTextTab):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if self.show:
            self.window.world.count_world_resources.set()

    @property
    def string(self) -> str:
        return f"Ресурсы в мире: {self.window.world.world_resources}"


class TPSTab(BaseTextTab):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        arcade.enable_timings()

    string = "not implemented"


class BaseSimulationWindow(arcade.Window):
    # desired_tps = int(1 / update_rate)
    # update_rate = 1 / tps
    desired_tps: int
    tps_tab: TPSTab

    def __init__(self, width: int, height: int) -> None:
        super().__init__(width, height, center_window = True)

        self.world: BaseSimulationWorld | None = None
        self.tabs: list[BaseTextTab] | None = None
        self.set_tps(settings.MAX_TPS)

        background_color = (255, 255, 255)
        arcade.set_background_color(background_color)

    def start(self, world_width: int, world_height: int) -> None:
        center = (self.width // 2, self.height // 2)
        self.world = BaseSimulationWorld(world_width, world_height, center)
        self.world.start()

        # плашки используют объект world
        self.tps_tab = TPSTab(self, 3, 1)
        # todo: добавить возможность выключать расчеты и вывод информации на плашках (сделать их кнопками?)
        # todo: заменить свои плашки на элементы UIWidget из arcade
        tabs = [
            WorldAgeTab(self, 3, 0),
            CreaturesBirthDeathCounterTab(self, 2, 0),
            CreaturesCounterTab(self, 2, 1),
            WorldResourcesCounterTab(self, 1, 0),
            MapResourcesCounterTab(self, 1, 1),
            CreaturesResourcesCounterTab(self, 1, 2),
            self.tps_tab
        ]
        self.tabs = tabs
        BaseTextTab.calculate_positions()

    def on_draw(self) -> None:
        self.clear()
        self.world.draw()
        BaseTextTab.draw_all()

    def on_update(self, delta_time: float) -> None:
        try:
            self.world.on_update(delta_time)
        except Exception as error:
            error.window = self
            raise error
        finally:
            if self.world.age % 10 == 0:
                timings = arcade.get_timings()
                # за 100 последних тиков
                execution_time_100 = 0
                for i in timings:
                    execution_time_100 += sum(timings[i])
                average_execution_time = execution_time_100 / 100
                self.tps_tab.string = f"tps/желаемые tps: {int(1 / average_execution_time)} / {self.desired_tps}"

    def set_tps(self, tps: int) -> None:
        self.desired_tps = tps
        self.set_update_rate(1 / tps)

    # todo: remove this method
    def on_mouse_press(self, x, y, button, modifiers) -> None:
        print(f"x: {x}, y: {y}")
