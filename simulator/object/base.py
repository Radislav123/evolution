import logging

from core import models
import abc


class BaseSimulationObject(abc.ABC):
    db_model: models.ObjectModel
    db_instance: models.ObjectModel
    logger: logging.Logger
    id: int

    def __repr__(self) -> str:
        return self.object_id

    def start(self, *args, **kwargs):
        """Выполняет подготовительные действия при начале симуляции."""

        self.save_to_db(*args, **kwargs)

    def stop(self, *args, **kwargs):
        """Выполняет завершающие действия при окончании симуляции."""

        self.save_to_db(*args, **kwargs)
        self.release_logs()

    def release_logs(self):
        """Отпускает файлы логов."""

        for handler in self.logger.handlers:
            self.logger.removeHandler(handler)

    @abc.abstractmethod
    def save_to_db(self, *args, **kwargs):
        """Сохраняет или обновляет объект в БД."""

        raise NotImplementedError()

    @property
    def object_id(self):
        return f"{self.__class__.__name__}{self.id}"
