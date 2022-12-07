from core import models
from player.object.base import BasePlaybackObject
from logger import BaseLogger


class BasePlaybackWorld(BasePlaybackObject):
    db_model = models.World
    db_instance: models.World

    def __init__(self, db_id):
        super().__init__(db_id)
        self.age = self.db_instance.age
        self.width = self.db_instance.width
        self.height = self.db_instance.height
        # {creature.object_id: creature}
        # self.creatures: dict[str, BasePlaybackCreature] = {}
        self.logger = BaseLogger(f"{self.object_id}_{self.logger_postfix}")
