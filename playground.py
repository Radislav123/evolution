import arcade
import arcade.gui


class Button(arcade.gui.UIFlatButton):
    def on_click(self, event: arcade.gui.UIOnClickEvent) -> None:
        print("--------------------------")
        print(self.text)
        print(self.rect)
        print("--------------------------")


class MainGame(arcade.Window):
    def __init__(self):
        super().__init__(600, 600, title = "Buttons")

        arcade.set_background_color(arcade.color.GRAY)

        self.ui_manager = arcade.gui.UIManager()
        self.ui_manager.enable()

        # self.add_grid_layout()
        # self.add_box_layout()
        self.add_anchor_layout()

    @staticmethod
    def get_buttons() -> tuple[Button, Button]:
        button_0 = Button(text = "grid_button_0")
        button_1 = Button(text = "grid_button_1")
        button_0.rect = arcade.gui.Rect(
            button_0.x,
            button_0.y,
            round(button_0.ui_label.width) + 10,
            round(button_0.ui_label.height) + 10
        )
        button_1.rect = arcade.gui.Rect(
            button_1.x,
            button_1.y,
            round(button_1.ui_label.width) + 10,
            round(button_1.ui_label.height) + 10
        )
        return button_0, button_1

    def add_grid_layout(self) -> None:
        button_0, button_1 = self.get_buttons()
        layout_0 = arcade.gui.UIGridLayout(row_count = 10)
        layout_0.add(button_0, row_num = 0)
        layout_0.add(button_1, row_num = 1)
        self.ui_manager.add(layout_0)

    def add_box_layout(self) -> None:
        button_0, button_1 = self.get_buttons()
        layout_0 = arcade.gui.UIBoxLayout(vertical = False, align = "right")
        layout_0.add(button_0)
        layout_0.add(button_1)
        self.ui_manager.add(layout_0)

    def add_anchor_layout(self) -> None:
        button_0, button_1 = self.get_buttons()
        layout_0 = arcade.gui.UIAnchorLayout()
        layout_0.add(button_0, anchor_x = "right", anchor_y = "top")
        layout_0.add(button_1, anchor_x = "right", anchor_y = "top", align_y = -button_0.height)
        self.ui_manager.add(layout_0)

    def on_draw(self) -> None:
        arcade.start_render()

        self.ui_manager.draw()


MainGame()
arcade.run()
