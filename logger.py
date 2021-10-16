# coding: utf-8

import time


LOGGERS = []


class ConsoleLogger:
    def __init__(self, colored=True):
        self._colored = colored

    def debug(self, message):
        print(f"{time.time()} [DEBUG] {message}")

    def info(self, message):
        msg = f"{time.time()} [INFO] {message}"
        if self._colored:
            print(f"\x1b[34m{msg}\x1b[0m")
        else:
            print(msg)

    def warn(self, message):
        msg = f"{time.time()} [WARN] {message}"
        if self._colored:
            print(f"\x1b[33m{msg}\x1b[0m")
        else:
            print(msg)

    def error(self, message):
        msg = f"{time.time()} [ERROR] {message}"
        if self._colored:
            print(f"\x1b[31m{msg}\x1b[0m")
        else:
            print(msg)


def debug(message):
    for logger in LOGGERS:
        logger.debug(message)


def info(message):
    for logger in LOGGERS:
        logger.info(message)


def warn(message):
    for logger in LOGGERS:
        logger.warn(message)


def error(message):
    for logger in LOGGERS:
        logger.error(message)
