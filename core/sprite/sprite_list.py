import arcade


class EvolutionSpriteList(arcade.SpriteList):
    def __repr__(self):
        string = f"{len(self)}: {', '.join(self)}"
        return string
