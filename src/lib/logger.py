#!/usr/bin/env python3


import logging
from enum import Enum


class LogLevel(Enum):
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


class Logger:
    _instance = None

    def __new__(cls, name='blue-code', log_file=None, level=logging.DEBUG):
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
            cls._instance.logger = logging.getLogger(name)
            cls._instance.logger.setLevel(level)

            # Avoid adding handlers multiple times if the logger is already configured.
            if not cls._instance.logger.handlers:
                # Console handler
                console_handler = logging.StreamHandler()
                console_handler.setLevel(level)
                console_formatter = logging.Formatter(
                    '%(levelname)s - %(message)s'
                )
                console_handler.setFormatter(console_formatter)
                cls._instance.logger.addHandler(console_handler)

                # File handler (only if log_file is provided)
                if log_file:
                    file_handler = logging.FileHandler(log_file)
                    file_handler.setLevel(level)
                    file_formatter = logging.Formatter(
                        '%(name)s - %(levelname)s - %(message)s'
                    )
                    file_handler.setFormatter(file_formatter)
                    cls._instance.logger.addHandler(file_handler)

        return cls._instance
