import logging

from core import models


class BaseSimulationObject:
    db_model: models.ObjectModel
    db_instance: models.ObjectModel
    logger: logging.Logger
    id: int

    def __repr__(self):
        return self.object_id

    def start(self):
        """Выполняет подготовительные действия при начале симуляции."""

        self.save_to_db()

    def stop(self):
        """Выполняет завершающие действия при окончании симуляции."""

        self.save_to_db()
        self.release_logs()

    def release_logs(self):
        """Отпускает файлы логов."""

        for handler in self.logger.handlers:
            self.logger.removeHandler(handler)

    def save_to_db(self):
        """Сохраняет или обновляет объект в БД."""

        raise NotImplementedError()

    @property
    def object_id(self):
        return f"{self.__class__.__name__}{self.id}"
