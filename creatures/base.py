class BaseCreature:
    counter = 0

    def __init__(self, position: set = (0, 0)):
        BaseCreature.counter += 1
        self.id = BaseCreature.counter
        self.genes = None
        self.stats = None
        self.position = position

    def tick(self):
        """Симулирует жизнедеятельность за один тик."""
        print(f"{self.id} : tick")
