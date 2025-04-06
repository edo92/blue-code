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
        # Convert enum to int if needed
        if isinstance(level, LogLevel):
            level = level.value

        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
            cls._instance.logger = None  # Initialize to None first

        return cls._instance

    def __init__(self, name='blue-code', log_file=None, level=logging.DEBUG):
        # Convert enum to int if needed
        if isinstance(level, LogLevel):
            level = level.value

        # Only initialize once
        if self.logger is None:
            self.logger = logging.getLogger(name)
            self.logger.setLevel(level)

            # Avoid adding handlers multiple times if the logger is already configured
            if not self.logger.handlers:
                # Console handler
                console_handler = logging.StreamHandler()
                console_handler.setLevel(level)
                console_formatter = logging.Formatter(
                    '%(levelname)s - %(message)s'
                )
                console_handler.setFormatter(console_formatter)
                self.logger.addHandler(console_handler)

                # File handler (only if log_file is provided)
                if log_file:
                    file_handler = logging.FileHandler(log_file)
                    file_handler.setLevel(level)
                    file_formatter = logging.Formatter(
                        '%(name)s - %(levelname)s - %(message)s'
                    )
                    file_handler.setFormatter(file_formatter)
                    self.logger.addHandler(file_handler)

    # Add these methods to make the class work correctly
    def debug(self, message):
        self.logger.debug(message)

    def info(self, message):
        self.logger.info(message)

    def warning(self, message):
        self.logger.warning(message)

    def error(self, message):
        self.logger.error(message)

    def critical(self, message):
        self.logger.critical(message)

    # Add this as a compatibility method
    def log(self, message):
        self.logger.debug(message)
