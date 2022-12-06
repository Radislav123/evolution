import logging
from pathlib import Path

from evolution.settings import LOGS_PATH


OBJECT_ID = "objectId"


class RemoveLevelFilter(logging.Filter):
    def __init__(self, level):
        super().__init__()
        self.level = level

    def filter(self, record):
        return record.levelno != self.level


class BaseLogger:
    """Обертка для logging <https://docs.python.org/3/library/logging.html>."""

    # история мира - уровень info
    CONSOLE_LOGS_LEVEL = logging.DEBUG
    FILE_LOGS_LEVEL = logging.DEBUG
    LOG_FORMAT = f"[%(asctime)s] - [%(levelname)s] - %(name)s - %({OBJECT_ID})s" \
                 f" - (%(filename)s).%(funcName)s(%(lineno)d) - %(message)s"
    LOG_FORMATTER = logging.Formatter(LOG_FORMAT)

    @staticmethod
    def get_function_real_filename(function):
        return function.__globals__["__file__"].split('\\')[-1]

    @classmethod
    def get_log_filepath(cls, filename):
        return Path(f"{LOGS_PATH}/{filename}.log")

    @classmethod
    def construct_handler(cls, logger: logging.Logger, log_level = logging.DEBUG, to_console = False):
        if to_console:
            handler = logging.StreamHandler()
        else:
            # в файл
            world_name = logger.name.split(".")[0]
            filename = world_name
            replacing_characters = [" ", "-", ":", "."]
            for character in replacing_characters:
                filename = filename.replace(character, "_")
            handler = logging.FileHandler(cls.get_log_filepath(filename))
        handler.setLevel(log_level)
        handler.setFormatter(cls.LOG_FORMATTER)
        return handler

    def __new__(cls, logger_name):
        # создает папку для логов, если ее нет
        Path(LOGS_PATH).mkdir(parents = True, exist_ok = True)
        logger = logging.getLogger(logger_name)
        logger.propagate = False
        logger.setLevel(logging.DEBUG)
        # в файл
        # noinspection PyTypeChecker
        logger.addHandler(cls.construct_handler(logger, cls.FILE_LOGS_LEVEL))
        # в консоль
        # noinspection PyTypeChecker
        console_handler = cls.construct_handler(logger, cls.CONSOLE_LOGS_LEVEL, True)
        console_handler.addFilter(RemoveLevelFilter(logging.INFO))
        logger.addHandler(console_handler)
        return logger


# для проверки логгера
if __name__ == "__main__":
    test_logger = BaseLogger("test_logger")
    print(f"logger name: {test_logger.name}")
    print(f"help: {test_logger.__doc__}")

    test_logger.info("info message")
    test_logger.debug("debug message")
    test_logger.warning("warning message")
    test_logger.error("error message")
    test_logger.critical("critical message")
