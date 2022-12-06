import logging

from simulator import models
from simulator.logger.base import OBJECT_ID


class Object:
    db_model: type(models.ObjectModel)
    db_instance: models.ObjectModel
    logger: logging.Logger | logging.LoggerAdapter
    _serial_number: int = None

    def __repr__(self):
        return self.object_id

    def post_init(self):
        self.save_to_db()
        self.logger = logging.LoggerAdapter(self.logger, {OBJECT_ID: self.object_id})

        self.logger.info(f"{self.object_id} generates")

    def release_logs(self):
        """Отпускает файлы логов."""

        for handler in self.logger.logger.handlers:
            self.logger.logger.removeHandler(handler)

    def save_to_db(self):
        """Сохраняет или обновляет объект в БД."""

        raise NotImplementedError()

    @classmethod
    def load_from_db(cls, db_instance):
        """Загружает объект из БД."""

        raise NotImplementedError()

    @property
    def object_id(self):
        return f"{self.__class__.__name__}{self.get_serial_number()}"

    @property
    def id(self):
        return self.get_serial_number()

    def get_serial_number(self) -> int:
        if self._serial_number is None:
            self._serial_number = self.db_model.objects.count()
        return self._serial_number
