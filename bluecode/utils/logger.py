#!/usr/bin/env python3

import logging
from enum import Enum


class LogLevel(Enum):
    """Enumeration of log levels."""
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


class Logger:
    """Singleton logger class for consistent logging throughout the application."""

    _instance = None
    _initialized = False

    def __new__(cls, name='bluecode', log_file=None, level=logging.INFO):
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
        return cls._instance

    def __init__(self, name='bluecode', log_file=None, level=logging.INFO):
        # Convert enum to int if needed
        if isinstance(level, LogLevel):
            level = level.value

        # Only initialize once
        if not self._initialized:
            self.logger = logging.getLogger(name)
            self.logger.setLevel(level)

            # Add console handler
            console_handler = logging.StreamHandler()
            console_handler.setLevel(level)
            console_formatter = logging.Formatter(
                '%(levelname)s - %(message)s')
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)

            # Add file handler if log_file is provided
            if log_file:
                file_handler = logging.FileHandler(log_file)
                file_handler.setLevel(level)
                file_formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                file_handler.setFormatter(file_formatter)
                self.logger.addHandler(file_handler)

            Logger._initialized = True

    def debug(self, message):
        """Log a debug message."""
        self.logger.debug(message)

    def info(self, message):
        """Log an info message."""
        self.logger.info(message)

    def warning(self, message):
        """Log a warning message."""
        self.logger.warning(message)

    def error(self, message):
        """Log an error message."""
        self.logger.error(message)

    def critical(self, message):
        """Log a critical message."""
        self.logger.critical(message)
