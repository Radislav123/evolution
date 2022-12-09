class Position:
    x: int
    y: int

    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __str__(self):
        return str(self.to_tuple())

    def to_tuple(self):
        return self.x, self.y


class MovementVector:
    x: int
    y: int

    def __init__(self, x = 0, y = 0):
        self.x = x
        self.y = y

    def __str__(self):
        return str(self.to_tuple())

    def to_tuple(self):
        return self.x, self.y

    def accumulate(self, x, y):
        self.x += x
        self.y += y

    def reset(self):
        self.x = 0
        self.y = 0

    def is_empty(self):
        return self.x == 0 and self.y == 0
