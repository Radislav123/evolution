import logging

from core import models


class BasePlaybackObject:
    db_model: models.ObjectModel
    db_instance: models.ObjectModel
    logger: logging.Logger

    def __init__(self, db_id):
        self.id = db_id
        self.db_instance = self.db_model.objects.get(id = db_id)

    def __repr__(self):
        return self.object_id

    def release_logs(self):
        """Отпускает файлы логов."""

        for handler in self.logger.handlers:
            self.logger.removeHandler(handler)

    @property
    def object_id(self):
        return f"{self.__class__.__name__}{self.id}"

    def start(self):
        """Выполняет подготовительные действия при начале воспроизведения."""

    def stop(self):
        """Выполняет завершающие действия при окончании воспроизведения."""

        self.release_logs()
