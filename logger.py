import inspect
import logging
from time import strftime as time
import os

class Logger:
    def __init__(
        self,
        debug=False,
        level: int = logging.INFO,
    ):
        self.DEBUG = debug
        self.logging = logging

        if not os.path.isdir('logs'):
            os.mkdir('logs')

        logging.basicConfig(
            level=logging.DEBUG if self.DEBUG else level,
            format="%(asctime)s | %(levelname)s | %(name)s: %(message)s",
            datefmt="%m-%d %H:%M:%S",
            handlers=[logging.FileHandler(filename=f'logs\\{time("%Y-%m-%d %H-%M-%S")}.log',
                                          mode="a", encoding="utf-8", delay=False)],)
        if self.DEBUG:
            self.logging.debug("Режим разработчика")

    @staticmethod
    def stack_trace(stack):
        return (
            stack[1].filename.replace("\\", "/").split("/")[-1].split(".")[0]
            + "."
            + f"{stack[1].function}"
        )

    def info(self, message, to_console=True):
        message = f"[{self.stack_trace(inspect.stack())}] {message}"
        self.logging.info(message)
        if to_console:
            self.print(message, log=False)

    def error(self, *message, to_console=True):
        message = " ".join([str(arg) for arg in message])
        message = f"[{self.stack_trace(inspect.stack())}] {message}"
        self.logging.error(message)
        if to_console:
            self.print(message, log=False)

    def critical(self, *message, to_console=True):
        message = " ".join([str(arg) for arg in message])
        message = f"[{self.stack_trace(inspect.stack())}] {message}"
        self.logging.critical(message)
        if to_console:
            self.print(message, log=False)

    def debug(self, *args, to_console=True, **kwargs):
        msg = " ".join([str(arg) for arg in args])
        msg = f"[{self.stack_trace(inspect.stack())}] {msg}"
        self.logging.debug(msg)
        if self.DEBUG or to_console:
            self.print(*args, **kwargs, log=False)

    def warning(self, message, to_console=True):
        message = f"[{self.stack_trace(inspect.stack())}] {message}"
        self.logging.warning(message)
        if to_console:
            self.print(message, log=False)

    def exception(self, message, to_console=True):
        message = f"[{self.stack_trace(inspect.stack())}] {message}"
        self.logging.exception(message)
        if to_console:
            self.print(message, log=False)

    def print(self, *args, log=True, **kwargs):
        msg = " ".join([str(arg) for arg in args])
        stack_tr = self.stack_trace(inspect.stack())
        if not stack_tr.lower().startswith("logger."):
            msg = f"[{stack_tr}] {msg}"
        print(msg, **kwargs)
        if log:
            self.logging.info(msg)
