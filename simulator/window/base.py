import enum
from typing import Any, Callable, Iterator

import arcade
import arcade.gui

from evolution import settings
from simulator.creature import BaseSimulationCreature
from simulator.world import BaseSimulationWorld
from simulator.world_resource import Resources


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
        def __init__(self, tab: "TextTab", text: Callable[[], str], *args, **kwargs) -> None:
            self.tab = tab
            self._text = text

            color = (0, 0, 0)
            super().__init__(tab.text, 0, 0, color = color, *args, **kwargs)

        def draw(self) -> None:
            if self.tab.state == self.tab.State.PRESSED:
                self.text = self._text()
                super().draw()

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
            text: Callable[..., str] = None,
            on_click: Callable[..., Any] | None = None,
            on_click_args = None
    ) -> None:
        super().__init__()

        self.state: TextTab.State | None = None
        self.set()
        self.corner: TextTabContainer.Corner | None = None
        self.update_text()
        border = 10
        self.rect = self.rect.resize(round(self.ui_label.width) + border, round(self.ui_label.height) + border)
        if text is None:
            def text() -> None:
                pass
        self.tab_label = self.Label(self, text)
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

    def on_click(self, event: arcade.gui.UIOnClickEvent) -> None:
        if self.state == self.State.PRESSED:
            self.reset()
        else:
            self.set()
        self.update_text()

    def update_text(self) -> None:
        self.text = str(self.state)


class TPSTab(TextTab):
    class Label(TextTab.Label):
        def __init__(self, tab: "TextTab", text: Callable[[], str], *args, **kwargs):
            super().__init__(tab, text, *args, **kwargs)
            self.text = "0"

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

        def __init__(self, index: int, *args, **kwargs) -> None:
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

            return result

    def __init__(self, window: "SimulationWindow") -> None:
        self.window = window
        # 00 - левый нижний угол (corners[0])
        # 01 - левый верхний угол (corners[1])
        # 10 - правый нижний угол (corners[2])
        # 11 - правый верхний угол (corners[3])
        # 01 11
        # 00 10
        # 1 3
        # 0 2
        # tabs[n] = [tab_0, tab_1,..]
        self.corners: tuple[
            TextTabContainer.Corner,
            TextTabContainer.Corner,
            TextTabContainer.Corner,
            TextTabContainer.Corner
        ] = (self.Corner(0), self.Corner(1), self.Corner(2), self.Corner(3))

    def __iter__(self) -> Iterator[TextTab]:
        tabs = []
        for corner in self.corners:
            tabs.extend(corner)
        return iter(tabs)

    def draw_all(self) -> None:
        for corner in self.corners:
            for tab in corner.children:
                if tab is not None:
                    tab.tab_label.draw()


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


class SimulationWindow(arcade.Window):
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

        self.world: BaseSimulationWorld | None = None
        self.tabs = TextTabContainer(self)
        self.set_tps(settings.MAX_TPS)
        self.tps = settings.MAX_TPS
        self.map_resources = Resources()
        self.creature_resources = Resources()
        self.world_resources = Resources()

        self.ui_manager = UIManager(self)

        background_color = (255, 255, 255, 255)
        arcade.set_background_color(background_color)

    def start(self, world_width: int, world_height: int) -> None:
        center = (self.width // 2, self.height // 2)
        self.world = BaseSimulationWorld(world_width, world_height, center)
        self.world.start()

        # todo: добавить возможность выключать РАСЧЕТЫ информации для плашек, при не нажатых кнопках
        self.construct_tabs()

        # необходимо, чтобы разместить плашки, так как элементы размещаются на экране только после первой отрисовки
        self.on_draw()
        self.ui_manager.set_tab_label_positions(self.tabs)

        self.ui_manager.enable()

    def construct_tabs(self) -> None:
        # правый верхний угол
        # возраст мира
        self.tabs.corners[3].add(TextTab(lambda: self.world.age))
        # счетчик tps
        self.tabs.corners[3].add(TPSTab(lambda: f"{self.tps}"))

        # правый нижний угол
        self.tabs.corners[2].add(
            TextTab(
                lambda: f"Появилось: {BaseSimulationCreature.birth_counter},"
                        f" умерло: {BaseSimulationCreature.death_counter}"
            )
        )
        self.tabs.corners[2].add(
            TextTab(
                lambda: f"Сейчас существ: {BaseSimulationCreature.birth_counter - BaseSimulationCreature.death_counter}"
            )
        )

        # левый верхний угол
        self.world_resources_tab = self.tabs.corners[1].add(
            TextTab(lambda: f"Ресурсы в мире: {self.world_resources}")
        )
        self.map_resources_tab = self.tabs.corners[1].add(
            TextTab(lambda: f"Ресурсы на карте: {self.map_resources}")
        )
        self.creature_resources_tab = self.tabs.corners[1].add(
            TextTab(lambda: f"Ресурсы существ: {self.creature_resources}")
        )

        self.ui_manager.add_tabs(self.tabs)

    def count_resources(self) -> None:
        # todo: rewrite loops by maps
        if self.map_resources_tab or self.world_resources_tab:
            self.map_resources = Resources()
            for line in self.world.chunks:
                for chunk in line:
                    self.map_resources += chunk.get_resources()

        if self.creature_resources_tab or self.world_resources_tab:
            self.creature_resources = Resources()
            for creature in self.world.creatures:
                creature: BaseSimulationCreature
                self.creature_resources += creature.remaining_resources
                self.creature_resources += creature.storage.stored_resources

        if self.world_resources_tab:
            self.world_resources = self.map_resources + self.creature_resources

    def count_tps(self) -> None:
        # todo: rewrite loops by maps
        # if self.world.age % 10 == 0:
        if self.world.age % 1 == 0:
            timings = arcade.get_timings()
            # за 100 последних тиков
            execution_time_100 = 0
            for i in timings:
                execution_time_100 += sum(timings[i])
            # добавляется 0.00000001, во избежание деления на 0
            average_execution_time = execution_time_100 / 100 + 0.0001
            self.tps = int(1 / average_execution_time)

    def on_draw(self) -> None:
        self.clear()
        self.world.draw()
        self.ui_manager.draw()
        self.tabs.draw_all()

    def on_update(self, delta_time: float) -> None:
        try:
            self.world.on_update(delta_time)
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
