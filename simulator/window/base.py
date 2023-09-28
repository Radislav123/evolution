import dataclasses
import enum
from collections import defaultdict
from typing import Any, Callable, Iterator

import arcade
import arcade.gui

from core.service import ObjectDescriptionReader
from evolution import settings
from simulator.creature import Creature
from simulator.world import World
from simulator.world_resource import Resources


@dataclasses.dataclass
class WindowDescriptor:
    name: str
    tab_update_rate: int
    world_age_tab_update_rate: int
    tps_tab_update_rate: int
    resources_tab_update_rate: int


window_descriptor: WindowDescriptor = ObjectDescriptionReader[WindowDescriptor]().read_folder_to_list(
    settings.WINDOW_DESCRIPTIONS_PATH,
    WindowDescriptor
)[0]


class TextTab(arcade.gui.UIFlatButton):
    class State(enum.Enum):
        NOT_PRESSED = 0
        PRESSED = 1

        @property
        def next(self) -> "TextTab.State":
            return self.__class__((self.value + 1) % len(self.__class__))

        def __str__(self) -> str:
            if self == self.NOT_PRESSED:
                string = "[  ]"
            elif self == self.PRESSED:
                string = "[x]"
            else:
                raise ValueError()
            return string

    class Label(arcade.Text):
        def __init__(self, tab: "TextTab", text: Callable[[], str], update_rate: int, *args, **kwargs) -> None:
            self.tab = tab
            self._text = text
            # количество тиков между обновлением текста
            self.update_rate = update_rate

            color = (0, 0, 0)
            super().__init__(tab.text, 0, 0, color = color, *args, **kwargs)

        def set_position(self) -> None:
            offset_x = 5
            offset_y = 8
            if self.tab.corner.index in [0, 1]:
                start_x = self.tab.rect.x + self.tab.width + offset_x
                anchor_x = "left"
            else:
                start_x = self.tab.rect.x - offset_x
                anchor_x = "right"
            start_y = self.tab.rect.y + offset_y
            anchor_y = "baseline"

            self.x = start_x
            self.y = start_y
            self.anchor_x = anchor_x
            self.anchor_y = anchor_y

    font_size = 12

    def __init__(
            self,
            text: Callable[..., str],
            update_rate: int,
            on_click: Callable[..., Any] | None = None,
            on_click_args = None
    ) -> None:
        super().__init__()

        self.update_rate = update_rate
        self.state: TextTab.State | None = None
        self.set()
        self.corner: TextTabContainer.Corner | None = None
        self.update_text()
        border = 10
        self.rect = self.rect.resize(round(self.ui_label.width) + border, round(self.ui_label.height) + border)
        self.tab_label = self.Label(self, text, self.update_rate)
        if on_click is None:
            def on_click() -> None:
                pass
        if on_click_args is None:
            on_click_args = []
        self._on_click = on_click
        self._on_click_args = on_click_args

    def __bool__(self) -> bool:
        return self.state == self.State.PRESSED

    def set(self) -> None:
        self.state = self.State.PRESSED
        self.update_text()

    def reset(self) -> None:
        self.state = self.State.NOT_PRESSED
        self.update_text()

    def on_click(self, event: arcade.gui.UIOnClickEvent = None) -> None:
        if self.state == self.State.PRESSED:
            self.reset()
        else:
            self.set()
        self.update_text()
        # noinspection PyArgumentList
        self._on_click(*self._on_click_args)

    def update_text(self) -> None:
        self.text = str(self.state)


class TPSTab(TextTab):
    def set(self) -> None:
        super().set()
        arcade.enable_timings()

    def reset(self) -> None:
        super().reset()
        try:
            arcade.disable_timings()
        except ValueError:
            # при отключении всегда выбрасывается исключение
            pass


class TextTabContainer:
    class Corner(arcade.gui.UIAnchorLayout):
        children: list[TextTab]

        def __init__(self, container: "TextTabContainer", index: int, *args, **kwargs) -> None:
            self.container = container
            self.index = index
            super().__init__(*args, **kwargs)

        def add(self, child: TextTab, **kwargs) -> TextTab:
            child.corner = self
            child.corner_position = len(self.children)

            if self.index in [0, 1]:
                anchor_x = "left"
            else:
                anchor_x = "right"
            if self.index in [0, 2]:
                anchor_y = "bottom"
                align_y = sum(map(lambda x: x.height, self.children))
            else:
                anchor_y = "top"
                align_y = -sum(map(lambda x: x.height, self.children))

            result = super().add(child, anchor_x = anchor_x, anchor_y = anchor_y, align_y = align_y, **kwargs)
            self.container.tabs.add(result)
            self.container.tab_update_rates[result.update_rate].add(result)

            return result

    def __init__(self, window: "Window") -> None:
        self.window = window
        # 00 - левый нижний угол (corners[0])
        # 01 - левый верхний угол (corners[1])
        # 10 - правый нижний угол (corners[2])
        # 11 - правый верхний угол (corners[3])
        # 01 11
        # 00 10
        # 1 3
        # 0 2
        # tab_container[n] = [tab_0, tab_1,..]
        self.corners: tuple[
            TextTabContainer.Corner,
            TextTabContainer.Corner,
            TextTabContainer.Corner,
            TextTabContainer.Corner
        ] = (
            self.Corner(self, 0),
            self.Corner(self, 1),
            self.Corner(self, 2),
            self.Corner(self, 3)
        )
        self.tabs: set[TextTab] = set()
        self.tab_update_rates: defaultdict[int, set[TextTab]] = defaultdict(set)

    def __iter__(self) -> Iterator[TextTab]:
        return iter(self.tabs)

    def draw_all(self) -> None:
        for tab in self.tabs:
            if tab.state == tab.State.PRESSED:
                tab.tab_label.draw()

    def update_all(self) -> None:
        for update_rate, tabs in self.tab_update_rates.items():
            if self.window.world.age % update_rate == 0:
                for tab in tabs:
                    if tab.state == tab.State.PRESSED:
                        # noinspection PyProtectedMember
                        tab.tab_label.text = tab.tab_label._text()


