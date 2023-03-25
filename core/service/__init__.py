class Switch:
    value: bool

    def __init__(self):
        self.value = False

    def __bool__(self) -> bool:
        return self.value

    def set(self):
        self.value = True

    def reset(self):
        self.value = False