class UIManager(arcade.gui.UIManager):
    def add_tabs(self, tabs: TextTabContainer) -> TextTabContainer:
        for corner in tabs.corners:
            self.add(corner)

        return tabs

    @staticmethod
    def set_tab_label_positions(tabs: TextTabContainer) -> None:
        for corner in tabs.corners:
            for tab in corner.children:
                tab.tab_label.set_position()


class Window(arcade.Window):
    # desired_tps = int(1 / update_rate)
    # update_rate = 1 / tps
    desired_tps: int
    # все ресурсы = ресурсы у существ + ресурсы на карте
    world_resources_tab: TextTab
    # ресурсы на карте
    map_resources_tab: TextTab
    # ресурсы у существ = ресурсы в хранилищах существ + ресурсы в телах существ
    creature_resources_tab: TextTab

    def __init__(self, width: int, height: int) -> None:
        super().__init__(width, height, center_window = True)

        self.world: World | None = None
        self.tab_container = TextTabContainer(self)
        self.set_tps(settings.MAX_TPS)
        self.tps = settings.MAX_TPS
        self.map_resources = Resources[int]()
        self.creature_resources = Resources[int]()
        self.world_resources = Resources[int]()

        self.ui_manager = UIManager(self)

        background_color = (255, 255, 255, 255)
        arcade.set_background_color(background_color)

    def start(self) -> None:
        center = (self.width // 2, self.height // 2)
        self.world = World(center)
        self.world.start()

        self.construct_tabs()

        # необходимо, чтобы разместить плашки, так как элементы размещаются на экране только после первой отрисовки
        self.on_draw()
        self.ui_manager.set_tab_label_positions(self.tab_container)

        self.ui_manager.enable()

    def construct_tabs(self) -> None:
        # правый верхний угол
        # возраст мира
        self.tab_container.corners[3].add(TextTab(lambda: self.world.age, window_descriptor.world_age_tab_update_rate))
        # счетчик tps
        self.tab_container.corners[3].add(
            TPSTab(lambda: f"tps/желаемые tps: {self.tps} / {self.desired_tps}", window_descriptor.tps_tab_update_rate)
        )

        # правый нижний угол
        self.tab_container.corners[2].add(
            TextTab(
                lambda: f"Появилось: {Creature.birth_counter}, умерло: {Creature.death_counter}",
                window_descriptor.tab_update_rate
            )
        )
        self.tab_container.corners[2].add(
            TextTab(
                lambda: f"Сейчас существ: {Creature.birth_counter - Creature.death_counter}",
                window_descriptor.tab_update_rate
            )
        )

        # левый верхний угол
        self.world_resources_tab = self.tab_container.corners[1].add(
            TextTab(lambda: f"Ресурсы в мире: {self.world_resources}", window_descriptor.resources_tab_update_rate)
        )
        self.map_resources_tab = self.tab_container.corners[1].add(
            TextTab(lambda: f"Ресурсы на карте: {self.map_resources}", window_descriptor.resources_tab_update_rate)
        )
        self.creature_resources_tab = self.tab_container.corners[1].add(
            TextTab(lambda: f"Ресурсы существ: {self.creature_resources}", window_descriptor.resources_tab_update_rate)
        )

        self.count_resources()
        self.count_tps()
        self.tab_container.update_all()

        self.ui_manager.add_tabs(self.tab_container)

    def count_resources(self) -> None:
        if self.world.age % window_descriptor.resources_tab_update_rate == 0:
            if self.map_resources_tab or self.world_resources_tab:
                self.map_resources = Resources[int]()
                # чтобы порядок ресурсов не менялся
                self.map_resources.fill_all(0)
                self.map_resources += Resources[int].sum(x.resources for x in self.world.chunk_list)

            if self.creature_resources_tab or self.world_resources_tab:
                self.creature_resources = Resources[int]()
                # чтобы порядок ресурсов не менялся
                self.creature_resources.fill_all(0)
                self.creature_resources += Resources[int].sum(x.remaining_resources for x in self.world.creatures) + \
                                           Resources[int].sum(x.storage.stored_resources for x in self.world.creatures)

            if self.world_resources_tab:
                self.world_resources = self.map_resources + self.creature_resources

    def count_tps(self) -> None:
        if self.world.age % window_descriptor.tps_tab_update_rate == 0:
            timings = arcade.get_timings()
            # за 100 последних тиков
            execution_time_100 = sum(sum(i) for i in timings.values())
            # добавляется небольшая константа, во избежание деления на 0
            average_execution_time = execution_time_100 / 100 + 0.00000001
            self.tps = int(1 / average_execution_time)

    def on_draw(self) -> None:
        self.clear()
        self.world.draw()
        self.ui_manager.draw()
        self.tab_container.draw_all()

    def on_update(self, delta_time: float) -> None:
        try:
            self.world.on_update()
            self.tab_container.update_all()
        except Exception as error:
            error.window = self
            raise error
        finally:
            self.count_resources()
            self.count_tps()

    def set_tps(self, tps: int) -> None:
        self.desired_tps = tps
        self.set_update_rate(1 / tps)

    def on_mouse_press(self, x, y, button, modifiers) -> None:
        """Выводит в консоль положение курсора."""

        print(f"x: {x}, y: {y}")
